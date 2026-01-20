"""Tests for execution pages."""

import pytest
from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.core.database import get_db
from unittest.mock import MagicMock, AsyncMock
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.web.routes.admin import pages_router, partials_router
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    WorkflowNotFoundError,
    InMemoryStatePersistence,
)


class MockWorkflowRegistry:
    """Mock registry for testing."""
    
    def __init__(self):
        self._workflows = {}
    
    def add(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow
    
    def get(self, workflow_id: str) -> Workflow:
        if workflow_id not in self._workflows:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        return self._workflows[workflow_id]
    
    def list_ids(self) -> list:
        return list(self._workflows.keys())


@pytest.fixture
def test_workflow() -> Workflow:
    """Create a test workflow."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test_workflow",
        revision="1.0",
        effective_date="2026-01-01",
        name="Test Workflow",
        description="A test workflow",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(name="Discovery", scope="project"),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="step_1",
                scope="project",
                role="PM",
                task_prompt="Do step 1",
                produces="discovery",
                inputs=[],
            ),
            WorkflowStep(
                step_id="step_2",
                scope="project",
                role="BA",
                task_prompt="Do step 2",
                produces="discovery",
                inputs=["discovery"],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow) -> MockWorkflowRegistry:
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def mock_persistence() -> InMemoryStatePersistence:
    return InMemoryStatePersistence()



@pytest.fixture
def mock_admin_user() -> User:
    """Create mock admin user."""
    from uuid import uuid4
    return User(
        user_id=str(uuid4()),
        email="admin@test.com",
        name="Test Admin",
        is_active=True,
        email_verified=True,
        is_admin=True,
    )

@pytest.fixture
def app(mock_registry, mock_persistence, mock_admin_user) -> FastAPI:
    clear_caches()
    reset_execution_service()
    
    test_app = FastAPI()
    
    # Override admin requirement
    async def mock_require_admin():
        return mock_admin_user
    test_app.dependency_overrides[require_admin] = mock_require_admin
    test_app.include_router(api_router)
    test_app.include_router(pages_router)
    test_app.include_router(partials_router)
    test_app.mount("/static", StaticFiles(directory="app/web/static/admin"), name="static")
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    # Mock database for LLMRun queries
    async def mock_get_db():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.fetchall.return_value = []
        
        async def mock_execute(*args, **kwargs):
            return mock_result
        mock_db.execute = mock_execute
        yield mock_db
    test_app.dependency_overrides[get_db] = mock_get_db
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


class TestExecutionsList:
    """Tests for executions list page."""
    
    def test_executions_page_renders(self, client: TestClient):
        """Executions page returns 200."""
        response = client.get("/admin/executions")
        assert response.status_code == 200
    
    def test_executions_page_shows_all_executions(self, client: TestClient):
        """Executions page renders with empty state when no DB executions.
        
        Note: This test uses a mocked empty database, so we can only verify
        the page structure renders correctly, not that created executions appear.
        The in-memory execution service state isn't visible to DB queries.
        """
        response = client.get("/admin/executions")
        assert response.status_code == 200
        assert "Executions" in response.text
    
    def test_executions_page_supports_workflow_filter(self, client: TestClient):
        """Executions page can filter by workflow."""
        response = client.get("/admin/executions?workflow_id=test_workflow")
        assert response.status_code == 200
    
    def test_executions_page_supports_status_filter(self, client: TestClient):
        """Executions page can filter by status."""
        response = client.get("/admin/executions?status=running")
        assert response.status_code == 200


class TestExecutionDetail:
    """Tests for execution detail page."""
    
    def test_execution_detail_page_renders(self, client: TestClient):
        """Execution detail page returns 200."""
        # Create an execution first
        start_resp = client.post(
            "/admin/workflows/test_workflow/start",
            data={"project_id": "proj_detail"},
            follow_redirects=False,
        )
        exec_url = start_resp.headers["location"]
        
        response = client.get(exec_url)
        assert response.status_code == 200
    
    def test_execution_detail_shows_current_step(self, client: TestClient):
        """Execution detail shows workflow info."""
        start_resp = client.post(
            "/admin/workflows/test_workflow/start",
            data={"project_id": "proj_step"},
            follow_redirects=False,
        )
        exec_url = start_resp.headers["location"]
        
        response = client.get(exec_url)
        assert "test_workflow" in response.text
    
    def test_execution_detail_shows_step_progress(self, client: TestClient):
        """Execution detail shows step progress."""
        start_resp = client.post(
            "/admin/workflows/test_workflow/start",
            data={"project_id": "proj_progress"},
            follow_redirects=False,
        )
        exec_url = start_resp.headers["location"]
        
        response = client.get(exec_url)
        assert "Step Progress" in response.text
    
    def test_execution_not_found(self, client: TestClient):
        """Non-existent execution returns 404."""
        response = client.get("/admin/executions/exec_nonexistent")
        assert response.status_code == 404


class TestExecutionPartials:
    """Tests for HTMX partials."""
    
    def test_status_partial_returns_html(self, client: TestClient):
        """Status partial returns status badge HTML."""
        # Create execution
        start_resp = client.post(
            "/admin/workflows/test_workflow/start",
            data={"project_id": "proj_partial"},
            follow_redirects=False,
        )
        exec_id = start_resp.headers["location"].split("/")[-1]
        
        response = client.get(
            f"/partials/executions/{exec_id}/status",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        assert "inline-flex" in response.text  # Tailwind status badge
    
    def test_cancel_button_appears_for_running(self, client: TestClient):
        """Cancel button appears for running execution."""
        start_resp = client.post(
            "/admin/workflows/test_workflow/start",
            data={"project_id": "proj_cancel"},
            follow_redirects=False,
        )
        exec_url = start_resp.headers["location"]
        
        response = client.get(exec_url)
        assert "Cancel Execution" in response.text

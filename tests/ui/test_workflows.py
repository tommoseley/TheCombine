"""Tests for workflow pages."""

import pytest
from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.web.routes.admin import pages_router
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
        description="A test workflow for testing",
        scopes={
            "project": ScopeConfig(parent=None),
            "section": ScopeConfig(parent="project"),
        },
        document_types={
            "discovery": DocumentTypeConfig(
                name="Discovery Document",
                scope="project",
                acceptance_required=True,
            ),
            "analysis": DocumentTypeConfig(
                name="Analysis",
                scope="section",
            ),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="step_discovery",
                scope="project",
                role="PM",
                task_prompt="Discover requirements",
                produces="discovery",
                inputs=[],
            ),
            WorkflowStep(
                step_id="step_analysis",
                scope="section",
                role="BA",
                task_prompt="Analyze requirements",
                produces="analysis",
                inputs=["discovery"],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow) -> MockWorkflowRegistry:
    """Create mock registry with test workflow."""
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def mock_persistence() -> InMemoryStatePersistence:
    """Create in-memory persistence."""
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
    """Create test app with UI routes."""
    clear_caches()
    reset_execution_service()
    
    test_app = FastAPI()
    
    # Override admin requirement
    async def mock_require_admin():
        return mock_admin_user
    test_app.dependency_overrides[require_admin] = mock_require_admin
    test_app.include_router(api_router)
    test_app.include_router(pages_router)
    test_app.mount("/static", StaticFiles(directory="app/web/static/admin"), name="static")
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestWorkflowsList:
    """Tests for workflows list page."""
    
    def test_workflows_page_renders(self, client: TestClient):
        """Workflows page returns 200."""
        response = client.get("/admin/workflows")
        assert response.status_code == 200
    
    def test_workflows_page_shows_all_workflows(self, client: TestClient):
        """Workflows page displays workflow name."""
        response = client.get("/admin/workflows")
        assert "Test Workflow" in response.text
    
    def test_workflow_card_displays_name_and_description(self, client: TestClient):
        """Workflow card shows name and description."""
        response = client.get("/admin/workflows")
        html = response.text
        
        assert "Test Workflow" in html
        assert "A test workflow for testing" in html
    
    def test_workflow_card_shows_step_count(self, client: TestClient):
        """Workflow card shows step count."""
        response = client.get("/admin/workflows")
        assert "2 steps" in response.text


class TestWorkflowDetail:
    """Tests for workflow detail page."""
    
    def test_workflow_detail_page_renders(self, client: TestClient):
        """Workflow detail page returns 200."""
        response = client.get("/admin/workflows/test_workflow")
        assert response.status_code == 200
    
    def test_workflow_detail_shows_scopes(self, client: TestClient):
        """Workflow detail shows scope definitions."""
        response = client.get("/admin/workflows/test_workflow")
        html = response.text
        
        assert "project" in html
        assert "section" in html
    
    def test_workflow_detail_shows_document_types(self, client: TestClient):
        """Workflow detail shows document types."""
        response = client.get("/admin/workflows/test_workflow")
        html = response.text
        
        assert "discovery" in html
        assert "Discovery Document" in html
        assert "Required" in html  # acceptance_required
    
    def test_workflow_detail_shows_steps(self, client: TestClient):
        """Workflow detail shows steps."""
        response = client.get("/admin/workflows/test_workflow")
        html = response.text
        
        assert "step_discovery" in html
        assert "step_analysis" in html
        assert "PM" in html
        assert "BA" in html
    
    def test_workflow_detail_not_found(self, client: TestClient):
        """Non-existent workflow returns 404."""
        response = client.get("/admin/workflows/nonexistent")
        assert response.status_code == 404


class TestStartWorkflow:
    """Tests for starting workflow from UI."""
    
    def test_start_workflow_creates_execution_and_redirects(self, client: TestClient):
        """Starting workflow creates execution and redirects."""
        response = client.post(
            "/admin/workflows/test_workflow/start",
            data={"project_id": "proj_test"},
            follow_redirects=False,
        )
        
        assert response.status_code == 303
        assert "/executions/" in response.headers["location"]

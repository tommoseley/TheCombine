"""Tests for dashboard and base layout."""

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
from app.web.routes.admin import pages_router, dashboard_router
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
        revision="1",
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
    test_app.include_router(dashboard_router)
    
    # Mount static files
    test_app.mount("/static", StaticFiles(directory="app/web/static/admin"), name="static")
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    # Mock database for LLMRun queries
    async def mock_get_db():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
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
    """Create test client."""
    return TestClient(app)


class TestDashboard:
    """Tests for dashboard page."""
    
    def test_dashboard_renders(self, client: TestClient):
        """Dashboard page returns 200."""
        response = client.get("/admin")
        assert response.status_code == 200
    
    def test_dashboard_shows_navigation(self, client: TestClient):
        """Dashboard includes navigation links."""
        response = client.get("/admin")
        html = response.text
        
        assert 'href="/admin/dashboard"' in html
        assert 'href="/admin/workflows"' in html
        assert 'href="/admin/executions"' in html
    
    def test_dashboard_shows_recent_executions_section(self, client: TestClient):
        """Dashboard has recent executions section."""
        response = client.get("/admin")
        html = response.text
        
        assert "Recent Activity" in html
    
    def test_dashboard_shows_workflow_shortcuts(self, client: TestClient):
        """Dashboard shows workflow shortcuts."""
        response = client.get("/admin")
        html = response.text
        
        assert "Quick Start" in html
        assert "Test Workflow" in html
        assert "2 steps" in html
    
    def test_dashboard_index_works(self, client: TestClient):
        """Dashboard index /dashboard shows available dashboards."""
        response = client.get("/admin/dashboard")
        assert response.status_code == 200
        assert "Cost Dashboard" in response.text


class TestBaseTemplate:
    """Tests for base template features."""
    
    def test_includes_htmx_script(self, client: TestClient):
        """Base template includes HTMX."""
        response = client.get("/admin")
        assert "htmx.org" in response.text
    
    def test_includes_websocket_script(self, client: TestClient):
        """Base template includes WebSocket script."""
        response = client.get("/admin")
        assert "websocket.js" in response.text
    
    def test_page_title_set(self, client: TestClient):
        """Page has correct title."""
        response = client.get("/admin")
        assert "<title>" in response.text
        assert "The Combine" in response.text

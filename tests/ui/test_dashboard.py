"""Tests for dashboard and base layout."""

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.ui.routers import pages_router
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
def app(mock_registry, mock_persistence) -> FastAPI:
    """Create test app with UI routes."""
    clear_caches()
    reset_execution_service()
    
    test_app = FastAPI()
    test_app.include_router(api_router)
    test_app.include_router(pages_router)
    
    # Mount static files
    test_app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")
    
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


class TestDashboard:
    """Tests for dashboard page."""
    
    def test_dashboard_renders(self, client: TestClient):
        """Dashboard page returns 200."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_dashboard_shows_navigation(self, client: TestClient):
        """Dashboard includes navigation links."""
        response = client.get("/")
        html = response.text
        
        assert 'href="/"' in html
        assert 'href="/workflows"' in html
        assert 'href="/executions"' in html
    
    def test_dashboard_shows_recent_executions_section(self, client: TestClient):
        """Dashboard has recent executions section."""
        response = client.get("/")
        html = response.text
        
        assert "Recent Executions" in html
    
    def test_dashboard_shows_workflow_shortcuts(self, client: TestClient):
        """Dashboard shows workflow shortcuts."""
        response = client.get("/")
        html = response.text
        
        assert "Quick Start" in html
        assert "Test Workflow" in html
        assert "2 steps" in html
    
    def test_dashboard_alias_works(self, client: TestClient):
        """Dashboard alias /dashboard works."""
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard" in response.text


class TestBaseTemplate:
    """Tests for base template features."""
    
    def test_includes_htmx_script(self, client: TestClient):
        """Base template includes HTMX."""
        response = client.get("/")
        assert "htmx.org" in response.text
    
    def test_includes_websocket_script(self, client: TestClient):
        """Base template includes WebSocket script."""
        response = client.get("/")
        assert "websocket.js" in response.text
    
    def test_page_title_set(self, client: TestClient):
        """Page has correct title."""
        response = client.get("/")
        assert "<title>" in response.text
        assert "The Combine" in response.text

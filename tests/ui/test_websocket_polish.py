"""Tests for WebSocket integration and UI polish."""

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.ui.routers import pages_router, partials_router
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
            "discovery": DocumentTypeConfig(
                name="Discovery",
                scope="project",
                acceptance_required=True,
            ),
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
def app(mock_registry, mock_persistence) -> FastAPI:
    clear_caches()
    reset_execution_service()
    
    test_app = FastAPI()
    test_app.include_router(api_router)
    test_app.include_router(pages_router)
    test_app.include_router(partials_router)
    test_app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def create_execution(client: TestClient) -> str:
    """Helper to create an execution and return its ID."""
    start_resp = client.post(
        "/workflows/test_workflow/start",
        data={"project_id": "proj_test"},
        follow_redirects=False,
    )
    return start_resp.headers["location"].split("/")[-1]


class TestWebSocketIntegration:
    """Tests for WebSocket client integration in pages."""
    
    def test_execution_detail_includes_websocket_js(self, client: TestClient):
        """Execution detail page includes WebSocket JavaScript."""
        exec_id = create_execution(client)
        response = client.get(f"/executions/{exec_id}")
        assert response.status_code == 200
        assert "websocket.js" in response.text
    
    def test_execution_detail_has_websocket_initialization(self, client: TestClient):
        """Execution detail page initializes WebSocket connection."""
        exec_id = create_execution(client)
        response = client.get(f"/executions/{exec_id}")
        assert "ExecutionWebSocket" in response.text
    
    def test_dashboard_does_not_have_websocket(self, client: TestClient):
        """Dashboard page doesn't initialize execution-specific WebSocket."""
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Dashboard includes the script but shouldn't init ExecutionWebSocket
        assert "new ExecutionWebSocket" not in response.text


class TestHTMXPolling:
    """Tests for HTMX polling fallback."""
    
    def test_execution_detail_has_htmx_polling(self, client: TestClient):
        """Execution detail page has HTMX polling for status updates."""
        exec_id = create_execution(client)
        response = client.get(f"/executions/{exec_id}")
        assert "hx-trigger" in response.text
    
    def test_dashboard_recent_executions_polling(self, client: TestClient):
        """Dashboard has polling for recent executions."""
        response = client.get("/dashboard")
        assert "every 10s" in response.text


class TestStaticAssets:
    """Tests for static asset serving."""
    
    def test_css_serves_correctly(self, client: TestClient):
        """CSS file is served with correct content type."""
        response = client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
    
    def test_js_serves_correctly(self, client: TestClient):
        """JavaScript file is served with correct content type."""
        response = client.get("/static/js/websocket.js")
        assert response.status_code == 200
        # Could be application/javascript or text/javascript
        content_type = response.headers.get("content-type", "")
        assert "javascript" in content_type
    
    def test_css_includes_calm_authority_tokens(self, client: TestClient):
        """CSS includes Calm Authority design tokens."""
        response = client.get("/static/css/styles.css")
        assert "--color-bg" in response.text
        assert "--color-primary" in response.text
    
    def test_websocket_js_has_reconnect_logic(self, client: TestClient):
        """WebSocket JS has reconnection logic."""
        response = client.get("/static/js/websocket.js")
        assert "attemptReconnect" in response.text
        assert "maxReconnectAttempts" in response.text


class TestGracefulDegradation:
    """Tests for graceful degradation without JavaScript."""
    
    def test_pages_work_without_js(self, client: TestClient):
        """Pages render valid HTML that works without JavaScript."""
        # Dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text.lower()
        
        # Workflows list
        response = client.get("/workflows")
        assert response.status_code == 200
        
        # Executions list
        response = client.get("/executions")
        assert response.status_code == 200
    
    def test_forms_have_standard_action(self, client: TestClient):
        """Forms have standard action attributes for non-JS fallback."""
        exec_id = create_execution(client)
        exec_service = get_execution_service(None)
        exec_service.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.get(f"/executions/{exec_id}/acceptance")
        # Form should have action attribute
        assert 'action="' in response.text or "action='" in response.text
    
    def test_links_are_real_urls(self, client: TestClient):
        """Navigation links are real URLs, not JavaScript-only."""
        response = client.get("/dashboard")
        assert 'href="/"' in response.text or "href='/'" in response.text
        assert 'href="/workflows"' in response.text or "href='/workflows'" in response.text
        assert 'href="/executions"' in response.text or "href='/executions'" in response.text

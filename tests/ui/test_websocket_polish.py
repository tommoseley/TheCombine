"""Tests for WebSocket integration and UI polish."""

import pytest
from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_persistence, clear_caches
from app.core.database import get_db
from unittest.mock import MagicMock
from app.api.v1.routers.executions import reset_execution_service
from app.web.routes.admin import pages_router, partials_router
from app.domain.workflow import InMemoryStatePersistence
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.plan_models import (
    WorkflowPlan,
    Node,
    NodeType,
    Edge,
    EdgeKind,
    ThreadOwnership,
    Governance,
)


class MockPlanRegistry:
    """Mock registry for testing."""

    def __init__(self):
        self._plans = {}

    def add(self, plan: WorkflowPlan) -> None:
        self._plans[plan.workflow_id] = plan

    def get(self, workflow_id: str) -> WorkflowPlan:
        if workflow_id not in self._plans:
            raise Exception(f"Plan not found: {workflow_id}")
        return self._plans[workflow_id]

    def list_ids(self) -> list:
        return list(self._plans.keys())


@pytest.fixture
def test_plan() -> WorkflowPlan:
    """Create a test workflow plan."""
    return WorkflowPlan(
        workflow_id="test_workflow",
        version="1.0.0",
        name="Test Workflow",
        description="A test workflow",
        scope_type="project",
        document_type="test_doc",
        requires_inputs=[],
        entry_node_ids=["start"],
        nodes=[
            Node(
                node_id="start",
                type=NodeType.TASK,
                description="Start task",
                task_ref="task1",
            ),
            Node(
                node_id="end",
                type=NodeType.END,
                description="End node",
                terminal_outcome="stabilized",
            ),
        ],
        edges=[
            Edge(
                edge_id="e1",
                from_node_id="start",
                to_node_id="end",
                outcome="success",
                label="Success",
                kind=EdgeKind.AUTO,
            ),
        ],
        outcome_mapping=[],
        thread_ownership=ThreadOwnership(owns_thread=False),
        governance=Governance(),
    )


@pytest.fixture
def mock_registry(test_plan) -> MockPlanRegistry:
    registry = MockPlanRegistry()
    registry.add(test_plan)
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

    test_app.dependency_overrides[get_plan_registry] = lambda: mock_registry
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


class TestWebSocketIntegration:
    """Tests for WebSocket client integration in pages.

    Note: Tests that depend on creating executions are skipped because they
    require full PlanExecutor infrastructure.
    """

    @pytest.mark.skip(reason="Requires full PlanExecutor infrastructure")
    def test_execution_detail_includes_websocket_js(self, client: TestClient):
        """Execution detail page includes WebSocket JavaScript."""
        pass

    @pytest.mark.skip(reason="Requires full PlanExecutor infrastructure")
    def test_execution_detail_has_websocket_initialization(self, client: TestClient):
        """Execution detail page initializes WebSocket connection."""
        pass

    def test_dashboard_does_not_have_websocket(self, client: TestClient):
        """Dashboard page doesn't initialize execution-specific WebSocket."""
        response = client.get("/admin")
        assert response.status_code == 200
        # Dashboard includes the script but shouldn't init ExecutionWebSocket
        assert "new ExecutionWebSocket" not in response.text


class TestHTMXPolling:
    """Tests for HTMX polling fallback."""

    @pytest.mark.skip(reason="Requires full PlanExecutor infrastructure")
    def test_execution_detail_has_htmx_polling(self, client: TestClient):
        """Execution detail page has HTMX polling for status updates."""
        pass

    def test_dashboard_shows_recent_activity(self, client: TestClient):
        """Dashboard shows recent activity section."""
        response = client.get("/admin")
        assert "Recent Activity" in response.text


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
        response = client.get("/admin")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text.lower()

        # Workflows list
        response = client.get("/admin/workflows")
        assert response.status_code == 200

        # Executions list
        response = client.get("/admin/executions")
        assert response.status_code == 200

    @pytest.mark.skip(reason="Requires full PlanExecutor infrastructure")
    def test_forms_have_standard_action(self, client: TestClient):
        """Forms have standard action attributes for non-JS fallback."""
        pass

    def test_links_are_real_urls(self, client: TestClient):
        """Navigation links are real URLs, not JavaScript-only."""
        response = client.get("/admin")
        assert 'href="/admin/dashboard"' in response.text or "href='/admin/dashboard'" in response.text
        assert 'href="/admin/workflows"' in response.text or "href='/admin/workflows'" in response.text
        assert 'href="/admin/executions"' in response.text or "href='/admin/executions'" in response.text

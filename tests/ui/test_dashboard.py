"""Tests for dashboard and base layout."""

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
from app.web.routes.admin import pages_router, dashboard_router
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
    """Create mock registry with test plan."""
    registry = MockPlanRegistry()
    registry.add(test_plan)
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

    test_app.dependency_overrides[get_plan_registry] = lambda: mock_registry
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
        """Base template includes HTMX library."""
        response = client.get("/admin")
        assert "htmx.org" in response.text

    def test_includes_tailwind(self, client: TestClient):
        """Base template includes Tailwind CSS."""
        response = client.get("/admin")
        assert "tailwindcss" in response.text

    def test_includes_lucide_icons(self, client: TestClient):
        """Base template includes Lucide icons."""
        response = client.get("/admin")
        assert "lucide" in response.text

    def test_dark_mode_support(self, client: TestClient):
        """Base template supports dark mode via class."""
        response = client.get("/admin")
        assert 'darkMode' in response.text


class TestStaticAssets:
    """Tests for static asset availability."""

    def test_custom_css_served(self, client: TestClient):
        """Custom CSS files are served."""
        response = client.get("/static/css/styles.css")
        assert response.status_code == 200

    @pytest.mark.skip(reason="main.js does not exist - test needs updating")
    def test_custom_js_served(self, client: TestClient):
        """Custom JS files are served."""
        response = client.get("/static/js/main.js")
        assert response.status_code == 200

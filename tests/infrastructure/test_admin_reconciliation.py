"""Intent-first tests for admin instrumentation reconciliation (WS-ADMIN-RECONCILE-001).

These tests encode the Tier 1 postconditions for restoring admin operational
visibility after HTMX admin decommission. All must FAIL before implementation
and PASS after.

Criteria:
1. Telemetry API mounted and returning data
2. Server route for /admin serves SPA
3. SPA Admin Panel renders (route + component exist)
4. Execution list API contract
5. Execution detail API contracts (transcript + QA coverage)
6. No dead admin navigation links
"""

import os
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.auth.dependencies import require_admin
from app.auth.models import User
from uuid import uuid4

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture
def mock_admin_user() -> User:
    return User(
        user_id=str(uuid4()),
        email="admin@test.com",
        name="Test Admin",
        is_active=True,
        email_verified=True,
        is_admin=True,
    )


@pytest.fixture
def client(mock_admin_user):
    async def mock_require_admin():
        return mock_admin_user
    app.dependency_overrides[require_admin] = mock_require_admin
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Criterion 1: Telemetry API mounted and returning data
# ---------------------------------------------------------------------------
class TestCriterion1TelemetryAPIMounted:
    """The telemetry cost endpoint must be reachable via the production app."""

    def test_telemetry_costs_returns_200(self, client):
        """GET /api/v1/telemetry/costs returns HTTP 200."""
        response = client.get("/api/v1/telemetry/costs")
        assert response.status_code == 200, (
            f"GET /api/v1/telemetry/costs must return 200, got {response.status_code}"
        )

    def test_telemetry_costs_schema(self, client):
        """Response contains daily_data array and summary object."""
        response = client.get("/api/v1/telemetry/costs")
        assert response.status_code != 404, "Telemetry costs endpoint must be mounted"
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code} (DB not available in test)")
        data = response.json()
        assert "daily_data" in data, "Response must contain daily_data"
        assert "summary" in data, "Response must contain summary"
        assert isinstance(data["daily_data"], list)

    def test_telemetry_costs_summary_fields(self, client):
        """Summary includes total_cost, total_tokens, total_calls."""
        response = client.get("/api/v1/telemetry/costs")
        assert response.status_code != 404, "Telemetry costs endpoint must be mounted"
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code} (DB not available in test)")
        summary = response.json()["summary"]
        assert "total_cost" in summary, "Summary must contain total_cost"
        assert "total_tokens" in summary, "Summary must contain total_tokens"
        assert "total_calls" in summary, "Summary must contain total_calls"

    def test_telemetry_costs_route_registered(self):
        """The telemetry costs route is registered in the app."""
        cost_paths = [
            r.path for r in app.routes
            if hasattr(r, "path") and "/telemetry/costs" in r.path
        ]
        assert len(cost_paths) > 0, (
            "Telemetry costs route must be registered in the app"
        )


# ---------------------------------------------------------------------------
# Criterion 2: Server route for /admin serves SPA
# ---------------------------------------------------------------------------
class TestCriterion2AdminServerRoute:
    """Navigation to /admin must serve the SPA, not return 404."""

    def test_admin_returns_200(self, client):
        """GET /admin returns HTTP 200."""
        response = client.get("/admin")
        assert response.status_code == 200, (
            f"GET /admin must return 200, got {response.status_code}"
        )

    def test_admin_returns_html(self, client):
        """GET /admin returns text/html content."""
        response = client.get("/admin")
        if response.status_code != 200:
            pytest.skip("/admin route not yet added")
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, (
            f"GET /admin must return text/html, got {content_type}"
        )


# ---------------------------------------------------------------------------
# Criterion 3: SPA Admin Panel renders
# ---------------------------------------------------------------------------
class TestCriterion3SPAAdminPanel:
    """The SPA must route /admin to an AdminPanel component."""

    def test_admin_panel_component_exists(self):
        """An AdminPanel component file exists in the SPA source."""
        component_path = os.path.join(
            REPO_ROOT, "spa", "src", "components", "admin", "AdminPanel.jsx"
        )
        assert os.path.exists(component_path), (
            f"AdminPanel component must exist at {component_path}"
        )

    def test_app_jsx_routes_admin(self):
        """App.jsx has explicit routing for /admin path."""
        app_jsx = os.path.join(REPO_ROOT, "spa", "src", "App.jsx")
        with open(app_jsx) as f:
            content = f.read()
        # Must have an explicit route match for /admin (not just /admin/workbench)
        assert "'/admin'" in content or '"/admin"' in content, (
            "App.jsx must explicitly route the /admin path"
        )
        # Must import AdminPanel
        assert "AdminPanel" in content, (
            "App.jsx must import and use AdminPanel component"
        )


# ---------------------------------------------------------------------------
# Criterion 4: Execution list API contract
# ---------------------------------------------------------------------------
class TestCriterion4ExecutionListContract:
    """Execution list endpoints must return the fields needed for admin browsing."""

    def test_executions_list_returns_200(self, client):
        """GET /api/v1/executions returns HTTP 200."""
        response = client.get("/api/v1/executions")
        assert response.status_code == 200

    def test_executions_list_schema(self, client):
        """Each execution contains required fields."""
        response = client.get("/api/v1/executions")
        data = response.json()
        assert "executions" in data, "Response must contain executions list"
        # If there are executions, verify schema
        for execution in data.get("executions", []):
            assert "execution_id" in execution
            assert "workflow_id" in execution
            assert "status" in execution

    def test_document_workflows_list_route_exists(self, client):
        """GET /api/v1/document-workflows/executions route is registered."""
        response = client.get("/api/v1/document-workflows/executions")
        # 200 with data or 500 (DB not available) — but not 404 (route missing)
        assert response.status_code != 404, (
            "Document workflows executions route must be registered"
        )


# ---------------------------------------------------------------------------
# Criterion 5: Execution detail API contracts (transcript + QA coverage)
# ---------------------------------------------------------------------------
class TestCriterion5ExecutionDetailContracts:
    """Execution detail sub-endpoints must be registered and return structured data."""

    def test_transcript_route_registered(self):
        """The transcript endpoint is registered in the app routes."""
        transcript_paths = [
            r.path for r in app.routes
            if hasattr(r, "path") and "/transcript" in r.path
            and "executions" in r.path
        ]
        assert len(transcript_paths) > 0, (
            "Transcript route /api/v1/executions/{id}/transcript must be registered"
        )

    def test_qa_coverage_route_registered(self):
        """The QA coverage endpoint is registered in the app routes."""
        qa_paths = [
            r.path for r in app.routes
            if hasattr(r, "path") and "/qa-coverage" in r.path
            and "executions" in r.path
        ]
        assert len(qa_paths) > 0, (
            "QA coverage route /api/v1/executions/{id}/qa-coverage must be registered"
        )


# ---------------------------------------------------------------------------
# Criterion 6: No dead admin navigation links
# ---------------------------------------------------------------------------
class TestCriterion6NoDeadAdminLinks:
    """No SPA navigation element may link to a path that returns 404."""

    def test_admin_link_resolves(self, client):
        """The /admin path must not return 404."""
        response = client.get("/admin")
        assert response.status_code != 404, (
            "/admin link in SPA sidecars must not lead to 404"
        )

    def test_admin_workbench_still_works(self, client):
        """GET /admin/workbench continues to work (regression guard)."""
        response = client.get("/admin/workbench")
        assert response.status_code == 200, (
            f"/admin/workbench must still return 200, got {response.status_code}"
        )

    def test_admin_execution_detail_route(self, client):
        """GET /admin/executions/{id} returns 200 (deep-link to execution detail)."""
        response = client.get("/admin/executions/exec-test123")
        assert response.status_code == 200, (
            f"/admin/executions/{{id}} must return 200, got {response.status_code}"
        )

    def test_no_href_to_dead_admin_routes(self):
        """No SPA source file links to removed HTMX admin routes."""
        spa_src = os.path.join(REPO_ROOT, "spa", "src")
        # Check for references to old HTMX admin routes (not /admin or /admin/workbench)
        dead_patterns = [
            "/admin/workflows",
            # Note: /admin/executions is a LIVE route (deep-link to execution detail)
            "/admin/dashboard",
            "/admin/documents",
            "/partials/",
        ]
        for pattern in dead_patterns:
            result = subprocess.run(
                ["grep", "-r", pattern, spa_src],
                capture_output=True,
                text=True,
            )
            # Filter out false positives from /api/v1/admin/ paths
            real_hits = [
                line for line in result.stdout.strip().split("\n")
                if line and "/api/" not in line
            ]
            assert len(real_hits) == 0, (
                f"Found SPA reference to removed route '{pattern}':\n"
                + "\n".join(real_hits)
            )

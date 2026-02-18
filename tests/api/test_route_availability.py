"""Tests for route availability.

Phase 11 Shake-Down: Ensures all expected routes are wired up and responding.
This prevents "dead code" routers that exist but aren't included in main.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.auth.dependencies import require_admin
from app.auth.models import User
from uuid import uuid4


@pytest.fixture
def mock_admin_user() -> User:
    """Create mock admin user."""
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
    """Create test client with admin auth override."""
    async def mock_require_admin():
        return mock_admin_user
    app.dependency_overrides[require_admin] = mock_require_admin
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestHealthRoutes:
    """Health check routes must be available."""
    
    def test_health_liveness(self, client):
        """GET /health returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_readiness(self, client):
        """GET /health/ready returns 200 or 503."""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]  # 503 if DB down
    
    def test_health_detailed(self, client):
        """GET /health/detailed returns 200 or 503."""
        response = client.get("/health/detailed")
        assert response.status_code in [200, 503]


class TestAPIDocumentation:
    """API documentation routes must be available."""
    
    def test_swagger_ui(self, client):
        """GET /docs returns Swagger UI."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_schema(self, client):
        """GET /openapi.json returns schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()


class TestWebUIRoutes:
    """Web UI routes must be available."""
    
    def test_home_page(self, client):
        """GET / returns home page."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_projects_list_page(self, client):
        """GET /projects/list returns projects list page."""
        response = client.get("/projects/list")
        # May return 200 or 500 (DB issues in test), but not 404
        assert response.status_code != 404, "Projects list route not wired up"


class TestDocumentAPIRoutes:
    """Document API routes must be available."""
    
    def test_document_types_route_exists(self, client):
        """GET /api/documents/types route is wired up."""
        response = client.get("/api/documents/types")
        # May return 200 or 500 (DB issues in test), but not 404
        assert response.status_code != 404, "Document types route not wired up"


class TestWorkflowRoutes:
    """Workflow routes must be available (Phase 8-10)."""

    def test_workflows_api_list(self, client):
        """GET /api/v1/workflows returns workflow list."""
        response = client.get("/api/v1/workflows")
        # Should return 200 with list, not 404
        assert response.status_code != 404, "Workflow API route not wired up"


class TestExecutionRoutes:
    """Execution routes must be available (Phase 8-10)."""

    def test_executions_api_list(self, client):
        """GET /api/v1/executions returns execution list."""
        response = client.get("/api/v1/executions")
        # Should return 200 with list, not 404
        assert response.status_code != 404, "Executions API route not wired up"


class TestAuthRoutes:
    """Authentication routes must be available."""

    def test_login_google_redirect(self, client):
        """GET /auth/login/google redirects to OAuth or returns 404 if not configured."""
        response = client.get("/auth/login/google", follow_redirects=False)
        # Should redirect (302) to Google OAuth, or 404 if OAuth not configured
        assert response.status_code in (302, 404), f"Unexpected status {response.status_code}"

    def test_optional_auth_endpoint(self, client):
        """GET /api/optional-auth works without auth."""
        response = client.get("/api/optional-auth")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestIntakeWorkflowRoutes:
    """Intake workflow routes must be available (WS-ADR-025)."""

    def test_intake_route_exists(self, client):
        """GET /intake route is wired up."""
        # Don't follow redirects to detect if route exists
        response = client.get("/intake", follow_redirects=False)
        # Should return 200 (feature enabled + auth), 302 (redirect to login),
        # but not 404 (route not wired)
        assert response.status_code in (200, 302), "Intake route not wired up"

    def test_intake_redirects_to_login_when_unauthenticated(self, client):
        """GET /intake redirects to login when not authenticated."""
        response = client.get("/intake", follow_redirects=False)
        # Without auth, should redirect to login
        assert response.status_code == 302
        assert "login" in response.headers.get("location", "").lower()

    def test_intake_execution_route_exists(self, client):
        """GET /intake/{execution_id} route is wired up."""
        # Don't follow redirects to detect if route exists
        response = client.get(
            "/intake/00000000-0000-0000-0000-000000000000",
            follow_redirects=False,
        )
        # Should redirect (auth required) or return error, but route is wired
        assert response.status_code in (200, 302, 500), \
            "Intake execution route not wired up"
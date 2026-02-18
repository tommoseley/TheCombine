"""Intent-first tests for HTMX admin section removal (WS-ADR-050-002).

These tests encode the Tier 1 postconditions for removing the deprecated
HTMX admin section. All must FAIL before implementation and PASS after.

Criteria:
1. HTMX admin routes return 404
2. No app/ Python file imports the removed admin modules
3. Composer routes preserved (not 404)
4. Admin templates directory does not exist
5. Admin static assets directory does not exist
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
# Criterion 1: HTMX admin routes return 404
# ---------------------------------------------------------------------------
class TestCriterion1AdminRoutesRemoved:
    """All deprecated HTMX admin routes must return 404."""

    @pytest.mark.parametrize("path", [
        "/admin/workflows",
        "/admin/executions",
        "/admin/dashboard",
        "/admin/dashboard/costs",
        "/admin/documents",
        "/partials/executions",
    ])
    def test_htmx_admin_route_returns_404(self, client, path):
        response = client.get(path)
        assert response.status_code == 404, (
            f"{path} must return 404 after HTMX admin removal, "
            f"got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# Criterion 2: No app/ imports of removed admin modules
# ---------------------------------------------------------------------------
class TestCriterion2NoAdminImports:
    """No Python file under app/ should import the removed admin modules."""

    REMOVED_MODULES = [
        "app.web.routes.admin.pages",
        "app.web.routes.admin.dashboard",
        "app.web.routes.admin.documents",
        "app.web.routes.admin.partials",
        "app.web.routes.admin.admin_routes",
    ]

    def test_no_imports_of_removed_modules(self):
        # Use grep to find any remaining imports
        for module in self.REMOVED_MODULES:
            result = subprocess.run(
                ["grep", "-r", module, os.path.join(REPO_ROOT, "app")],
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "", (
                f"Found import of removed module {module}:\n{result.stdout}"
            )


# ---------------------------------------------------------------------------
# Criterion 3: Composer routes preserved
# ---------------------------------------------------------------------------
class TestCriterion3ComposerPreserved:
    """Composer API routes must still be registered (not removed)."""

    def test_composer_route_registered(self):
        """Check the app route table directly — the composer prefix must exist."""
        composer_paths = [
            r.path for r in app.routes
            if hasattr(r, "path") and "/api/admin/composer" in r.path
        ]
        assert len(composer_paths) > 0, (
            "Composer routes (/api/admin/composer/*) must still be registered"
        )


# ---------------------------------------------------------------------------
# Criterion 4: Admin templates directory removed
# ---------------------------------------------------------------------------
class TestCriterion4TemplatesRemoved:
    """The HTMX admin templates directory must not exist."""

    def test_admin_templates_directory_removed(self):
        templates_dir = os.path.join(
            REPO_ROOT, "app", "web", "templates", "admin"
        )
        assert not os.path.exists(templates_dir), (
            f"Admin templates directory must be removed: {templates_dir}"
        )


# ---------------------------------------------------------------------------
# Criterion 5: Admin static assets removed
# ---------------------------------------------------------------------------
class TestCriterion5StaticAssetsRemoved:
    """The HTMX admin static assets directory must not exist."""

    def test_admin_static_directory_removed(self):
        static_dir = os.path.join(
            REPO_ROOT, "app", "web", "static", "admin"
        )
        assert not os.path.exists(static_dir), (
            f"Admin static assets directory must be removed: {static_dir}"
        )

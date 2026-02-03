"""
Tests for the Admin Workbench API endpoints.

These tests verify that the Admin Workbench correctly exposes
Git-canonical configuration from combine-config/.
"""

import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.services.admin_workbench_service import (
    reset_admin_workbench_service,
)
from app.config.package_loader import reset_package_loader


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_admin_workbench_service()
    reset_package_loader()
    yield
    reset_admin_workbench_service()
    reset_package_loader()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestDocumentTypeEndpoints:
    """Tests for document type endpoints."""

    def test_list_document_types(self, client):
        """Should list all document types."""
        response = client.get("/api/v1/admin/workbench/document-types")

        assert response.status_code == 200
        data = response.json()

        assert "document_types" in data
        assert "total" in data
        assert data["total"] >= 2  # project_discovery, primary_implementation_plan

        doc_type_ids = [dt["doc_type_id"] for dt in data["document_types"]]
        assert "project_discovery" in doc_type_ids
        assert "primary_implementation_plan" in doc_type_ids

    def test_get_document_type(self, client):
        """Should get document type details."""
        response = client.get("/api/v1/admin/workbench/document-types/project_discovery")

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["display_name"] == "Project Discovery"
        assert data["version"] == "1.4.0"
        assert data["authority_level"] == "descriptive"
        assert data["creation_mode"] == "llm_generated"
        assert data["scope"] == "project"
        assert data["requires_pgc"] is True
        assert data["is_llm_generated"] is True

    def test_get_document_type_with_version(self, client):
        """Should get specific version of document type."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery",
            params={"version": "1.4.0"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.4.0"

    def test_get_nonexistent_document_type(self, client):
        """Should return 404 for nonexistent document type."""
        response = client.get("/api/v1/admin/workbench/document-types/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "DOCUMENT_TYPE_NOT_FOUND"

    def test_get_nonexistent_version(self, client):
        """Should return 404 for nonexistent version."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery",
            params={"version": "99.0.0"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VERSION_NOT_FOUND"

    def test_list_document_type_versions(self, client):
        """Should list versions of a document type."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery/versions"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert "1.4.0" in data["versions"]
        assert data["active_version"] == "1.4.0"

    def test_get_task_prompt(self, client):
        """Should get task prompt content."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery/task-prompt"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["version"] == "1.4.0"
        assert data["content"] is not None
        assert "Project Discovery" in data["content"]

    def test_get_schema(self, client):
        """Should get output schema."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery/schema"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["schema"] is not None
        assert data["schema"]["title"] == "Project Discovery"

    def test_get_pgc_context(self, client):
        """Should get PGC context content."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery/pgc-context"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["content"] is not None

    def test_get_assembled_prompt(self, client):
        """Should get assembled prompt."""
        response = client.get(
            "/api/v1/admin/workbench/document-types/project_discovery/assembled-prompt"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["prompt"] is not None
        # Should contain role content
        assert "Technical Architect" in data["prompt"]
        # Should contain task content
        assert "Project Discovery" in data["prompt"]


class TestRoleEndpoints:
    """Tests for role endpoints."""

    def test_list_roles(self, client):
        """Should list all roles."""
        response = client.get("/api/v1/admin/workbench/roles")

        assert response.status_code == 200
        data = response.json()

        assert "roles" in data
        assert "total" in data

        role_ids = [r["role_id"] for r in data["roles"]]
        assert "technical_architect" in role_ids
        assert "project_manager" in role_ids

    def test_get_role(self, client):
        """Should get role details."""
        response = client.get("/api/v1/admin/workbench/roles/technical_architect")

        assert response.status_code == 200
        data = response.json()

        assert data["role_id"] == "technical_architect"
        assert data["version"] == "1.0.0"
        assert "Technical Architect" in data["content"]

    def test_get_nonexistent_role(self, client):
        """Should return 404 for nonexistent role."""
        response = client.get("/api/v1/admin/workbench/roles/nonexistent")

        assert response.status_code == 404


class TestTemplateEndpoints:
    """Tests for template endpoints."""

    def test_list_templates(self, client):
        """Should list all templates."""
        response = client.get("/api/v1/admin/workbench/templates")

        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert "total" in data

        template_ids = [t["template_id"] for t in data["templates"]]
        assert "document_generator" in template_ids

    def test_get_template(self, client):
        """Should get template details."""
        response = client.get("/api/v1/admin/workbench/templates/document_generator")

        assert response.status_code == 200
        data = response.json()

        assert data["template_id"] == "document_generator"
        assert data["version"] == "1.0.0"
        assert "$$ROLE_PROMPT" in data["content"]
        assert "$$TASK_PROMPT" in data["content"]

    def test_get_nonexistent_template(self, client):
        """Should return 404 for nonexistent template."""
        response = client.get("/api/v1/admin/workbench/templates/nonexistent")

        assert response.status_code == 404


class TestActiveReleasesEndpoint:
    """Tests for active releases endpoint."""

    def test_get_active_releases(self, client):
        """Should get active releases."""
        response = client.get("/api/v1/admin/workbench/active-releases")

        assert response.status_code == 200
        data = response.json()

        assert "document_types" in data
        assert "roles" in data
        assert "templates" in data
        assert "workflows" in data

        assert data["document_types"]["project_discovery"] == "1.4.0"
        assert data["roles"]["technical_architect"] == "1.0.0"
        assert data["templates"]["document_generator"] == "1.0.0"


class TestCacheEndpoint:
    """Tests for cache management endpoint."""

    def test_invalidate_cache(self, client):
        """Should invalidate cache successfully."""
        response = client.post("/api/v1/admin/workbench/cache/invalidate")

        assert response.status_code == 204

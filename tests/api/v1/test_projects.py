"""Tests for Projects API.

NOTE: These tests require database infrastructure and are skipped in CI.
They use the real app without proper mocking of database/auth dependencies.
"""

import pytest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app

# Skip entire module - tests require database infrastructure not available in CI
pytestmark = pytest.mark.skip(reason="Tests require database infrastructure - needs proper mocking")


@pytest.fixture
def client():
    """Test client for API."""
    return TestClient(app)


class TestProjectsList:
    """Tests for GET /api/v1/projects endpoint."""

    def test_list_returns_structure(self, client):
        """List endpoint returns expected structure."""
        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()

        assert "projects" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data

        assert isinstance(data["projects"], list)

    def test_list_supports_pagination(self, client):
        """List endpoint supports offset and limit."""
        response = client.get("/api/v1/projects?offset=10&limit=5")

        assert response.status_code == 200
        data = response.json()

        assert data["offset"] == 10
        assert data["limit"] == 5

    def test_list_supports_search(self, client):
        """List endpoint supports search parameter."""
        response = client.get("/api/v1/projects?search=test")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data


class TestProjectCreate:
    """Tests for POST /api/v1/projects endpoint."""

    def test_create_requires_name(self, client):
        """Create endpoint requires name field."""
        response = client.post(
            "/api/v1/projects",
            json={"description": "Test description"},
        )

        assert response.status_code == 422  # Validation error

    def test_create_returns_project(self, client):
        """Create endpoint returns project structure."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": f"Test Project {uuid4().hex[:8]}",
                "description": "A test project",
                "icon": "folder",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "project_id" in data
        assert "name" in data
        assert data["name"].startswith("Test Project")


class TestProjectFromIntake:
    """Tests for POST /api/v1/projects/from-intake endpoint."""

    def test_from_intake_requires_execution_id(self, client):
        """From-intake endpoint requires execution_id."""
        response = client.post(
            "/api/v1/projects/from-intake",
            json={
                "intake_document": {"project_name": "Test"},
            },
        )

        assert response.status_code == 422  # Validation error

    def test_from_intake_requires_intake_document(self, client):
        """From-intake endpoint requires intake_document."""
        response = client.post(
            "/api/v1/projects/from-intake",
            json={
                "execution_id": "test-exec-123",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_from_intake_creates_project(self, client):
        """From-intake endpoint creates project with concierge_intake doc."""
        response = client.post(
            "/api/v1/projects/from-intake",
            json={
                "execution_id": f"test-exec-{uuid4().hex[:8]}",
                "intake_document": {
                    "project_name": f"Intake Test {uuid4().hex[:6]}",
                    "summary": {
                        "description": "A project created from intake",
                    },
                },
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "project_id" in data
        # Project ID should be in hyphen format (e.g., IT-001)
        assert "-" in data["project_id"]


class TestProjectGet:
    """Tests for GET /api/v1/projects/{id} endpoint."""

    def test_get_not_found(self, client):
        """Get returns 404 for nonexistent project."""
        response = client.get(f"/api/v1/projects/{uuid4()}")

        assert response.status_code == 404

    def test_get_invalid_id_format(self, client):
        """Get handles invalid ID gracefully."""
        response = client.get("/api/v1/projects/not-a-valid-id")

        # Should return 404 (not found), not 500 (server error)
        assert response.status_code == 404


class TestProjectTree:
    """Tests for GET /api/v1/projects/{id}/tree endpoint."""

    def test_tree_not_found(self, client):
        """Tree returns 404 for nonexistent project."""
        response = client.get(f"/api/v1/projects/{uuid4()}/tree")

        assert response.status_code == 404

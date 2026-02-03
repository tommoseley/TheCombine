"""Tests for Production Line API (ADR-043).

NOTE: These tests require database infrastructure and are skipped in CI.
They use the real app without proper mocking of database/auth dependencies.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.main import app

# Skip entire module - tests require database infrastructure not available in CI
pytestmark = pytest.mark.skip(reason="Tests require database infrastructure - needs proper mocking")


@pytest.fixture
def client():
    """Test client for API."""
    return TestClient(app)


class TestProductionStatus:
    """Tests for /api/v1/production/status endpoint."""

    def test_status_returns_structure(self, client):
        """Status endpoint returns expected structure."""
        response = client.get("/api/v1/production/status?project_id=test-project")

        assert response.status_code == 200
        data = response.json()

        assert "project_id" in data
        assert "line_state" in data
        assert "tracks" in data
        assert "interrupts" in data
        assert "summary" in data

        # Summary has required fields
        summary = data["summary"]
        assert "total" in summary
        assert "stabilized" in summary
        assert "active" in summary
        assert "blocked" in summary
        assert "queued" in summary
        assert "awaiting_operator" in summary

    def test_status_requires_project_id(self, client):
        """Status endpoint requires project_id parameter."""
        response = client.get("/api/v1/production/status")
        assert response.status_code == 422  # Validation error


class TestProductionStart:
    """Tests for /api/v1/production/start endpoint."""

    def test_start_single_document(self, client):
        """Start production for single document."""
        response = client.post(
            "/api/v1/production/start?project_id=test-project&document_type=project_discovery"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "started"
        assert data["project_id"] == "test-project"
        assert data["document_type"] == "project_discovery"

    def test_start_full_line(self, client):
        """Start full line production (no document_type)."""
        response = client.post("/api/v1/production/start?project_id=test-project")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "started"
        assert data["project_id"] == "test-project"
        assert data["mode"] == "full_line"

    def test_start_requires_project_id(self, client):
        """Start endpoint requires project_id parameter."""
        response = client.post("/api/v1/production/start")
        assert response.status_code == 422  # Validation error


class TestProductionEvents:
    """Tests for /api/v1/production/events SSE endpoint.

    Note: SSE endpoints require async testing with httpx or similar.
    These tests verify route registration only.
    """

    @pytest.mark.skip(reason="SSE streaming endpoints require async client")
    def test_events_endpoint_streams(self, client):
        """Events endpoint streams events."""
        # TODO: Implement with async httpx client
        pass

    @pytest.mark.skip(reason="SSE validation happens after stream starts")
    def test_events_requires_project_id(self, client):
        """Events endpoint requires project_id parameter."""
        # Note: FastAPI validates query params before starting stream,
        # but TestClient still hangs waiting for stream
        pass

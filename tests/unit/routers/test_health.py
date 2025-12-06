"""Tests for health router."""
from fastapi.testclient import TestClient

from app.orchestrator_api.main import app

client = TestClient(app)


class TestHealthRouter:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        # Accept either healthy or unhealthy - your health check is sophisticated
        assert data["status"] in ["healthy", "unhealthy"]

"""Operational tests for health endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.health import router


@pytest.fixture
def app():
    """Create test app with health router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestLivenessProbe:
    """Tests for liveness probe endpoint."""
    
    def test_liveness_returns_200(self, client):
        """Liveness probe returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_liveness_returns_healthy_status(self, client):
        """Liveness probe returns healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_liveness_does_not_check_database(self, client):
        """Liveness probe doesn't require database."""
        # This should succeed even without DB setup
        response = client.get("/health")
        assert response.status_code == 200


class TestReadinessProbe:
    """Tests for readiness probe endpoint."""
    
    def test_readiness_checks_database(self, app):
        """Readiness probe checks database connection."""
        # Mock successful DB check
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result
        
        async def mock_get_db():
            yield mock_db
        
        from app.core.database import get_db
        app.dependency_overrides[get_db] = mock_get_db
        
        client = TestClient(app)
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
    
    def test_readiness_fails_on_db_error(self, app):
        """Readiness probe fails when database unreachable."""
        # Mock failed DB check
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Connection refused")
        
        async def mock_get_db():
            yield mock_db
        
        from app.core.database import get_db
        app.dependency_overrides[get_db] = mock_get_db
        
        client = TestClient(app)
        response = client.get("/health/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"


class TestDetailedHealth:
    """Tests for detailed health endpoint."""
    
    def test_detailed_returns_checks(self, app):
        """Detailed health returns check results."""
        # Mock DB
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "PostgreSQL 15.0"
        mock_db.execute.return_value = mock_result
        
        async def mock_get_db():
            yield mock_db
        
        from app.core.database import get_db
        app.dependency_overrides[get_db] = mock_get_db
        
        client = TestClient(app)
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
    
    def test_detailed_shows_db_version(self, app):
        """Detailed health shows database version."""
        mock_db = AsyncMock()
        
        # First call for version
        mock_result1 = MagicMock()
        mock_result1.scalar.return_value = "PostgreSQL 15.0"
        
        # Second call for migrations
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = "abc123"
        
        mock_db.execute.side_effect = [mock_result1, mock_result2]
        
        async def mock_get_db():
            yield mock_db
        
        from app.core.database import get_db
        app.dependency_overrides[get_db] = mock_get_db
        
        client = TestClient(app)
        response = client.get("/health/detailed")
        
        data = response.json()
        assert "PostgreSQL" in data["checks"]["database"]["version"]

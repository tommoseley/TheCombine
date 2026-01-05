"""Tests for dashboard UI pages."""

import pytest
from uuid import uuid4
from datetime import date

from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from app.core.database import get_db

from app.ui.routers.dashboard import (
    router,
    set_telemetry_svc,
    reset_telemetry_svc,
)
from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset telemetry service before each test."""
    reset_telemetry_svc()
    yield
    reset_telemetry_svc()


@pytest.fixture
def store():
    """Create fresh telemetry store."""
    return InMemoryTelemetryStore()


@pytest.fixture
def service(store):
    """Create telemetry service."""
    return TelemetryService(store)



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
def app(service, mock_admin_user):
    """Create test app."""
    set_telemetry_svc(service)
    
    test_app = FastAPI()
    
    # Override admin requirement
    async def mock_require_admin_dep():
        return mock_admin_user
    test_app.dependency_overrides[require_admin] = mock_require_admin_dep
    
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
    
    test_app.include_router(router)
    
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestCostDashboard:
    """Tests for cost dashboard page."""
    
    def test_dashboard_renders(self, client):
        """Cost dashboard page renders."""
        response = client.get("/admin/dashboard/costs")
        
        assert response.status_code == 200
        assert "Cost Dashboard" in response.text
    
    def test_dashboard_shows_summary_cards(self, client):
        """Dashboard shows summary cards."""
        response = client.get("/admin/dashboard/costs")
        
        assert response.status_code == 200
        assert "Total Cost" in response.text
        assert "Total Tokens" in response.text
        assert "API Calls" in response.text
        assert "Success Rate" in response.text
    
    def test_dashboard_shows_averages(self, client):
        """Dashboard shows averages section."""
        response = client.get("/admin/dashboard/costs")
        
        assert response.status_code == 200
        assert "Averages" in response.text
        assert "per day" in response.text
        assert "per call" in response.text
    
    def test_dashboard_shows_daily_breakdown(self, client):
        """Dashboard shows daily breakdown table."""
        response = client.get("/admin/dashboard/costs")
        
        assert response.status_code == 200
        assert "Daily Breakdown" in response.text
    
    def test_dashboard_accepts_days_parameter(self, client):
        """Dashboard accepts days query parameter."""
        response = client.get("/admin/dashboard/costs?days=14")
        
        assert response.status_code == 200
    
    def test_dashboard_rejects_invalid_days(self, client):
        """Dashboard rejects invalid days parameter."""
        response = client.get("/admin/dashboard/costs?days=0")
        
        assert response.status_code == 422  # Validation error
    
    def test_dashboard_limits_days_max(self, client):
        """Dashboard rejects days > 90."""
        response = client.get("/admin/dashboard/costs?days=100")
        
        assert response.status_code == 422


class TestCostDashboardWithData:
    """Tests for dashboard with actual telemetry data."""
    
    @pytest.mark.asyncio
    async def test_dashboard_reflects_costs(self, client, service):
        """Dashboard shows actual cost data."""
        # Log some calls
        await service.log_call(
            call_id=uuid4(),
            execution_id=uuid4(),
            step_id="test",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=200.0,
        )
        
        response = client.get("/admin/dashboard/costs?days=1")
        
        assert response.status_code == 200
        # Should show non-zero cost
        assert "$0.0" not in response.text or "1,500" in response.text


class TestDailyCostsPartial:
    """Tests for daily costs partial endpoint."""
    
    def test_partial_renders(self, client):
        """Daily costs partial renders."""
        response = client.get("/admin/dashboard/costs/api/daily")
        
        assert response.status_code == 200
    
    def test_partial_accepts_days(self, client):
        """Partial accepts days parameter."""
        response = client.get("/admin/dashboard/costs/api/daily?days=7")
        
        assert response.status_code == 200
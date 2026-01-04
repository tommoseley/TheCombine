"""Tests for dashboard UI pages."""

import pytest
from uuid import uuid4
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
def app(service):
    """Create test app."""
    set_telemetry_svc(service)
    
    test_app = FastAPI()
    test_app.include_router(router)
    
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestCostDashboard:
    """Tests for cost dashboard page."""
    
    def test_dashboard_renders(self, client):
        """Cost dashboard page renders."""
        response = client.get("/dashboard/costs")
        
        assert response.status_code == 200
        assert "Cost Dashboard" in response.text
    
    def test_dashboard_shows_summary_cards(self, client):
        """Dashboard shows summary cards."""
        response = client.get("/dashboard/costs")
        
        assert response.status_code == 200
        assert "Total Cost" in response.text
        assert "Total Tokens" in response.text
        assert "API Calls" in response.text
        assert "Success Rate" in response.text
    
    def test_dashboard_shows_averages(self, client):
        """Dashboard shows averages section."""
        response = client.get("/dashboard/costs")
        
        assert response.status_code == 200
        assert "Averages" in response.text
        assert "per day" in response.text
        assert "per call" in response.text
    
    def test_dashboard_shows_daily_breakdown(self, client):
        """Dashboard shows daily breakdown table."""
        response = client.get("/dashboard/costs")
        
        assert response.status_code == 200
        assert "Daily Breakdown" in response.text
    
    def test_dashboard_accepts_days_parameter(self, client):
        """Dashboard accepts days query parameter."""
        response = client.get("/dashboard/costs?days=14")
        
        assert response.status_code == 200
    
    def test_dashboard_rejects_invalid_days(self, client):
        """Dashboard rejects invalid days parameter."""
        response = client.get("/dashboard/costs?days=0")
        
        assert response.status_code == 422  # Validation error
    
    def test_dashboard_limits_days_max(self, client):
        """Dashboard rejects days > 90."""
        response = client.get("/dashboard/costs?days=100")
        
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
        
        response = client.get("/dashboard/costs?days=1")
        
        assert response.status_code == 200
        # Should show non-zero cost
        assert "$0.0" not in response.text or "1,500" in response.text


class TestDailyCostsPartial:
    """Tests for daily costs partial endpoint."""
    
    def test_partial_renders(self, client):
        """Daily costs partial renders."""
        response = client.get("/dashboard/costs/api/daily")
        
        assert response.status_code == 200
    
    def test_partial_accepts_days(self, client):
        """Partial accepts days parameter."""
        response = client.get("/dashboard/costs/api/daily?days=7")
        
        assert response.status_code == 200

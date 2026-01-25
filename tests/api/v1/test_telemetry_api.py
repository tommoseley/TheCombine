"""Tests for Telemetry API."""

import pytest
from uuid import uuid4
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers.telemetry import (
    router,
    reset_telemetry_service,
)
from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset telemetry service before each test."""
    reset_telemetry_service()
    yield
    reset_telemetry_service()


@pytest.fixture
def app():
    """Create test app."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestGetTelemetrySummary:
    """Tests for GET /telemetry/summary."""
    
    def test_summary_endpoint_exists(self, client):
        """Summary endpoint returns 200."""
        response = client.get("/api/v1/telemetry/summary")
        assert response.status_code == 200
    
    def test_summary_returns_expected_fields(self, client):
        """Summary returns expected fields."""
        response = client.get("/api/v1/telemetry/summary")
        data = response.json()
        
        assert "total_calls" in data
        assert "total_cost_usd" in data
        assert "total_tokens" in data
        assert "avg_cost_per_call" in data
        assert "success_rate" in data
    
    def test_summary_empty_returns_zeros(self, client):
        """Summary with no data returns zeros."""
        response = client.get("/api/v1/telemetry/summary")
        data = response.json()
        
        assert data["total_calls"] == 0
        assert data["total_cost_usd"] == 0.0
        assert data["total_tokens"] == 0


class TestGetDailyCosts:
    """Tests for GET /telemetry/costs/daily."""
    
    def test_daily_costs_endpoint_exists(self, client):
        """Daily costs endpoint returns 200."""
        response = client.get("/api/v1/telemetry/costs/daily")
        assert response.status_code == 200
    
    def test_daily_costs_returns_expected_fields(self, client):
        """Daily costs returns expected fields."""
        response = client.get("/api/v1/telemetry/costs/daily")
        data = response.json()
        
        assert "total_cost_usd" in data
        assert "input_tokens" in data
        assert "output_tokens" in data
        assert "call_count" in data
        assert "error_count" in data
        assert "avg_latency_ms" in data
    
    def test_daily_costs_accepts_date_param(self, client):
        """Daily costs accepts date parameter."""
        response = client.get("/api/v1/telemetry/costs/daily?target_date=2026-01-01")
        assert response.status_code == 200


class TestGetExecutionCosts:
    """Tests for GET /telemetry/executions/{id}/costs."""
    
    def test_execution_not_found(self, client):
        """Non-existent execution returns 404."""
        response = client.get(f"/api/v1/telemetry/executions/{uuid4()}/costs")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "EXECUTION_NOT_FOUND"
    
    def test_execution_invalid_uuid(self, client):
        """Invalid UUID returns 422."""
        response = client.get("/api/v1/telemetry/executions/not-a-uuid/costs")
        assert response.status_code == 422


class TestGetWorkflowStats:
    """Tests for GET /telemetry/workflows/{id}/stats."""
    
    def test_workflow_stats_endpoint_exists(self, client):
        """Workflow stats endpoint returns 200."""
        response = client.get("/api/v1/telemetry/workflows/test-workflow/stats")
        assert response.status_code == 200
    
    def test_workflow_stats_returns_expected_fields(self, client):
        """Workflow stats returns expected fields."""
        response = client.get("/api/v1/telemetry/workflows/test-workflow/stats")
        data = response.json()
        
        assert data["workflow_id"] == "test-workflow"
        assert "execution_count" in data
        assert "completed_count" in data
        assert "failed_count" in data
        assert "total_cost_usd" in data
        assert "avg_cost_usd" in data
        assert "avg_duration_ms" in data

"""
Unit tests for metrics router endpoints (PIPELINE-175D)

Tests FastAPI router layer with mocked service.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.orchestrator_api.main import app
from app.orchestrator_api.services.token_metrics_types import (
    MetricsSummary,
    PipelineMetrics,
    PipelineSummary,
    DailyCost,
    PhaseMetricsInternal
)

client = TestClient(app)


class TestMetricsSummaryEndpoint:
    """Test GET /metrics/summary"""
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_summary_success(self, mock_service_class):
        """
        Given: Service returns valid MetricsSummary
        When: GET /metrics/summary
        Then: Returns 200 with MetricsSummaryResponse JSON
        """
        mock_service = Mock()
        mock_service.get_summary.return_value = MetricsSummary(
            total_pipelines=10,
            total_cost_usd=5.50,
            total_input_tokens=15000,
            total_output_tokens=25000,
            success_count=7,
            failure_count=3,
            last_usage_timestamp=datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        )
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_pipelines"] == 10
        assert data["total_cost_usd"] == 5.50
        assert data["total_input_tokens"] == 15000
        assert data["total_output_tokens"] == 25000
        assert data["success_count"] == 7
        assert data["failure_count"] == 3
        # Note: last_usage_timestamp excluded from response (ADR-013)
        assert "last_usage_timestamp" not in data
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_summary_no_data(self, mock_service_class):
        """
        Given: Service returns MetricsSummary with zeros
        When: GET /metrics/summary
        Then: Returns 200 with zeros (not 404)
        """
        mock_service = Mock()
        mock_service.get_summary.return_value = MetricsSummary(
            total_pipelines=0,
            total_cost_usd=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            success_count=0,
            failure_count=0,
            last_usage_timestamp=None
        )
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_pipelines"] == 0
        assert data["total_cost_usd"] == 0.0


class TestPipelineMetricsEndpoint:
    """Test GET /metrics/pipeline/{pipeline_id}"""
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_pipeline_metrics_success(self, mock_service_class):
        """
        Given: Service returns PipelineMetrics
        When: GET /metrics/pipeline/{pipeline_id}
        Then: Returns 200 with PipelineMetricsResponse JSON
        """
        mock_service = Mock()
        mock_service.get_pipeline_metrics.return_value = PipelineMetrics(
            pipeline_id="test-123",
            status="completed",
            current_phase="commit_phase",
            epic_description="Test Epic",
            total_cost_usd=2.50,
            total_input_tokens=3500,
            total_output_tokens=5500,
            phase_breakdown=[
                PhaseMetricsInternal(
                    phase_name="pm_phase",
                    role_name="pm",
                    input_tokens=1500,
                    output_tokens=2500,
                    cost_usd=0.025,
                    execution_time_ms=2500,
                    timestamp="2024-12-06T10:00:00+00:00"
                )
            ]
        )
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/pipeline/test-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_id"] == "test-123"
        assert data["status"] == "completed"
        assert data["total_cost_usd"] == 2.50
        assert len(data["phase_breakdown"]) == 1
        assert data["phase_breakdown"][0]["phase_name"] == "pm_phase"
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_pipeline_metrics_not_found(self, mock_service_class):
        """
        Given: Service returns None (pipeline not found)
        When: GET /metrics/pipeline/{pipeline_id}
        Then: Returns 404
        """
        mock_service = Mock()
        mock_service.get_pipeline_metrics.return_value = None
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/pipeline/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestRecentPipelinesEndpoint:
    """Test GET /metrics/recent"""
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_recent_pipelines_success(self, mock_service_class):
        """
        Given: Service returns list of PipelineSummary
        When: GET /metrics/recent
        Then: Returns 200 with array of summaries
        """
        mock_service = Mock()
        mock_service.get_recent_pipelines.return_value = [
            PipelineSummary(
                pipeline_id="test-1",
                epic_description="Epic 1",
                status="completed",
                total_cost_usd=1.50,
                total_tokens=5000,
                created_at=datetime(2024, 12, 6, 10, 0, 0)
            ),
            PipelineSummary(
                pipeline_id="test-2",
                epic_description=None,
                status="in_progress",
                total_cost_usd=0.75,
                total_tokens=2500,
                created_at=datetime(2024, 12, 6, 11, 0, 0)
            )
        ]
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/recent")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["pipeline_id"] == "test-1"
        assert data[0]["epic_description"] == "Epic 1"
        assert data[1]["epic_description"] is None
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_recent_pipelines_with_limit(self, mock_service_class):
        """
        Given: limit query parameter provided
        When: GET /metrics/recent?limit=5
        Then: Service called with limit=5
        """
        mock_service = Mock()
        mock_service.get_recent_pipelines.return_value = []
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/recent?limit=5")
        
        assert response.status_code == 200
        mock_service.get_recent_pipelines.assert_called_once_with(limit=5)
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_recent_pipelines_empty(self, mock_service_class):
        """
        Given: Service returns empty list
        When: GET /metrics/recent
        Then: Returns 200 with empty array (not 404)
        """
        mock_service = Mock()
        mock_service.get_recent_pipelines.return_value = []
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/recent")
        
        assert response.status_code == 200
        assert response.json() == []


class TestDailyCostsEndpoint:
    """Test GET /metrics/daily-costs"""
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_daily_costs_success(self, mock_service_class):
        """
        Given: Service returns list of DailyCost
        When: GET /metrics/daily-costs
        Then: Returns 200 with array of daily costs
        """
        mock_service = Mock()
        mock_service.get_daily_costs.return_value = [
            DailyCost(date="2024-12-04", total_cost_usd=2.50),
            DailyCost(date="2024-12-05", total_cost_usd=3.75),
            DailyCost(date="2024-12-06", total_cost_usd=1.25)
        ]
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/daily-costs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["date"] == "2024-12-04"
        assert data[0]["total_cost_usd"] == 2.50
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_daily_costs_with_days_parameter(self, mock_service_class):
        """
        Given: days query parameter provided
        When: GET /metrics/daily-costs?days=3
        Then: Service called with days=3
        """
        mock_service = Mock()
        mock_service.get_daily_costs.return_value = []
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/daily-costs?days=3")
        
        assert response.status_code == 200
        mock_service.get_daily_costs.assert_called_once_with(days=3)
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_daily_costs_empty(self, mock_service_class):
        """
        Given: Service returns empty list
        When: GET /metrics/daily-costs
        Then: Returns 200 with empty array
        """
        mock_service = Mock()
        mock_service.get_daily_costs.return_value = []
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/daily-costs")
        
        assert response.status_code == 200
        assert response.json() == []


class TestMetricsOverviewHTMLEndpoint:
    """Test GET /metrics (HTML template)"""
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_metrics_overview_renders_template(self, mock_service_class):
        """
        Given: Service returns valid data
        When: GET /metrics (HTML)
        Then: Returns 200 with HTML content
        """
        mock_service = Mock()
        mock_service.get_summary.return_value = MetricsSummary(
            total_pipelines=10,
            total_cost_usd=5.50,
            total_input_tokens=15000,
            total_output_tokens=25000,
            success_count=7,
            failure_count=3,
            last_usage_timestamp=datetime.now(timezone.utc)
        )
        mock_service.get_recent_pipelines.return_value = []
        mock_service.get_daily_costs.return_value = []
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics", headers={"Accept": "text/html"})
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Metrics Dashboard" in response.content
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_metrics_overview_no_data(self, mock_service_class):
        """
        Given: Service returns empty/zero data
        When: GET /metrics
        Then: Returns 200 with HTML showing "No data" messages
        """
        mock_service = Mock()
        mock_service.get_summary.return_value = MetricsSummary(
            total_pipelines=0,
            total_cost_usd=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            success_count=0,
            failure_count=0,
            last_usage_timestamp=None
        )
        mock_service.get_recent_pipelines.return_value = []
        mock_service.get_daily_costs.return_value = []
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics")
        
        assert response.status_code == 200
        # Template should handle zero data gracefully


class TestMetricsPipelineDetailHTMLEndpoint:
    """Test GET /metrics/{pipeline_id} (HTML template)"""
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_pipeline_detail_renders_template(self, mock_service_class):
        """
        Given: Pipeline exists
        When: GET /metrics/{pipeline_id} (HTML)
        Then: Returns 200 with HTML detail page
        """
        mock_service = Mock()
        mock_service.get_pipeline_metrics.return_value = PipelineMetrics(
            pipeline_id="test-123",
            status="completed",
            current_phase="commit_phase",
            epic_description="Test Epic",
            total_cost_usd=2.50,
            total_input_tokens=3500,
            total_output_tokens=5500,
            phase_breakdown=[]
        )
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/test-123", headers={"Accept": "text/html"})
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"test-123" in response.content
    
    @patch('app.orchestrator_api.routers.metrics.TokenMetricsService')
    def test_get_pipeline_detail_not_found(self, mock_service_class):
        """
        Given: Pipeline does not exist
        When: GET /metrics/{pipeline_id} (HTML)
        Then: Returns 404
        """
        mock_service = Mock()
        mock_service.get_pipeline_metrics.return_value = None
        mock_service_class.return_value = mock_service
        
        response = client.get("/metrics/nonexistent")
        
        assert response.status_code == 404
"""
Unit tests for TokenMetricsService (PIPELINE-175D)

Tests business logic layer for metrics aggregation.
All repository calls are mocked - no database required.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from app.orchestrator_api.services.token_metrics_service import TokenMetricsService
from app.orchestrator_api.services.token_metrics_types import (
    MetricsSummary,
    PipelineMetrics,
    PipelineSummary,
    DailyCost,
    PhaseMetricsInternal
)


class TestTokenMetricsServiceGetSummary:
    """Test get_summary() method"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_summary_success(self, mock_session_ctx, mock_repo_class):
        """
        Given: Repository returns valid aggregates
        When: get_summary() called
        Then: Returns MetricsSummary with correct totals
        """
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_system_aggregates.return_value = {
            "count": 10,
            "total_cost": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "last_timestamp": datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        }
        mock_repo_class.return_value = mock_repo
        
        # Mock session for success/failure counts
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().scalar.side_effect = [7, 3]  # 7 success, 3 failures
        mock_session_ctx.return_value = mock_session
        
        # Execute
        service = TokenMetricsService()
        result = service.get_summary()
        
        # Assert
        assert isinstance(result, MetricsSummary)
        assert result.total_pipelines == 10
        assert result.total_cost_usd == 5.50
        assert result.total_input_tokens == 15000
        assert result.total_output_tokens == 25000
        assert result.success_count == 7
        assert result.failure_count == 3
        assert result.last_usage_timestamp == datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_get_summary_repository_raises_exception(self, mock_repo_class):
        """
        Given: Repository raises exception
        When: get_summary() called
        Then: Returns safe defaults (zeros/None) and logs warning
        """
        mock_repo = Mock()
        mock_repo.get_system_aggregates.side_effect = RuntimeError("DB connection failed")
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_summary()
        
        # Should return safe defaults
        assert result.total_pipelines == 0
        assert result.total_cost_usd == 0.0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.last_usage_timestamp is None
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_summary_zero_pipelines(self, mock_session_ctx, mock_repo_class):
        """
        Given: No pipelines in system
        When: get_summary() called
        Then: Returns MetricsSummary with zeros
        """
        mock_repo = Mock()
        mock_repo.get_system_aggregates.return_value = {
            "count": 0,
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "last_timestamp": None
        }
        mock_repo_class.return_value = mock_repo
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().scalar.side_effect = [0, 0]
        mock_session_ctx.return_value = mock_session
        
        service = TokenMetricsService()
        result = service.get_summary()
        
        assert result.total_pipelines == 0
        assert result.total_cost_usd == 0.0
        assert result.last_usage_timestamp is None


class TestTokenMetricsServiceGetPipelineMetrics:
    """Test get_pipeline_metrics() method"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_get_pipeline_metrics_success(self, mock_pipeline_repo_class, mock_usage_repo_class):
        """
        Given: Pipeline exists with usage records
        When: get_pipeline_metrics(pipeline_id) called
        Then: Returns PipelineMetrics with phase breakdown
        """
        # Mock pipeline repository
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.return_value = {
            "pipeline_id": "test-123",
            "status": "completed",
            "current_phase": "ba_phase",
            "epic_description": "Test Epic"
        }
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        # Mock usage repository
        mock_usage_repo = Mock()
        mock_usage_record_1 = Mock()
        mock_usage_record_1.phase_name = "pm_phase"
        mock_usage_record_1.role_name = "pm"
        mock_usage_record_1.input_tokens = 1500
        mock_usage_record_1.output_tokens = 2500
        mock_usage_record_1.cost_usd = 0.025
        mock_usage_record_1.execution_time_ms = 2500
        mock_usage_record_1.used_at = datetime(2024, 12, 6, 10, 0, 0, tzinfo=timezone.utc)
        
        mock_usage_record_2 = Mock()
        mock_usage_record_2.phase_name = "architect_phase"
        mock_usage_record_2.role_name = "architect"
        mock_usage_record_2.input_tokens = 2000
        mock_usage_record_2.output_tokens = 3000
        mock_usage_record_2.cost_usd = 0.035
        mock_usage_record_2.execution_time_ms = 3200
        mock_usage_record_2.used_at = datetime(2024, 12, 6, 10, 5, 0, tzinfo=timezone.utc)
        
        mock_usage_repo.get_pipeline_usage.return_value = [
            mock_usage_record_1,
            mock_usage_record_2
        ]
        mock_usage_repo_class.return_value = mock_usage_repo
        
        # Execute
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("test-123")
        
        # Assert
        assert result is not None
        assert isinstance(result, PipelineMetrics)
        assert result.pipeline_id == "test-123"
        assert result.status == "completed"
        assert result.total_cost_usd == pytest.approx(0.060, rel=1e-9)
        assert result.total_input_tokens == 3500
        assert result.total_output_tokens == 5500
        assert len(result.phase_breakdown) == 2
        
        # Check phase breakdown
        assert result.phase_breakdown[0].phase_name == "pm_phase"
        assert result.phase_breakdown[0].input_tokens == 1500
        assert result.phase_breakdown[1].phase_name == "architect_phase"
        assert result.phase_breakdown[1].input_tokens == 2000
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_get_pipeline_metrics_not_found(self, mock_pipeline_repo_class):
        """
        Given: Pipeline does not exist
        When: get_pipeline_metrics(pipeline_id) called
        Then: Returns None
        """
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.return_value = None
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("nonexistent-id")
        
        assert result is None
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_get_pipeline_metrics_repository_raises_exception(self, mock_pipeline_repo_class):
        """
        Given: Repository raises exception
        When: get_pipeline_metrics() called
        Then: Returns None and logs warning
        """
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.side_effect = RuntimeError("DB error")
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("test-123")
        
        assert result is None
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_get_pipeline_metrics_no_usage_records(self, mock_pipeline_repo_class, mock_usage_repo_class):
        """
        Given: Pipeline exists but has no usage records
        When: get_pipeline_metrics() called
        Then: Returns PipelineMetrics with empty phase_breakdown
        """
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.return_value = {
            "pipeline_id": "test-123",
            "status": "in_progress",
            "current_phase": "pm_phase",
            "epic_description": "New Pipeline"
        }
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        mock_usage_repo = Mock()
        mock_usage_repo.get_pipeline_usage.return_value = []
        mock_usage_repo_class.return_value = mock_usage_repo
        
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("test-123")
        
        assert result is not None
        assert result.total_cost_usd == 0.0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
        assert len(result.phase_breakdown) == 0
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_get_pipeline_metrics_null_token_values(self, mock_pipeline_repo_class, mock_usage_repo_class):
        """
        Given: Usage records have NULL token/cost values
        When: get_pipeline_metrics() called
        Then: Treats NULLs as zeros, returns valid metrics
        """
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.return_value = {
            "pipeline_id": "test-123",
            "status": "completed",
            "current_phase": "commit_phase",
            "epic_description": "Test"
        }
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        mock_usage_repo = Mock()
        mock_record = Mock()
        mock_record.phase_name = "pm_phase"
        mock_record.role_name = "pm"
        mock_record.input_tokens = None
        mock_record.output_tokens = None
        mock_record.cost_usd = None
        mock_record.execution_time_ms = None
        mock_record.used_at = datetime.now(timezone.utc)
        
        mock_usage_repo.get_pipeline_usage.return_value = [mock_record]
        mock_usage_repo_class.return_value = mock_usage_repo
        
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("test-123")
        
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
        assert result.total_cost_usd == 0.0


class TestTokenMetricsServiceGetRecentPipelines:
    """Test get_recent_pipelines() method"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_recent_pipelines_success(self, mock_session_ctx):
        """
        Given: Database has pipelines with usage data
        When: get_recent_pipelines() called
        Then: Returns list of PipelineSummary objects
        """
        # Mock database result
        mock_row1 = Mock()
        mock_row1.pipeline_id = "test-1"
        mock_row1.status = "completed"
        mock_row1.artifacts = '{"epic": {"description": "Test Epic 1"}}'
        mock_row1.created_at = datetime(2024, 12, 6, 10, 0, 0)
        mock_row1.total_cost = Decimal("1.50")
        mock_row1.total_tokens = 5000
        
        mock_row2 = Mock()
        mock_row2.pipeline_id = "test-2"
        mock_row2.status = "in_progress"
        mock_row2.artifacts = '{"pm": {"epic_description": "Test Epic 2"}}'
        mock_row2.created_at = datetime(2024, 12, 6, 11, 0, 0)
        mock_row2.total_cost = Decimal("0.75")
        mock_row2.total_tokens = 2500
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = [mock_row1, mock_row2]
        mock_session_ctx.return_value = mock_session
        
        # Execute
        service = TokenMetricsService()
        result = service.get_recent_pipelines(limit=20)
        
        # Assert
        assert len(result) == 2
        assert isinstance(result[0], PipelineSummary)
        assert result[0].pipeline_id == "test-1"
        assert result[0].epic_description == "Test Epic 1"
        assert result[0].total_cost_usd == 1.50
        assert result[1].pipeline_id == "test-2"
        assert result[1].epic_description == "Test Epic 2"
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_recent_pipelines_no_epic_available(self, mock_session_ctx):
        """
        Given: Pipeline has no epic in artifacts
        When: get_recent_pipelines() called
        Then: Returns PipelineSummary with epic_description=None
        """
        mock_row = Mock()
        mock_row.pipeline_id = "test-1"
        mock_row.status = "completed"
        mock_row.artifacts = '{}'  # Empty artifacts
        mock_row.created_at = datetime.now()
        mock_row.total_cost = Decimal("1.00")
        mock_row.total_tokens = 3000
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = [mock_row]
        mock_session_ctx.return_value = mock_session
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        assert len(result) == 1
        assert result[0].epic_description is None
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_recent_pipelines_malformed_json(self, mock_session_ctx):
        """
        Given: Pipeline has malformed JSON in artifacts
        When: get_recent_pipelines() called
        Then: Returns PipelineSummary with epic_description=None (defensive)
        """
        mock_row = Mock()
        mock_row.pipeline_id = "test-1"
        mock_row.status = "completed"
        mock_row.artifacts = '{invalid json'
        mock_row.created_at = datetime.now()
        mock_row.total_cost = Decimal("0.50")
        mock_row.total_tokens = 1000
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = [mock_row]
        mock_session_ctx.return_value = mock_session
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        assert len(result) == 1
        assert result[0].epic_description is None
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_recent_pipelines_database_raises_exception(self, mock_session_ctx):
        """
        Given: Database query raises exception
        When: get_recent_pipelines() called
        Then: Returns empty list and logs warning
        """
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute.side_effect = RuntimeError("DB error")
        mock_session_ctx.return_value = mock_session
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        assert result == []
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_recent_pipelines_respects_limit(self, mock_session_ctx):
        """
        Given: Database has many pipelines
        When: get_recent_pipelines(limit=5) called
        Then: SQL query includes LIMIT parameter
        """
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = []
        mock_session_ctx.return_value = mock_session
        
        service = TokenMetricsService()
        service.get_recent_pipelines(limit=5)
        
        # Verify execute was called with limit parameter
        call_args = mock_session.execute.call_args
        # call_args is (args, kwargs), parameters are in args[1]
        assert call_args[0][1] == {"limit": 5}


class TestTokenMetricsServiceGetDailyCosts:
    """Test get_daily_costs() method"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.datetime')
    def test_get_daily_costs_success(self, mock_datetime, mock_repo_class):
        """
        Given: Repository returns daily aggregates
        When: get_daily_costs(days=7) called
        Then: Returns list of DailyCost with filled gaps
        """
        # Fix current time
        fixed_now = datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Mock repository
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.return_value = [
            {"date": "2024-12-04", "total_cost": 2.50},
            {"date": "2024-12-05", "total_cost": 3.75},
            {"date": "2024-12-06", "total_cost": 1.25}
        ]
        mock_repo_class.return_value = mock_repo
        
        # Execute
        service = TokenMetricsService()
        result = service.get_daily_costs(days=7)
        
        # Assert
        assert len(result) == 7
        assert all(isinstance(day, DailyCost) for day in result)
        
        # Check that missing dates get 0.0
        date_to_cost = {day.date: day.total_cost_usd for day in result}
        assert date_to_cost.get("2024-11-30", 0.0) == 0.0  # Missing date
        assert date_to_cost.get("2024-12-04") == 2.50
        assert date_to_cost.get("2024-12-05") == 3.75
        assert date_to_cost.get("2024-12-06") == 1.25
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_get_daily_costs_no_data(self, mock_repo_class):
        """
        Given: Repository returns empty aggregates
        When: get_daily_costs() called
        Then: Returns list of DailyCost with all zeros
        """
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.return_value = []
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_daily_costs(days=3)
        
        assert len(result) == 3
        assert all(day.total_cost_usd == 0.0 for day in result)
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_get_daily_costs_repository_raises_exception(self, mock_repo_class):
        """
        Given: Repository raises exception
        When: get_daily_costs() called
        Then: Returns empty list and logs warning
        """
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.side_effect = RuntimeError("DB error")
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_daily_costs(days=7)
        
        assert result == []


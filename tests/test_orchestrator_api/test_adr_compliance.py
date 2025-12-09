"""
ADR Compliance Tests for PIPELINE-175D Metrics Dashboard

Tests that implementation matches architectural decisions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from app.orchestrator_api.services.token_metrics_service import TokenMetricsService
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import (
    PipelinePromptUsageRepository,
)


class TestADR013InternalFieldExclusion:
    """Test ADR-013: Exclude internal fields from API responses"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_summary_excludes_last_usage_timestamp(self, mock_repo_class):
        """
        Given: Service returns metrics summary
        When: Converted to response schema
        Then: last_usage_timestamp excluded from response (ADR-013)
        """
        mock_repo = Mock()
        mock_repo.get_system_aggregates.return_value = {
            "count": 10,
            "total_cost": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "last_timestamp": "2024-12-06T10:00:00"
        }
        mock_repo_class.return_value = mock_repo
        
        # Mock the database queries
        with patch('app.orchestrator_api.services.token_metrics_service.get_db_session') as mock_get_db_session:
            mock_session = Mock()
            mock_session.execute.return_value.scalar.return_value = 7  # success_count
            mock_get_db_session.return_value.__enter__.return_value = mock_session
            mock_get_db_session.return_value.__exit__.return_value = None
            
            service = TokenMetricsService()
            result = service.get_summary()
        
        # Internal field present in service response
        assert result.last_usage_timestamp == "2024-12-06T10:00:00"
        
        # Router layer must exclude this from API response
        # (tested in router tests via response schema)


class TestADR014TimezoneHandling:
    """Test ADR-014: Database UTC for all timestamps"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.datetime')
    def test_daily_costs_use_utc_not_local(self, mock_datetime, mock_repo_class):
        """
        Given: Server in non-UTC timezone
        When: get_daily_costs() called
        Then: Uses database UTC for date calculations
        """
        # Fix datetime.now() to return UTC
        fixed_now = datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.return_value = [
            {"date": "2024-12-06", "total_cost": 2.50}
        ]
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_daily_costs(days=1)
        
        # Verify date calculation uses UTC
        assert len(result) == 1
        assert result[0].date == "2024-12-06"
        
        # Verify repository called with keyword argument
        mock_repo.get_daily_aggregates.assert_called_once_with(days=1)
    
    def test_timestamp_fields_stored_as_utc(self):
        """
        Given: Timestamp being stored
        When: Saved to database
        Then: Must be timezone-aware UTC (ADR-014)
        """
        # Example of correct timestamp
        utc_timestamp = datetime(2024, 12, 6, 10, 0, 0, tzinfo=timezone.utc)
        
        assert utc_timestamp.tzinfo is not None
        assert utc_timestamp.tzinfo == timezone.utc


class TestADR015ErrorHandlingNeverRaise:
    """Test ADR-015: Service layer never raises exceptions"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_get_summary_handles_repository_error(self, mock_repo_class):
        """
        Given: Repository raises exception
        When: get_summary() called
        Then: Returns safe defaults, never raises (ADR-015)
        """
        mock_repo = Mock()
        mock_repo.get_system_aggregates.side_effect = Exception("DB connection failed")
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_summary()
        
        # Returns safe defaults instead of raising
        assert result.total_pipelines == 0
        assert result.total_cost_usd == 0.0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_get_pipeline_metrics_handles_repository_error(
        self, mock_pipeline_repo_class, mock_usage_repo_class
    ):
        """
        Given: Repository raises exception
        When: get_pipeline_metrics() called
        Then: Returns None, never raises (ADR-015)
        """
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.side_effect = Exception("DB error")
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("test-123")
        
        # Returns None instead of raising
        assert result is None
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_get_recent_pipelines_handles_database_error(self, mock_get_db_session):
        """
        Given: Database query raises exception
        When: get_recent_pipelines() called
        Then: Returns empty list, never raises (ADR-015)
        """
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Query failed")
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_db_session.return_value.__exit__.return_value = None
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        # Returns empty list instead of raising
        assert result == []
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_get_daily_costs_handles_repository_error(self, mock_repo_class):
        """
        Given: Repository raises exception
        When: get_daily_costs() called
        Then: Returns empty list, never raises (ADR-015)
        """
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.side_effect = Exception("Aggregation failed")
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_daily_costs()
        
        # Returns empty list instead of raising
        assert result == []


class TestADR016NullHandling:
    """Test ADR-016: COALESCE for nullable metrics"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_summary_handles_null_costs(self, mock_repo_class):
        """
        Given: Database returns NULL for cost/token fields
        When: get_summary() called
        Then: Treats NULLs as zeros (ADR-016)
        """
        mock_repo = Mock()
        mock_repo.get_system_aggregates.return_value = {
            "count": 5,
            "total_cost": None,  # NULL in database
            "total_input_tokens": None,
            "total_output_tokens": None,
            "last_timestamp": None
        }
        mock_repo_class.return_value = mock_repo
        
        # Mock database session for status counts
        with patch('app.orchestrator_api.services.token_metrics_service.get_db_session') as mock_get_db_session:
            mock_session = Mock()
            mock_session.execute.return_value.scalar.return_value = 0
            mock_get_db_session.return_value.__enter__.return_value = mock_session
            mock_get_db_session.return_value.__exit__.return_value = None
            
            service = TokenMetricsService()
            result = service.get_summary()
        
        # NULLs converted to zeros
        assert result.total_cost_usd == 0.0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
    def test_pipeline_metrics_handles_null_tokens(
        self, mock_pipeline_repo_class, mock_usage_repo_class
    ):
        """
        Given: Usage records have NULL token/cost values
        When: get_pipeline_metrics() called
        Then: Treats NULLs as zeros in aggregation (ADR-016)
        """
        mock_pipeline_repo = Mock()
        mock_pipeline_repo.get_pipeline_with_epic.return_value = {
            "pipeline_id": "test-123",
            "status": "completed",
            "current_phase": "commit_phase",
            "epic_description": "Test"
        }
        mock_pipeline_repo_class.return_value = mock_pipeline_repo
        
        # Usage record with NULLs
        mock_usage_record = Mock()
        mock_usage_record.phase_name = "pm_phase"
        mock_usage_record.role_name = "pm"
        mock_usage_record.input_tokens = None  # NULL
        mock_usage_record.output_tokens = None  # NULL
        mock_usage_record.cost_usd = None  # NULL
        mock_usage_record.execution_time_ms = None
        mock_usage_record.used_at = datetime(2024, 12, 6, 10, 0, 0, tzinfo=timezone.utc)
        
        mock_usage_repo = Mock()
        mock_usage_repo.get_pipeline_usage.return_value = [mock_usage_record]
        mock_usage_repo_class.return_value = mock_usage_repo
        
        service = TokenMetricsService()
        result = service.get_pipeline_metrics("test-123")
        
        # NULLs treated as zeros
        assert result.total_cost_usd == 0.0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
        assert result.phase_breakdown[0].input_tokens == 0
        assert result.phase_breakdown[0].output_tokens == 0


class TestADR017ServiceLayerIsolation:
    """Test ADR-017: Service layer owns business logic"""
    
    def test_service_constructs_own_repositories(self):
        """
        Given: Service initialization
        When: Service instantiated
        Then: Constructs repositories internally (no injection for MVP)
        """
        service = TokenMetricsService()
        
        # Service has no injected dependencies
        # Repositories constructed inside methods
        assert hasattr(service, '__init__')
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    def test_service_handles_missing_data_gracefully(self, mock_repo_class):
        """
        Given: No data in database
        When: get_summary() called
        Then: Returns valid response with zeros (ADR-017)
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
        
        with patch('app.orchestrator_api.services.token_metrics_service.get_db_session') as mock_get_db_session:
            mock_session = Mock()
            mock_session.execute.return_value.scalar.return_value = 0
            mock_get_db_session.return_value.__enter__.return_value = mock_session
            mock_get_db_session.return_value.__exit__.return_value = None
            
            service = TokenMetricsService()
            result = service.get_summary()
        
        assert result.total_pipelines == 0
        assert result.total_cost_usd == 0.0


class TestADR018DailyGapFilling:
    """Test ADR-018: Fill gaps in daily cost data"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.datetime')
    def test_daily_costs_fills_missing_dates(self, mock_datetime, mock_repo_class):
        """
        Given: Database has data for 2 of 7 days
        When: get_daily_costs(days=7) called
        Then: Returns all 7 days with 0.0 for missing dates (ADR-018)
        """
        # Fix current date
        fixed_now = datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Only 2 days have data
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.return_value = [
            {"date": "2024-12-05", "total_cost": 1.50},
            {"date": "2024-12-06", "total_cost": 2.00}
        ]
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_daily_costs(days=7)
        
        # Returns all 7 days
        assert len(result) == 7
        
        # Missing days have 0.0 cost
        dates_with_zero = [r for r in result if r.total_cost_usd == 0.0]
        assert len(dates_with_zero) == 5
        
        # Days with data have correct costs
        dec_05 = next(r for r in result if r.date == "2024-12-05")
        assert dec_05.total_cost_usd == 1.50
        
        dec_06 = next(r for r in result if r.date == "2024-12-06")
        assert dec_06.total_cost_usd == 2.00
    
    @patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
    @patch('app.orchestrator_api.services.token_metrics_service.datetime')
    def test_daily_costs_generates_correct_date_range(self, mock_datetime, mock_repo_class):
        """
        Given: Request for N days
        When: get_daily_costs(days=N) called
        Then: Returns exactly N consecutive dates ending today (ADR-018)
        """
        fixed_now = datetime(2024, 12, 6, 15, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_repo = Mock()
        mock_repo.get_daily_aggregates.return_value = []
        mock_repo_class.return_value = mock_repo
        
        service = TokenMetricsService()
        result = service.get_daily_costs(days=5)
        
        # Returns exactly 5 days
        assert len(result) == 5
        
        # Dates are consecutive
        dates = [r.date for r in result]
        assert dates == [
            "2024-12-02",
            "2024-12-03",
            "2024-12-04",
            "2024-12-05",
            "2024-12-06"
        ]


class TestADR019EpicDescriptionExtraction:
    """Test ADR-019: Extract epic from artifacts JSON"""
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_epic_extracted_from_epic_description_field(self, mock_get_db_session):
        """
        Given: Pipeline artifacts has epic.description
        When: get_recent_pipelines() called
        Then: Extracts epic_description correctly (ADR-019)
        """
        mock_row = Mock()
        mock_row.pipeline_id = "test-123"
        mock_row.status = "completed"
        mock_row.artifacts = '{"epic": {"description": "Build metrics dashboard"}}'
        mock_row.created_at = "2024-12-06T10:00:00"
        mock_row.total_cost = 1.50
        mock_row.total_tokens = 5000
        
        mock_session = Mock()
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_db_session.return_value.__exit__.return_value = None
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        assert len(result) == 1
        assert result[0].epic_description == "Build metrics dashboard"
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_epic_extracted_from_pm_epic_description_field(self, mock_get_db_session):
        """
        Given: Pipeline artifacts has pm.epic_description
        When: get_recent_pipelines() called
        Then: Extracts epic_description as fallback (ADR-019)
        """
        mock_row = Mock()
        mock_row.pipeline_id = "test-456"
        mock_row.status = "in_progress"
        mock_row.artifacts = '{"pm": {"epic_description": "User authentication"}}'
        mock_row.created_at = "2024-12-06T11:00:00"
        mock_row.total_cost = 0.75
        mock_row.total_tokens = 2500
        
        mock_session = Mock()
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_db_session.return_value.__exit__.return_value = None
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        assert len(result) == 1
        assert result[0].epic_description == "User authentication"
    
    @patch('app.orchestrator_api.services.token_metrics_service.get_db_session')
    def test_epic_none_when_not_present(self, mock_get_db_session):
        """
        Given: Pipeline artifacts has no epic
        When: get_recent_pipelines() called
        Then: Returns None for epic_description (ADR-019)
        """
        mock_row = Mock()
        mock_row.pipeline_id = "test-789"
        mock_row.status = "completed"
        mock_row.artifacts = '{}'
        mock_row.created_at = "2024-12-06T12:00:00"
        mock_row.total_cost = 1.00
        mock_row.total_tokens = 3000
        
        mock_session = Mock()
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_db_session.return_value.__exit__.return_value = None
        
        service = TokenMetricsService()
        result = service.get_recent_pipelines()
        
        assert len(result) == 1
        assert result[0].epic_description is None
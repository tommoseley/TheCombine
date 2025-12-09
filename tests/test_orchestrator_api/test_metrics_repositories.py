"""
Unit tests for PipelinePromptUsageRepository extensions (PIPELINE-175D)

Tests new methods added for metrics aggregation:
- get_system_aggregates()
- get_pipeline_usage()
- get_daily_aggregates()
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import PipelinePromptUsageRepository


class TestPipelinePromptUsageRepositoryGetSystemAggregates:
    """Test get_system_aggregates() method"""
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_system_aggregates_with_data(self):
        """
        Given: Database has pipeline_prompt_usage records
        When: get_system_aggregates() called
        Then: Returns dict with count, total_cost, total_tokens, last_timestamp
        """
        mock_row = Mock()
        mock_row.count = 10
        mock_row.total_cost = Decimal("5.50")
        mock_row.total_input = 15000
        mock_row.total_output = 25000
        mock_row.last_timestamp = datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchone.return_value = mock_row
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_system_aggregates()
        
        assert result["count"] == 10
        assert result["total_cost"] == 5.50
        assert result["total_input_tokens"] == 15000
        assert result["total_output_tokens"] == 25000
        assert result["last_timestamp"] == datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_system_aggregates_no_data(self):
        """
        Given: Database has no pipeline_prompt_usage records
        When: get_system_aggregates() called
        Then: Returns dict with zeros and None
        """
        mock_row = Mock()
        mock_row.count = 0
        mock_row.total_cost = None
        mock_row.total_input = None
        mock_row.total_output = None
        mock_row.last_timestamp = None
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchone.return_value = mock_row
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_system_aggregates()
        
        assert result["count"] == 0
        assert result["total_cost"] == 0.0
        assert result["total_input_tokens"] == 0
        assert result["total_output_tokens"] == 0
        assert result["last_timestamp"] is None
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_system_aggregates_handles_null_values(self):
        """
        Given: Database aggregates return NULL for some values
        When: get_system_aggregates() called
        Then: Treats NULLs as zeros
        """
        mock_row = Mock()
        mock_row.count = 5
        mock_row.total_cost = None
        mock_row.total_input = 1000
        mock_row.total_output = None
        mock_row.last_timestamp = datetime.now(timezone.utc)
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchone.return_value = mock_row
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_system_aggregates()
        
        assert result["total_cost"] == 0.0
        assert result["total_input_tokens"] == 1000
        assert result["total_output_tokens"] == 0


class TestPipelinePromptUsageRepositoryGetPipelineUsage:
    """Test get_pipeline_usage() method"""
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_pipeline_usage_with_records(self):
        """
        Given: Pipeline has multiple usage records
        When: get_pipeline_usage(pipeline_id) called
        Then: Returns list of usage objects with phase/role info
        """
        mock_record1 = Mock()
        mock_record1.phase_name = "pm_phase"
        mock_record1.role_name = "pm"
        mock_record1.input_tokens = 1500
        mock_record1.output_tokens = 2500
        mock_record1.cost_usd = Decimal("0.025")
        mock_record1.execution_time_ms = 2500
        mock_record1.used_at = datetime(2024, 12, 6, 10, 0, 0, tzinfo=timezone.utc)
        
        mock_record2 = Mock()
        mock_record2.phase_name = "architect_phase"
        mock_record2.role_name = "architect"
        mock_record2.input_tokens = 2000
        mock_record2.output_tokens = 3000
        mock_record2.cost_usd = Decimal("0.035")
        mock_record2.execution_time_ms = 3200
        mock_record2.used_at = datetime(2024, 12, 6, 10, 5, 0, tzinfo=timezone.utc)
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = [mock_record1, mock_record2]
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_pipeline_usage("test-123")
        
        assert len(result) == 2
        assert result[0].phase_name == "pm_phase"
        assert result[0].input_tokens == 1500
        assert result[1].phase_name == "architect_phase"
        assert result[1].input_tokens == 2000
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_pipeline_usage_no_records(self):
        """
        Given: Pipeline has no usage records
        When: get_pipeline_usage(pipeline_id) called
        Then: Returns empty list
        """
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = []
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_pipeline_usage("nonexistent-id")
        
        assert result == []
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_pipeline_usage_ordered_by_timestamp(self):
        """
        Given: Usage records exist
        When: get_pipeline_usage() called
        Then: Results ordered by used_at ASC
        """
        # We verify ordering by checking the SQL query includes ORDER BY
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = []
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            repo.get_pipeline_usage("test-123")
        
        # Verify SQL contains ORDER BY clause
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "ORDER BY" in sql_text
        assert "ppu.used_at" in sql_text


class TestPipelinePromptUsageRepositoryGetDailyAggregates:
    """Test get_daily_aggregates() method"""
    
    @patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.datetime')
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_daily_aggregates_with_data(self, mock_datetime):
        """
        Given: Database has usage records over multiple days
        When: get_daily_aggregates(days=7) called
        Then: Returns list of dicts with date and total_cost
        """
        # Fix current time
        fixed_now = datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_row1 = Mock()
        mock_row1.date = "2024-12-04"
        mock_row1.total_cost = Decimal("2.50")
        
        mock_row2 = Mock()
        mock_row2.date = "2024-12-05"
        mock_row2.total_cost = Decimal("3.75")
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = [mock_row1, mock_row2]
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_daily_aggregates(days=7)
        
        assert len(result) == 2
        assert result[0]["date"] == "2024-12-04"
        assert result[0]["total_cost"] == 2.50
        assert result[1]["date"] == "2024-12-05"
        assert result[1]["total_cost"] == 3.75
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_daily_aggregates_no_data(self):
        """
        Given: Database has no usage records in date range
        When: get_daily_aggregates() called
        Then: Returns empty list
        """
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = []
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            result = repo.get_daily_aggregates(days=7)
        
        assert result == []
    
    @patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.datetime')
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_daily_aggregates_respects_days_parameter(self, mock_datetime):
        """
        Given: days parameter specified
        When: get_daily_aggregates(days=3) called
        Then: SQL query filters for last 3 days
        """
        fixed_now = datetime(2024, 12, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = []
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            repo.get_daily_aggregates(days=3)
        
        # Verify SQL was called with correct start_date
        call_args = mock_session.execute.call_args
        params = call_args[1]
        # Start date should be 3 days ago
        expected_start = (fixed_now.date() - timedelta(days=2)).isoformat()
        assert params["start_date"] == expected_start
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_daily_aggregates_uses_utc_timezone(self):
        """
        Given: System in non-UTC timezone
        When: get_daily_aggregates() called
        Then: Uses database UTC for date grouping (ADR-014 compliance)
        """
        # This test verifies the SQL uses DATE(used_at) not local timezone conversion
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.execute().fetchall.return_value = []
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.get_db_session', return_value=mock_session):
            repo = PipelinePromptUsageRepository()
            repo.get_daily_aggregates(days=7)
        
        # Verify SQL uses DATE() function (database UTC grouping)
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "DATE(" in sql_text or "date(" in sql_text


class TestPipelineRepositoryGetPipelineWithEpic:
    """Test get_pipeline_with_epic() method"""
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_pipeline_with_epic_exists(self):
        """
        Given: Pipeline exists with artifacts
        When: get_pipeline_with_epic(pipeline_id) called
        Then: Returns dict with pipeline_id, status, current_phase, epic_description
        """
        from app.orchestrator_api.persistence.repositories.pipeline_repository import PipelineRepository
        
        mock_pipeline = Mock()
        mock_pipeline.id = "test-123"
        mock_pipeline.status = "completed"
        mock_pipeline.current_phase = "commit_phase"
        mock_pipeline.artifacts = {"epic": {"description": "Test Epic"}}
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.query().filter().first.return_value = mock_pipeline
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_repository.get_db_session', return_value=mock_session):
            repo = PipelineRepository()
            result = repo.get_pipeline_with_epic("test-123")
        
        assert result is not None
        assert result["pipeline_id"] == "test-123"
        assert result["status"] == "completed"
        assert result["current_phase"] == "commit_phase"
        assert result["epic_description"] == "Test Epic"
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_pipeline_with_epic_not_found(self):
        """
        Given: Pipeline does not exist
        When: get_pipeline_with_epic(pipeline_id) called
        Then: Returns None
        """
        from app.orchestrator_api.persistence.repositories.pipeline_repository import PipelineRepository
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.query().filter().first.return_value = None
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_repository.get_db_session', return_value=mock_session):
            repo = PipelineRepository()
            result = repo.get_pipeline_with_epic("nonexistent")
        
        assert result is None
    
    @pytest.mark.skip(reason="Requires SQL implementation")
    def test_get_pipeline_with_epic_no_artifacts(self):
        """
        Given: Pipeline exists with NULL artifacts
        When: get_pipeline_with_epic() called
        Then: Returns dict with epic_description=None
        """
        from app.orchestrator_api.persistence.repositories.pipeline_repository import PipelineRepository
        
        mock_pipeline = Mock()
        mock_pipeline.id = "test-123"
        mock_pipeline.status = "in_progress"
        mock_pipeline.current_phase = "pm_phase"
        mock_pipeline.artifacts = None
        
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.query().filter().first.return_value = mock_pipeline
        
        with patch('app.orchestrator_api.persistence.repositories.pipeline_repository.get_db_session', return_value=mock_session):
            repo = PipelineRepository()
            result = repo.get_pipeline_with_epic("test-123")
        
        assert result["epic_description"] is None
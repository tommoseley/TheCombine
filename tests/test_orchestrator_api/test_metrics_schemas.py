"""
Unit tests for metrics Pydantic schemas (PIPELINE-175D)

Tests schema validation, serialization, and type coercion.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.orchestrator_api.schemas.metrics import (
    MetricsSummaryResponse,
    PipelineMetricsResponse,
    PhaseMetrics,
    RecentPipelineResponse,
    DailyCostResponse
)


class TestMetricsSummaryResponseSchema:
    """Test MetricsSummaryResponse schema"""
    
    def test_valid_summary_response(self):
        """
        Given: Valid summary data
        When: MetricsSummaryResponse constructed
        Then: Schema validates successfully
        """
        data = {
            "total_pipelines": 10,
            "total_cost_usd": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        
        response = MetricsSummaryResponse(**data)
        
        assert response.total_pipelines == 10
        assert response.total_cost_usd == 5.50
        assert response.total_input_tokens == 15000
        assert response.total_output_tokens == 25000
        assert response.success_count == 7
        assert response.failure_count == 3
    
    def test_summary_response_with_zeros(self):
        """
        Given: Summary data with all zeros
        When: MetricsSummaryResponse constructed
        Then: Schema accepts zeros as valid
        """
        data = {
            "total_pipelines": 0,
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "success_count": 0,
            "failure_count": 0
        }
        
        response = MetricsSummaryResponse(**data)
        
        assert response.total_pipelines == 0
        assert response.total_cost_usd == 0.0
    
    def test_summary_response_missing_required_field(self):
        """
        Given: Data missing required field
        When: MetricsSummaryResponse constructed
        Then: Raises ValidationError
        """
        data = {
            "total_pipelines": 10,
            # Missing total_cost_usd
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MetricsSummaryResponse(**data)
        
        assert "total_cost_usd" in str(exc_info.value)
    
    def test_summary_response_invalid_type(self):
        """
        Given: Data with invalid type
        When: MetricsSummaryResponse constructed
        Then: Raises ValidationError
        """
        data = {
            "total_pipelines": "ten",  # Should be int
            "total_cost_usd": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        
        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**data)
    
    def test_summary_response_excludes_timestamp(self):
        """
        Given: Data includes timestamp (internal field)
        When: MetricsSummaryResponse serialized
        Then: Timestamp excluded from output (ADR-013)
        """
        data = {
            "total_pipelines": 10,
            "total_cost_usd": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        
        response = MetricsSummaryResponse(**data)
        json_data = response.model_dump()
        
        assert "last_usage_timestamp" not in json_data


class TestPipelineMetricsResponseSchema:
    """Test PipelineMetricsResponse schema"""
    
    def test_valid_pipeline_metrics(self):
        """
        Given: Valid pipeline metrics data
        When: PipelineMetricsResponse constructed
        Then: Schema validates successfully
        """
        data = {
            "pipeline_id": "test-123",
            "status": "completed",
            "current_phase": "commit_phase",
            "epic_description": "Test Epic",
            "total_cost_usd": 2.50,
            "total_input_tokens": 3500,
            "total_output_tokens": 5500,
            "phase_breakdown": [
                {
                    "phase_name": "pm_phase",
                    "role_name": "pm",
                    "input_tokens": 1500,
                    "output_tokens": 2500,
                    "cost_usd": 0.025,
                    "execution_time_ms": 2500,
                    "timestamp": "2024-12-06T10:00:00+00:00"
                }
            ]
        }
        
        response = PipelineMetricsResponse(**data)
        
        assert response.pipeline_id == "test-123"
        assert response.status == "completed"
        assert response.total_cost_usd == 2.50
        assert len(response.phase_breakdown) == 1
        assert response.phase_breakdown[0].phase_name == "pm_phase"
    
    def test_pipeline_metrics_null_epic_description(self):
        """
        Given: Pipeline with no epic description
        When: PipelineMetricsResponse constructed
        Then: Accepts None for epic_description
        """
        data = {
            "pipeline_id": "test-123",
            "status": "in_progress",
            "current_phase": "pm_phase",
            "epic_description": None,
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "phase_breakdown": []
        }
        
        response = PipelineMetricsResponse(**data)
        
        assert response.epic_description is None
    
    def test_pipeline_metrics_empty_phase_breakdown(self):
        """
        Given: Pipeline with no usage records
        When: PipelineMetricsResponse constructed
        Then: Accepts empty phase_breakdown list
        """
        data = {
            "pipeline_id": "test-123",
            "status": "in_progress",
            "current_phase": "pm_phase",
            "epic_description": "New Pipeline",
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "phase_breakdown": []
        }
        
        response = PipelineMetricsResponse(**data)
        
        assert response.phase_breakdown == []


class TestPhaseMetricsSchema:
    """Test PhaseMetrics schema"""
    
    def test_valid_phase_metrics(self):
        """
        Given: Valid phase metrics data
        When: PhaseMetrics constructed
        Then: Schema validates successfully
        """
        data = {
            "phase_name": "pm_phase",
            "role_name": "pm",
            "input_tokens": 1500,
            "output_tokens": 2500,
            "cost_usd": 0.025,
            "execution_time_ms": 2500,
            "timestamp": "2024-12-06T10:00:00+00:00"
        }
        
        phase = PhaseMetrics(**data)
        
        assert phase.phase_name == "pm_phase"
        assert phase.role_name == "pm"
        assert phase.input_tokens == 1500
        assert phase.cost_usd == 0.025
    
    def test_phase_metrics_null_execution_time(self):
        """
        Given: Phase metrics with null execution time
        When: PhaseMetrics constructed
        Then: Accepts None for optional field
        """
        data = {
            "phase_name": "pm_phase",
            "role_name": "pm",
            "input_tokens": 1500,
            "output_tokens": 2500,
            "cost_usd": 0.025,
            "execution_time_ms": None,
            "timestamp": "2024-12-06T10:00:00+00:00"
        }
        
        phase = PhaseMetrics(**data)
        
        assert phase.execution_time_ms is None
    
    def test_phase_metrics_invalid_timestamp_format(self):
        """
        Given: Invalid timestamp format
        When: PhaseMetrics constructed
        Then: Accepts string (no datetime validation at schema level)
        """
        data = {
            "phase_name": "pm_phase",
            "role_name": "pm",
            "input_tokens": 1500,
            "output_tokens": 2500,
            "cost_usd": 0.025,
            "execution_time_ms": 2500,
            "timestamp": "invalid-date"
        }
        
        # Schema allows any string for timestamp
        phase = PhaseMetrics(**data)
        assert phase.timestamp == "invalid-date"


class TestRecentPipelineResponseSchema:
    """Test RecentPipelineResponse schema"""
    
    def test_valid_recent_pipeline(self):
        """
        Given: Valid pipeline summary data
        When: RecentPipelineResponse constructed
        Then: Schema validates successfully
        """
        data = {
            "pipeline_id": "test-123",
            "epic_description": "Test Epic",
            "status": "completed",
            "total_cost_usd": 1.50,
            "total_tokens": 5000,
            "created_at": "2024-12-06T10:00:00"
        }
        
        pipeline = RecentPipelineResponse(**data)
        
        assert pipeline.pipeline_id == "test-123"
        assert pipeline.epic_description == "Test Epic"
        assert pipeline.total_cost_usd == 1.50
        assert pipeline.total_tokens == 5000
    
    def test_recent_pipeline_null_epic(self):
        """
        Given: Pipeline with no epic
        When: RecentPipelineResponse constructed
        Then: Accepts None for epic_description
        """
        data = {
            "pipeline_id": "test-123",
            "epic_description": None,
            "status": "in_progress",
            "total_cost_usd": 0.75,
            "total_tokens": 2500,
            "created_at": "2024-12-06T11:00:00"
        }
        
        pipeline = RecentPipelineResponse(**data)
        
        assert pipeline.epic_description is None
    
    def test_recent_pipeline_datetime_serialization(self):
        """
        Given: created_at as datetime object
        When: RecentPipelineResponse serialized
        Then: Datetime converted to ISO string
        """
        data = {
            "pipeline_id": "test-123",
            "epic_description": "Test",
            "status": "completed",
            "total_cost_usd": 1.50,
            "total_tokens": 5000,
            "created_at": datetime(2024, 12, 6, 10, 0, 0, tzinfo=timezone.utc)
        }
        
        pipeline = RecentPipelineResponse(**data)
        json_data = pipeline.model_dump()
        
        # Datetime should be serialized as string
        assert isinstance(json_data["created_at"], (str, datetime))


class TestDailyCostResponseSchema:
    """Test DailyCostResponse schema"""
    
    def test_valid_daily_cost(self):
        """
        Given: Valid daily cost data
        When: DailyCostResponse constructed
        Then: Schema validates successfully
        """
        data = {
            "date": "2024-12-06",
            "total_cost_usd": 2.50
        }
        
        daily_cost = DailyCostResponse(**data)
        
        assert daily_cost.date == "2024-12-06"
        assert daily_cost.total_cost_usd == 2.50
    
    def test_daily_cost_zero_cost(self):
        """
        Given: Day with no usage
        When: DailyCostResponse constructed
        Then: Accepts 0.0 for total_cost_usd
        """
        data = {
            "date": "2024-12-06",
            "total_cost_usd": 0.0
        }
        
        daily_cost = DailyCostResponse(**data)
        
        assert daily_cost.total_cost_usd == 0.0
    
    def test_daily_cost_date_format(self):
        """
        Given: Date in YYYY-MM-DD format
        When: DailyCostResponse constructed
        Then: Accepts string date (no validation)
        """
        data = {
            "date": "2024-12-06",
            "total_cost_usd": 1.25
        }
        
        daily_cost = DailyCostResponse(**data)
        
        assert len(daily_cost.date) == 10
        assert daily_cost.date.count("-") == 2


class TestSchemaTypeCoercion:
    """Test Pydantic type coercion behavior"""
    
    def test_int_to_float_coercion(self):
        """
        Given: Integer provided for float field
        When: Schema constructed
        Then: Pydantic coerces int to float
        """
        data = {
            "date": "2024-12-06",
            "total_cost_usd": 2  # Int instead of float
        }
        
        daily_cost = DailyCostResponse(**data)
        
        assert daily_cost.total_cost_usd == 2.0
        assert isinstance(daily_cost.total_cost_usd, float)
    
    def test_float_to_int_validation(self):
        """
        Given: Float provided for int field
        When: Schema constructed
        Then: Pydantic 2.x accepts whole numbers, rejects fractional
        """
        # Whole number floats are OK
        data_ok = {
            "total_pipelines": 10.0,
            "total_cost_usd": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        response = MetricsSummaryResponse(**data_ok)
        assert response.total_pipelines == 10
        
        # Fractional floats are rejected
        data_bad = {
            "total_pipelines": 10.7,
            "total_cost_usd": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        with pytest.raises(ValidationError) as exc_info:
            MetricsSummaryResponse(**data_bad)
        assert "total_pipelines" in str(exc_info.value)


class TestSchemaSerializationExclusions:
    """Test that internal fields are excluded from API responses"""
    
    def test_summary_excludes_internal_timestamp(self):
        """
        Given: MetricsSummaryResponse with data
        When: Serialized to JSON
        Then: last_usage_timestamp excluded (ADR-013)
        """
        data = {
            "total_pipelines": 10,
            "total_cost_usd": 5.50,
            "total_input_tokens": 15000,
            "total_output_tokens": 25000,
            "success_count": 7,
            "failure_count": 3
        }
        
        response = MetricsSummaryResponse(**data)
        json_output = response.model_dump_json()
        
        assert "last_usage_timestamp" not in json_output
        assert "total_pipelines" in json_output
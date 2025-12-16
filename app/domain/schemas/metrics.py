"""Pydantic schemas for metrics API responses."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class MetricsSummaryResponse(BaseModel):
    """
    JSON response for GET /metrics/summary.
    
    Note: Excludes last_usage_timestamp (only used in HTML templates).
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_pipelines": 42,
                "total_cost_usd": 12.50,
                "total_input_tokens": 150000,
                "total_output_tokens": 50000,
                "success_count": 38,
                "failure_count": 4
            }
        }
    )
    
    total_pipelines: int = Field(..., description="Total number of pipelines")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    total_input_tokens: int = Field(..., description="Total input tokens across all pipelines")
    total_output_tokens: int = Field(..., description="Total output tokens across all pipelines")
    success_count: int = Field(..., description="Number of completed pipelines")
    failure_count: int = Field(..., description="Number of failed/error pipelines")


class PhaseMetrics(BaseModel):
    """Schema for phase-level metrics (shared between internal and external)."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phase_name": "pm_phase",
                "role_name": "pm",
                "input_tokens": 5000,
                "output_tokens": 1500,
                "cost_usd": 0.15,
                "execution_time_ms": 3200,
                "timestamp": "2025-12-06T10:30:00Z"
            }
        }
    )
    
    phase_name: str = Field(..., description="Phase identifier")
    role_name: str = Field(..., description="Role that executed this phase")
    input_tokens: int = Field(..., description="Input tokens for this phase")
    output_tokens: int = Field(..., description="Output tokens for this phase")
    cost_usd: float = Field(..., description="Cost in USD for this phase")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    timestamp: str = Field(..., description="Execution timestamp (ISO format)")


class PipelineMetricsResponse(BaseModel):
    """JSON response for GET /metrics/pipelines/{id}."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pipeline_id": "pipe_123",
                "status": "completed",
                "current_phase": "commit",
                "epic_description": "Add metrics dashboard",
                "total_cost_usd": 0.45,
                "total_input_tokens": 12000,
                "total_output_tokens": 3000,
                "phase_breakdown": [
                    {
                        "phase_name": "pm_phase",
                        "role_name": "pm",
                        "input_tokens": 5000,
                        "output_tokens": 1500,
                        "cost_usd": 0.15,
                        "execution_time_ms": 3200,
                        "timestamp": "2025-12-06T10:30:00Z"
                    }
                ]
            }
        }
    )
    
    pipeline_id: str = Field(..., description="Pipeline identifier")
    status: str = Field(..., description="Pipeline status")
    current_phase: str = Field(..., description="Current phase name")
    epic_description: Optional[str] = Field(None, description="Epic description if available")
    total_cost_usd: float = Field(..., description="Total cost for this pipeline")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")
    phase_breakdown: list[PhaseMetrics] = Field(..., description="Per-phase metrics")


class RecentPipelineResponse(BaseModel):
    """Schema for pipeline summary in recent pipelines list."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pipeline_id": "pipe_123",
                "epic_description": "Add user authentication",
                "status": "completed",
                "total_cost_usd": 0.45,
                "total_tokens": 15000,
                "created_at": "2025-12-06T10:00:00Z"
            }
        }
    )
    
    pipeline_id: str = Field(..., description="Pipeline identifier")
    epic_description: Optional[str] = Field(None, description="Epic description if available")
    status: str = Field(..., description="Pipeline status")
    total_cost_usd: float = Field(..., description="Total cost for this pipeline")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    created_at: datetime = Field(..., description="Pipeline creation timestamp")


class DailyCostResponse(BaseModel):
    """Schema for daily cost aggregates."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-12-06",
                "total_cost_usd": 5.25
            }
        }
    )
    
    date: str = Field(..., description="Date in YYYY-MM-DD format (database UTC)")
    total_cost_usd: float = Field(..., description="Total cost for this date")
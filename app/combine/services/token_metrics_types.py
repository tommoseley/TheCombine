from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MetricsSummary:
    """Internal type for system-wide metrics summary."""
    total_pipelines: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    success_count: int
    failure_count: int
    last_usage_timestamp: Optional[datetime]


@dataclass
class PipelineSummary:
    """Internal type for pipeline list items."""
    pipeline_id: str
    epic_description: Optional[str]
    status: str
    total_cost_usd: float
    total_tokens: int
    created_at: datetime


@dataclass
class PhaseMetricsInternal:
    """Internal type for phase-level metrics."""
    phase_name: str
    role_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    execution_time_ms: Optional[int]
    timestamp: str


@dataclass
class PipelineMetrics:
    """Internal type for per-pipeline metrics with breakdown."""
    pipeline_id: str
    status: str
    current_phase: str
    epic_description: Optional[str]
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    phase_breakdown: list  # list[PhaseMetricsInternal]


@dataclass
class DailyCost:
    """Internal type for daily cost aggregates."""
    date: str  # YYYY-MM-DD in database UTC
    total_cost_usd: float

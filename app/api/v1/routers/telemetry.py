"""Telemetry API endpoints for cost tracking and metrics."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
    CostSummary,
)


router = APIRouter(prefix="/telemetry", tags=["telemetry"])


# Module-level store for dependency injection
_telemetry_store: Optional[InMemoryTelemetryStore] = None
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get telemetry service instance."""
    global _telemetry_store, _telemetry_service
    if _telemetry_service is None:
        _telemetry_store = InMemoryTelemetryStore()
        _telemetry_service = TelemetryService(_telemetry_store)
    return _telemetry_service


def get_telemetry_store() -> InMemoryTelemetryStore:
    """Get telemetry store instance."""
    global _telemetry_store
    if _telemetry_store is None:
        _telemetry_store = InMemoryTelemetryStore()
    return _telemetry_store


def set_telemetry_service(service: TelemetryService, store: InMemoryTelemetryStore) -> None:
    """Set telemetry service (for testing/configuration)."""
    global _telemetry_service, _telemetry_store
    _telemetry_service = service
    _telemetry_store = store


def reset_telemetry_service() -> None:
    """Reset to default service (for testing)."""
    global _telemetry_store, _telemetry_service
    _telemetry_store = None
    _telemetry_service = None


# Response Models
class CostSummaryResponse(BaseModel):
    """Cost summary response."""
    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    call_count: int
    error_count: int
    avg_latency_ms: float
    cache_hit_rate: float


class WorkflowStatsResponse(BaseModel):
    """Statistics for a specific workflow."""
    workflow_id: str
    execution_count: int
    completed_count: int
    failed_count: int
    total_cost_usd: float
    avg_cost_usd: float
    avg_duration_ms: float


class StepCostResponse(BaseModel):
    """Cost breakdown for a step."""
    step_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    cached: bool


class ExecutionCostsResponse(BaseModel):
    """Cost breakdown for an execution."""
    execution_id: UUID
    total_cost_usd: float
    total_tokens: int
    call_count: int
    steps: List[StepCostResponse]


class TelemetrySummaryResponse(BaseModel):
    """Overall telemetry summary."""
    total_calls: int
    total_cost_usd: float
    total_tokens: int
    avg_cost_per_call: float
    success_rate: float
    period_start: Optional[date] = None
    period_end: Optional[date] = None


def _summary_to_response(summary: CostSummary) -> CostSummaryResponse:
    """Convert CostSummary to response model."""
    return CostSummaryResponse(
        total_cost_usd=float(summary.total_cost_usd),
        input_tokens=summary.input_tokens,
        output_tokens=summary.output_tokens,
        cached_tokens=summary.cached_tokens,
        call_count=summary.call_count,
        error_count=summary.error_count,
        avg_latency_ms=summary.avg_latency_ms,
        cache_hit_rate=summary.cache_hit_rate,
    )


@router.get(
    "/summary",
    response_model=TelemetrySummaryResponse,
    summary="Get telemetry summary",
    description="Get overall telemetry summary for a date.",
)
async def get_telemetry_summary(
    target_date: Optional[date] = Query(None, description="Date for summary (default: today)"),
    service: TelemetryService = Depends(get_telemetry_service),
) -> TelemetrySummaryResponse:
    """Get overall telemetry summary."""
    if target_date is None:
        target_date = date.today()
    
    summary = await service.get_daily_summary(target_date)
    
    total_tokens = summary.input_tokens + summary.output_tokens
    avg_cost = float(summary.total_cost_usd) / max(summary.call_count, 1)
    success_rate = 1.0 - (summary.error_count / max(summary.call_count, 1))
    
    return TelemetrySummaryResponse(
        total_calls=summary.call_count,
        total_cost_usd=float(summary.total_cost_usd),
        total_tokens=total_tokens,
        avg_cost_per_call=avg_cost,
        success_rate=success_rate,
        period_start=target_date,
        period_end=target_date,
    )


@router.get(
    "/costs/daily",
    response_model=CostSummaryResponse,
    summary="Get daily cost summary",
    description="Get detailed cost summary for a specific date.",
)
async def get_daily_costs(
    target_date: Optional[date] = Query(None, description="Date (default: today)"),
    service: TelemetryService = Depends(get_telemetry_service),
) -> CostSummaryResponse:
    """Get detailed cost summary for a date."""
    if target_date is None:
        target_date = date.today()
    
    summary = await service.get_daily_summary(target_date)
    return _summary_to_response(summary)


@router.get(
    "/executions/{execution_id}/costs",
    response_model=ExecutionCostsResponse,
    summary="Get execution costs",
    description="Get cost breakdown for a specific execution.",
    responses={
        404: {"description": "Execution not found"},
    },
)
async def get_execution_costs(
    execution_id: UUID,
    service: TelemetryService = Depends(get_telemetry_service),
    store: InMemoryTelemetryStore = Depends(get_telemetry_store),
) -> ExecutionCostsResponse:
    """Get cost breakdown for an execution."""
    records = await store.get_execution_calls(execution_id)
    
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXECUTION_NOT_FOUND",
                "message": f"No telemetry found for execution: {execution_id}",
            },
        )
    
    steps = [
        StepCostResponse(
            step_id=r.step_id,
            model=r.model,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            cost_usd=float(r.cost_usd),
            latency_ms=r.latency_ms,
            cached=r.cached,
        )
        for r in records
    ]
    
    total_cost = sum(float(r.cost_usd) for r in records)
    total_tokens = sum(r.input_tokens + r.output_tokens for r in records)
    
    return ExecutionCostsResponse(
        execution_id=execution_id,
        total_cost_usd=total_cost,
        total_tokens=total_tokens,
        call_count=len(records),
        steps=steps,
    )


@router.get(
    "/workflows/{workflow_id}/stats",
    response_model=WorkflowStatsResponse,
    summary="Get workflow statistics",
    description="Get statistics for a specific workflow.",
)
async def get_workflow_stats(
    workflow_id: str,
) -> WorkflowStatsResponse:
    """Get statistics for a workflow (placeholder - needs workflow tracking)."""
    return WorkflowStatsResponse(
        workflow_id=workflow_id,
        execution_count=0,
        completed_count=0,
        failed_count=0,
        total_cost_usd=0.0,
        avg_cost_usd=0.0,
        avg_duration_ms=0.0,
    )

"""Metrics router - JSON and HTML endpoints for operator dashboard."""

from pathlib import Path
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.orchestrator_api.services.token_metrics_service import (
    TokenMetricsService,
)
from app.orchestrator_api.schemas.metrics import (
    MetricsSummaryResponse,
    PipelineMetricsResponse,
    PhaseMetrics,
    RecentPipelineResponse,  # ← ADD THIS
    DailyCostResponse        # ← ADD THIS
)

logger = logging.getLogger(__name__)

# Router setup
router = APIRouter()

# Template setup
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Verify directory exists
if not TEMPLATE_DIR.exists():
    logger.error(f"Template directory not found: {TEMPLATE_DIR}")


# ---------------------------------------------------------------------------
# JSON endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/metrics/summary",
    response_model=MetricsSummaryResponse,
    tags=["metrics"],
)
async def get_metrics_summary() -> MetricsSummaryResponse:
    """
    Get system-wide aggregated metrics.

    Returns JSON with total pipelines, cost, tokens, and success/failure counts.
    Does NOT include last_usage_timestamp (use HTML endpoint for live indicator).

    No authentication required - operator tool for trusted network.
    """
    service = TokenMetricsService()
    summary = service.get_summary()

    # Convert internal MetricsSummary → MetricsSummaryResponse
    # Exclude last_usage_timestamp from JSON response
    return MetricsSummaryResponse(
        total_pipelines=summary.total_pipelines,
        total_cost_usd=summary.total_cost_usd,
        total_input_tokens=summary.total_input_tokens,
        total_output_tokens=summary.total_output_tokens,
        success_count=summary.success_count,
        failure_count=summary.failure_count,
    )


@router.get(
    "/metrics/pipeline/{pipeline_id}",
    response_model=PipelineMetricsResponse,
    tags=["metrics"],
)
async def get_pipeline_metrics(
    pipeline_id: str,
) -> PipelineMetricsResponse:
    """
    Get detailed metrics for a specific pipeline.

    Returns JSON with per-pipeline totals and phase-level breakdown.
    Returns 404 if pipeline not found.

    No authentication required - operator tool for trusted network.
    """
    service = TokenMetricsService()
    metrics = service.get_pipeline_metrics(pipeline_id)

    if metrics is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Convert internal PipelineMetrics → PipelineMetricsResponse
    return PipelineMetricsResponse(
        pipeline_id=metrics.pipeline_id,
        status=metrics.status,
        current_phase=metrics.current_phase,
        epic_description=metrics.epic_description,
        total_cost_usd=metrics.total_cost_usd,
        total_input_tokens=metrics.total_input_tokens,
        total_output_tokens=metrics.total_output_tokens,
        phase_breakdown=[
            PhaseMetrics(
                phase_name=p.phase_name,
                role_name=p.role_name,
                input_tokens=p.input_tokens,
                output_tokens=p.output_tokens,
                cost_usd=p.cost_usd,
                execution_time_ms=p.execution_time_ms,
                timestamp=p.timestamp,
            )
            for p in metrics.phase_breakdown
        ],
    )


# ---------------------------------------------------------------------------
# HTML endpoints
# ---------------------------------------------------------------------------
@router.get("/metrics", response_class=HTMLResponse, tags=["metrics"])
async def metrics_overview(request: Request) -> HTMLResponse:
    """
    Render metrics overview dashboard (HTML).

    Displays system-wide metrics, recent pipelines, and cost trend chart.
    Auto-refreshes every 30 seconds.

    No authentication required - operator tool for trusted network.
    """
    service = TokenMetricsService()
    summary = service.get_summary()
    recent = service.get_recent_pipelines(limit=20)
    daily = service.get_daily_costs(days=7)

    # Calculate last_usage_minutes for live indicator
    last_usage_minutes = None
    if summary.last_usage_timestamp:
        try:
            # Handle timezone-naive datetime from SQLite
            timestamp = summary.last_usage_timestamp
            if timestamp.tzinfo is None:
                from datetime import timezone as _tz

                timestamp = timestamp.replace(tzinfo=_tz.utc)

            delta = datetime.now(_tz.utc) - timestamp
            last_usage_minutes = int(delta.total_seconds() / 60)
        except Exception as e:
            logger.warning(f"Failed to calculate last_usage_minutes: {e}")

    return templates.TemplateResponse(
        request=request,
        name="metrics/overview.html",
        context={
            "request": request,
            "summary": summary,  # Full MetricsSummary with last_usage_timestamp
            "recent_pipelines": recent,
            "daily_costs": daily,
            "last_usage_minutes": last_usage_minutes,
        },
    )


@router.get(
    "/metrics/pipeline/{pipeline_id}",
    response_class=HTMLResponse,
    name="pipeline_detail",
    tags=["metrics"],
)
async def pipeline_detail(
    request: Request, pipeline_id: str
) -> HTMLResponse:
    """
    Render per-pipeline detail page (HTML).

    Displays pipeline summary and phase-by-phase breakdown.
    Returns 404 page if pipeline not found.

    No authentication required - operator tool for trusted network.
    """
    service = TokenMetricsService()
    pipeline = service.get_pipeline_metrics(pipeline_id)

    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    return templates.TemplateResponse(
        request=request,
        name="metrics/detail.html",
        context={
            "request": request,
            "pipeline": pipeline,  # Full PipelineMetrics with breakdown
        },
    )


@router.get("/metrics/recent", tags=["metrics"])
async def get_recent_pipelines(limit: int = 20):
    """Get recent pipelines with metrics."""
    service = TokenMetricsService()
    pipelines = service.get_recent_pipelines(limit=limit)
    
    return [
        RecentPipelineResponse(
            pipeline_id=p.pipeline_id,
            epic_description=p.epic_description,
            status=p.status,
            total_cost_usd=p.total_cost_usd,
            total_tokens=p.total_tokens,
            created_at=p.created_at
        )
        for p in pipelines
    ]


@router.get("/metrics/daily-costs", tags=["metrics"])
async def get_daily_costs(days: int = 7):
    """Get daily cost aggregates."""
    service = TokenMetricsService()
    costs = service.get_daily_costs(days=days)
    
    return [
        DailyCostResponse(
            date=c.date,
            total_cost_usd=c.total_cost_usd
        )
        for c in costs
    ]


# Fix the pipeline detail endpoint URL (singular not plural)
@router.get("/metrics/pipeline/{pipeline_id}", tags=["metrics"])  # ← singular
async def get_pipeline_metrics(pipeline_id: str):
    """Get detailed metrics for a specific pipeline."""
    service = TokenMetricsService()
    metrics = service.get_pipeline_metrics(pipeline_id)
    
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")
    
    return PipelineMetricsResponse(
        pipeline_id=metrics.pipeline_id,
        status=metrics.status,
        current_phase=metrics.current_phase,
        epic_description=metrics.epic_description,
        total_cost_usd=metrics.total_cost_usd,
        total_input_tokens=metrics.total_input_tokens,
        total_output_tokens=metrics.total_output_tokens,
        phase_breakdown=[
            PhaseMetrics(
                phase_name=p.phase_name,
                role_name=p.role_name,
                input_tokens=p.input_tokens,
                output_tokens=p.output_tokens,
                cost_usd=p.cost_usd,
                execution_time_ms=p.execution_time_ms,
                timestamp=p.timestamp
            )
            for p in metrics.phase_breakdown
        ]
    )

@router.get("/metrics/{pipeline_id}", tags=["metrics"])
async def get_pipeline_detail_html(
    request: Request,
    pipeline_id: str
):
    """
    Get pipeline detail page (HTML).
    
    Returns HTML when Accept header is text/html,
    otherwise redirects to JSON endpoint.
    """
    # Check if client wants HTML
    accept = request.headers.get("accept", "")
    
    if "text/html" in accept:
        service = TokenMetricsService()
        metrics = service.get_pipeline_metrics(pipeline_id)
        
        if metrics is None:
            raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")
        
        # Calculate phase data for template
        phases = [
            {
                "name": p.phase_name,
                "role": p.role_name,
                "cost": p.cost_usd,
                "input_tokens": p.input_tokens,
                "output_tokens": p.output_tokens,
                "execution_time_ms": p.execution_time_ms
            }
            for p in metrics.phase_breakdown
        ]
        
        return templates.TemplateResponse(
            request=request,
            name="metrics/detail.html",
            context={
                "pipeline": {
                    "pipeline_id": metrics.pipeline_id,
                    "status": metrics.status,
                    "current_phase": metrics.current_phase,
                    "epic_description": metrics.epic_description or "N/A",
                    "total_cost_usd": metrics.total_cost_usd,
                    "total_input_tokens": metrics.total_input_tokens,
                    "total_output_tokens": metrics.total_output_tokens,
                },
                "phases": phases
            }
        )
    else:
        # Not HTML request - redirect to JSON endpoint
        # (or you could return JSON directly here)
        raise HTTPException(status_code=404, detail="Use /metrics/pipeline/{id} for JSON")
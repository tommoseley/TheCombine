"""Dashboard pages for UI."""

from datetime import date, timedelta, datetime, timezone
from typing import Optional
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date

from app.auth.dependencies import require_admin
from app.auth.models import User
from app.core.database import get_db
from app.domain.models.llm_logging import LLMRun
from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
    CostSummary,
)


router = APIRouter(prefix="/admin", tags=["admin-dashboard"], dependencies=[Depends(require_admin)])

templates = Jinja2Templates(directory="app/web/templates/admin")


# Module-level service
_telemetry_store: Optional[InMemoryTelemetryStore] = None
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_svc() -> TelemetryService:
    """Get telemetry service."""
    global _telemetry_store, _telemetry_service
    if _telemetry_service is None:
        _telemetry_store = InMemoryTelemetryStore()
        _telemetry_service = TelemetryService(_telemetry_store)
    return _telemetry_service


def set_telemetry_svc(service: TelemetryService) -> None:
    """Set telemetry service (for testing)."""
    global _telemetry_service
    _telemetry_service = service


def reset_telemetry_svc() -> None:
    """Reset telemetry service."""
    global _telemetry_store, _telemetry_service
    _telemetry_store = None
    _telemetry_service = None


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_index(request: Request):
    """Dashboard index - list available dashboards."""
    dashboards = [
        {
            "name": "Cost Dashboard",
            "description": "Track LLM API costs, token usage, and spending trends",
            "url": "/admin/dashboard/costs",
            "icon": "chart-bar",
        },
    ]
    return templates.TemplateResponse(request, "pages/dashboard/index.html", {
        "active_page": "costs",
        "dashboards": dashboards,
    })


@router.get("/dashboard/costs", response_class=HTMLResponse)
async def cost_dashboard(
    request: Request,
    days: int = Query(default=7, ge=1, le=90),
    source: Optional[str] = Query(default=None),
    service: TelemetryService = Depends(get_telemetry_svc),
    db: AsyncSession = Depends(get_db),
):
    """Render cost dashboard page with unified workflow and document build costs."""
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days-1)
    
    # Initialize daily data structure
    daily_totals = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0, "errors": 0, "workflow_cost": 0.0, "document_cost": 0.0})
    
    # Get workflow telemetry (unless filtered to documents only)
    if source != "documents":
        for i in range(days):
            day = today - timedelta(days=i)
            summary = await service.get_daily_summary(day)
            day_str = day.strftime("%Y-%m-%d")
            daily_totals[day_str]["cost"] += float(summary.total_cost_usd)
            daily_totals[day_str]["workflow_cost"] += float(summary.total_cost_usd)
            daily_totals[day_str]["tokens"] += summary.input_tokens + summary.output_tokens
            daily_totals[day_str]["calls"] += summary.call_count
            daily_totals[day_str]["errors"] += summary.error_count
    
    # Get document build costs from llm_run table (unless filtered to workflows only)
    if source != "workflows":
        # Query for document builds in the date range
        query = select(LLMRun).where(
            and_(
                LLMRun.artifact_type.isnot(None),
                LLMRun.started_at >= datetime.combine(start_date, datetime.min.time()),
            )
        )
        
        result = await db.execute(query)
        runs = result.scalars().all()
        
        for run in runs:
            if run.started_at:
                day_str = run.started_at.strftime("%Y-%m-%d")
                cost = float(run.cost_usd or 0)
                daily_totals[day_str]["cost"] += cost
                daily_totals[day_str]["document_cost"] += cost
                daily_totals[day_str]["tokens"] += (run.input_tokens or 0) + (run.output_tokens or 0)
                daily_totals[day_str]["calls"] += 1
                if run.status == "FAILED":
                    daily_totals[day_str]["errors"] += 1
    
    # Build daily_data list in chronological order
    daily_data = []
    total_cost = 0.0
    total_tokens = 0
    total_calls = 0
    total_errors = 0
    
    for i in range(days-1, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        data = daily_totals[day_str]
        
        daily_data.append({
            "date": day_str,
            "date_short": day.strftime("%m/%d"),
            "cost": data["cost"],
            "tokens": data["tokens"],
            "calls": data["calls"],
            "errors": data["errors"],
            "workflow_cost": data["workflow_cost"],
            "document_cost": data["document_cost"],
        })
        
        total_cost += data["cost"]
        total_tokens += data["tokens"]
        total_calls += data["calls"]
        total_errors += data["errors"]
    
    # Calculate averages
    avg_cost_per_day = total_cost / days if days > 0 else 0
    avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
    success_rate = (1 - (total_errors / total_calls)) * 100 if total_calls > 0 else 100
    
    return templates.TemplateResponse(
        request,
        "pages/dashboard/costs.html",
        {
            "active_page": "costs",
            "period_days": days,
            "source_filter": source,
            "daily_data": daily_data,
            "summary": {
                "total_cost": round(total_cost, 4),
                "total_tokens": total_tokens,
                "total_calls": total_calls,
                "total_errors": total_errors,
                "avg_cost_per_day": round(avg_cost_per_day, 4),
                "avg_cost_per_call": round(avg_cost_per_call, 6),
                "success_rate": round(success_rate, 1),
            },
        },
    )


@router.get("/dashboard/costs/api/daily", response_class=HTMLResponse)
async def cost_daily_partial(
    request: Request,
    days: int = Query(default=7, ge=1, le=90),
    service: TelemetryService = Depends(get_telemetry_svc),
):
    """Partial endpoint for daily cost data (HTMX)."""
    today = datetime.now(timezone.utc).date()
    
    daily_data = []
    for i in range(days):
        day = today - timedelta(days=i)
        summary = await service.get_daily_summary(day)
        daily_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "cost": float(summary.total_cost_usd),
            "tokens": summary.input_tokens + summary.output_tokens,
            "calls": summary.call_count,
        })
    
    daily_data.reverse()
    
    return templates.TemplateResponse(
        request,
        "partials/dashboard/daily_costs.html",
        {"daily_data": daily_data},
    )
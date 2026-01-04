"""Dashboard pages for UI."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
    CostSummary,
)


router = APIRouter(tags=["dashboard-pages"])

templates = Jinja2Templates(directory="app/ui/templates")


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


@router.get("/dashboard/costs", response_class=HTMLResponse)
async def cost_dashboard(
    request: Request,
    days: int = Query(default=7, ge=1, le=90),
    service: TelemetryService = Depends(get_telemetry_svc),
):
    """Render cost dashboard page."""
    today = date.today()
    
    # Get daily summaries for the period
    daily_data = []
    total_cost = 0.0
    total_tokens = 0
    total_calls = 0
    total_errors = 0
    
    for i in range(days):
        day = today - timedelta(days=i)
        summary = await service.get_daily_summary(day)
        
        daily_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "date_short": day.strftime("%m/%d"),
            "cost": float(summary.total_cost_usd),
            "tokens": summary.input_tokens + summary.output_tokens,
            "calls": summary.call_count,
            "errors": summary.error_count,
        })
        
        total_cost += float(summary.total_cost_usd)
        total_tokens += summary.input_tokens + summary.output_tokens
        total_calls += summary.call_count
        total_errors += summary.error_count
    
    # Reverse for chronological order
    daily_data.reverse()
    
    # Calculate averages
    avg_cost_per_day = total_cost / days if days > 0 else 0
    avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
    success_rate = (1 - (total_errors / total_calls)) * 100 if total_calls > 0 else 100
    
    return templates.TemplateResponse(
        request,
        "pages/dashboard/costs.html",
        {
            "active_page": "dashboard",
            "period_days": days,
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
    today = date.today()
    
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

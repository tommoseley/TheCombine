"""Dashboard pages for UI."""

from datetime import timedelta, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.api.services.cost_service import get_cost_dashboard_data
from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
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
    # Use the cost service for data
    data = await get_cost_dashboard_data(
        db=db,
        telemetry_service=service,
        days=days,
        source=source,
    )

    return templates.TemplateResponse(
        request,
        "pages/dashboard/costs.html",
        {
            "active_page": "costs",
            "period_days": data["period_days"],
            "source_filter": data["source_filter"],
            "daily_data": data["daily_data"],
            "summary": data["summary"],
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
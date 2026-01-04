"""Partial routes for HTMX updates."""

from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.v1.dependencies import get_workflow_registry, get_persistence
from app.api.v1.routers.executions import get_execution_service
from app.api.v1.services.execution_service import ExecutionService, ExecutionNotFoundError
from app.domain.workflow import (
    WorkflowRegistry,
    WorkflowStatus,
    StatePersistence,
)


router = APIRouter(prefix="/partials", tags=["partials"])

templates = Jinja2Templates(directory="app/ui/templates")


def get_exec_service(
    persistence: StatePersistence = Depends(get_persistence),
) -> ExecutionService:
    """Get execution service via dependency injection."""
    return get_execution_service(persistence)


@router.get("/executions", response_class=HTMLResponse)
async def executions_list_partial(
    request: Request,
    workflow_id: Optional[str] = Query(None, alias="workflow_filter"),
    status: Optional[str] = Query(None, alias="status_filter"),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Return execution list partial for HTMX updates."""
    # Convert status string to enum
    status_enum = None
    if status:
        try:
            status_enum = WorkflowStatus(status)
        except ValueError:
            pass
    
    all_executions = await execution_service.list_executions(
        workflow_id=workflow_id,
        status=status_enum,
    )
    
    executions = [
        {
            "execution_id": e.execution_id,
            "workflow_id": e.workflow_id,
            "project_id": e.project_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "started_at": e.started_at.strftime("%Y-%m-%d %H:%M") if e.started_at else None,
        }
        for e in all_executions
    ]
    
    return templates.TemplateResponse(
        request,
        "partials/execution_list.html",
        {"executions": executions},
    )


@router.get("/executions/recent", response_class=HTMLResponse)
async def recent_executions_partial(
    request: Request,
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Return recent executions partial for dashboard."""
    all_executions = await execution_service.list_executions()
    
    executions = [
        {
            "execution_id": e.execution_id,
            "workflow_id": e.workflow_id,
            "project_id": e.project_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "started_at": e.started_at.strftime("%Y-%m-%d %H:%M") if e.started_at else None,
        }
        for e in all_executions[:10]
    ]
    
    return templates.TemplateResponse(
        request,
        "partials/execution_list.html",
        {"executions": executions},
    )


@router.get("/executions/{execution_id}/status", response_class=HTMLResponse)
async def execution_status_partial(
    request: Request,
    execution_id: str,
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Return execution status badge partial."""
    try:
        state, _ = await execution_service.get_execution(execution_id)
        status = state.status.value if hasattr(state.status, 'value') else str(state.status)
    except ExecutionNotFoundError:
        status = "unknown"
    
    return templates.TemplateResponse(
        request,
        "components/status_badge.html",
        {"status": status},
    )

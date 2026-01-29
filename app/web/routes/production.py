"""Production Line web routes (ADR-043).

Serves the Production Line UI - uses React + SSE for real-time updates.
This is a full-page route (not HTMX partial) to support React rendering.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.services.production_service import (
    get_project,
    get_production_tracks,
    get_production_status,
)
from app.domain.workflow.production_state import ProductionState
from app.domain.workflow.interrupt_registry import InterruptRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/production", tags=["production"])

templates = Jinja2Templates(directory="app/web/templates")


@router.get("", response_class=HTMLResponse)
async def production_line(
    request: Request,
    project_id: Optional[str] = Query(None, description="Project ID"),
    db: AsyncSession = Depends(get_db),
):
    """Render the Production Line page.

    Always returns full page (extends base.html) for React/SSE support.
    """
    project = None
    tracks = []
    interrupt = None
    line_state = "idle"
    summary = {
        "total": 0,
        "stabilized": 0,
        "active": 0,
        "blocked": 0,
        "queued": 0,
        "awaiting_operator": 0,
    }

    if project_id:
        status = await get_production_status(db, project_id)

        if status.get("project_name"):
            project = await get_project(db, project_id)
            tracks = status["tracks"]
            line_state = status["line_state"]
            summary = status["summary"]

            registry = InterruptRegistry(db)
            pending_interrupts = await registry.get_pending(project_id)
            if pending_interrupts:
                interrupt = pending_interrupts[0].to_dict()

    context = {
        "request": request,
        "project": project,
        "tracks": tracks,
        "line_state": line_state,
        "summary": summary,
        "interrupt": interrupt,
    }

    return templates.TemplateResponse("production/line_react.html", context)


@router.post("/start", response_class=HTMLResponse)
async def start_production(
    request: Request,
    project_id: str = Query(..., description="Project ID"),
    document_type: Optional[str] = Query(None, description="Specific document type"),
    db: AsyncSession = Depends(get_db),
):
    """Start production for a project."""
    from app.domain.workflow.project_orchestrator import ProjectOrchestrator

    if document_type:
        return RedirectResponse(
            url=f"/projects/{project_id}/documents/{document_type}/build",
            status_code=303,
        )
    else:
        try:
            orchestrator = ProjectOrchestrator(db)
            state = await orchestrator.run_full_line(project_id)

            logger.info(
                f"Full line production started for {project_id}: "
                f"status={state.status.value}, tracks={len(state.tracks)}"
            )

            return RedirectResponse(
                url=f"/production?project_id={project_id}",
                status_code=303,
            )

        except Exception as e:
            logger.error(f"Failed to start full line production: {e}")
            tracks = await get_production_tracks(db, project_id)
            for track in tracks:
                if track["state"] == ProductionState.QUEUED.value:
                    return RedirectResponse(
                        url=f"/projects/{project_id}/documents/{track['document_type']}/build",
                        status_code=303,
                    )

            return RedirectResponse(
                url=f"/production?project_id={project_id}",
                status_code=303,
            )
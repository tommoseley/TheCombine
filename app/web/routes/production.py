"""Production Line web routes (ADR-043).

Serves the Production Line UI - the primary operator surface for
watching document manufacturing in real-time.
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

    This is the primary operator surface per ADR-043.
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
        # Use the production service to get status
        status = await get_production_status(db, project_id)

        if status.get("project_name"):
            project = await get_project(db, project_id)
            tracks = status["tracks"]
            line_state = status["line_state"]
            summary = status["summary"]

            # Get full interrupt details from registry (includes payload)
            registry = InterruptRegistry(db)
            pending_interrupts = await registry.get_pending(project_id)
            if pending_interrupts:
                # Convert to dict for template
                interrupt = pending_interrupts[0].to_dict()

    return templates.TemplateResponse(
        "production/line.html",
        {
            "request": request,
            "project": project,
            "tracks": tracks,
            "line_state": line_state,
            "summary": summary,
            "interrupt": interrupt,
        },
    )


@router.post("/start", response_class=HTMLResponse)
async def start_production(
    request: Request,
    project_id: str = Query(..., description="Project ID"),
    document_type: Optional[str] = Query(None, description="Specific document type"),
    db: AsyncSession = Depends(get_db),
):
    """Start production for a project.

    If document_type is specified, redirects to that document's build page.
    Otherwise, uses ProjectOrchestrator to run the full line.
    """
    from app.domain.workflow.project_orchestrator import ProjectOrchestrator

    if document_type:
        # Start single document - redirect to build page
        return RedirectResponse(
            url=f"/projects/{project_id}/workflows/{document_type}/build",
            status_code=303,
        )
    else:
        # Run full line using ProjectOrchestrator
        try:
            orchestrator = ProjectOrchestrator(db)
            state = await orchestrator.run_full_line(project_id)

            logger.info(
                f"Full line production started for {project_id}: "
                f"status={state.status.value}, tracks={len(state.tracks)}"
            )

            # Redirect back to production page to see progress
            return RedirectResponse(
                url=f"/production?project_id={project_id}",
                status_code=303,
            )

        except Exception as e:
            logger.error(f"Failed to start full line production: {e}")
            # Fall back to redirecting to first queued document
            tracks = await get_production_tracks(db, project_id)
            for track in tracks:
                if track["state"] == ProductionState.QUEUED.value:
                    return RedirectResponse(
                        url=f"/projects/{project_id}/workflows/{track['document_type']}/build",
                        status_code=303,
                    )

            # All done or error, redirect back
            return RedirectResponse(
                url=f"/production?project_id={project_id}",
                status_code=303,
            )

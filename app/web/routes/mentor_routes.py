"""
Mentor routes for The Combine UI
Handles AI mentor interactions (PM, BA, Developer, QA)
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates, get_template
from app.api.services import project_service

router = APIRouter(tags=["mentors"])


@router.get("/projects/{project_id}/mentors/pm/new", response_class=HTMLResponse)
async def get_pm_mentor_form(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Show form to start PM Mentor
    """
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # TODO: Create pm_mentor_form wrapper + partial
    return templates.TemplateResponse(
        "pages/pm_mentor_form.html",
        {
            "request": request,
            "project": project
        }
    )
"""
Project routes for The Combine UI - Simplified
Two-target HTMX approach: #document-container and #document-content
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from uuid import UUID
import logging

from database import get_db
from .shared import templates
from app.api.services import project_service
from app.api.services.document_status_service import document_status_service

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

async def _get_project_with_icon(db: AsyncSession, project_id: str) -> dict | None:
    """Get project with icon field."""
    result = await db.execute(
        text("""
            SELECT id, name, project_id, description, icon, created_at, updated_at
            FROM projects WHERE id = :project_id
        """),
        {"project_id": project_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    return {
        "id": str(row.id),
        "name": row.name,
        "project_id": row.project_id,
        "description": row.description,
        "icon": row.icon or "folder",
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


def _get_htmx_target(request: Request) -> str | None:
    """Get the HTMX target element."""
    return request.headers.get("HX-Target")


# ============================================================================
# PROJECT LIST (for sidebar)
# ============================================================================

@router.get("/list", response_class=HTMLResponse)
async def get_project_list(
    request: Request,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get list of projects for sidebar."""
    if search:
        result = await db.execute(
            text("""
                SELECT id, name, project_id, icon FROM projects
                WHERE name ILIKE :search OR project_id ILIKE :search
                ORDER BY name ASC
            """),
            {"search": f"%{search}%"}
        )
    else:
        result = await db.execute(
            text("SELECT id, name, project_id, icon FROM projects ORDER BY name ASC")
        )
    
    rows = result.fetchall()
    projects = [
        {"id": str(row.id), "name": row.name, "project_id": row.project_id, "icon": row.icon or "folder"}
        for row in rows
    ]
    
    return templates.TemplateResponse("components/project_list.html", {
        "request": request,
        "projects": projects
    })


# ============================================================================
# PROJECT DETAIL - Returns document container
# ============================================================================

@router.get("/{project_id}", response_class=HTMLResponse)
async def get_project(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get project view.
    - HTMX request targeting #document-container: return _document_container.html
    - Full page request: return full page with base.html
    """
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_uuid = UUID(project_id)
    document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
    
    context = {
        "request": request,
        "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": None,
    }
    
    # HTMX request - return just the document container partial
    if _is_htmx_request(request):
        return templates.TemplateResponse("pages/partials/_document_container.html", context)
    
    # Full page request - return with base template
    # For now, return the partial (base.html will include it via block)
    return templates.TemplateResponse("pages/partials/_document_container.html", context)


@router.put("/{project_id}", response_class=HTMLResponse)
async def update_project(
    request: Request,
    project_id: str,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Update project - returns just the project overview content."""
    await db.execute(
        text("""
            UPDATE projects 
            SET name = :name, description = :description, icon = :icon, updated_at = NOW()
            WHERE id = :project_id
        """),
        {"name": name.strip(), "description": description.strip(), "icon": icon, "project_id": project_id}
    )
    await db.commit()
    
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_uuid = UUID(project_id)
    document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
    
    return templates.TemplateResponse(
        "pages/partials/_project_overview.html",
        {
            "request": request,
            "project": project,
            "document_statuses": document_statuses,
        },
        headers={"HX-Trigger": "refreshProjectList"}
    )


# ============================================================================
# PROJECT CRUD
# ============================================================================

@router.get("/new", response_class=HTMLResponse)
async def new_project_form(request: Request):
    """Display form for creating a new project."""
    return templates.TemplateResponse("pages/partials/_project_new_content.html", {
        "request": request,
        "project": None,
        "mode": "create"
    })


@router.post("/create", response_class=HTMLResponse)
async def create_project_handler(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    try:
        project = await project_service.create_project(
            db=db,
            name=name.strip(),
            description=description.strip(),
            icon=icon
        )
        
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
                "title": "Project Created",
                "message": f'Project "{name}" has been created.',
            },
            headers={"HX-Redirect": f"/ui/projects/{project['id']}"}
        )
        
    except ValueError as e:
        return templates.TemplateResponse("components/alerts/error.html", {
            "request": request,
            "title": "Error Creating Project",
            "message": str(e)
        })


@router.delete("/{project_id}", response_class=HTMLResponse)
async def delete_project(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project."""
    try:
        await db.execute(text("DELETE FROM projects WHERE id = :project_id"), {"project_id": project_id})
        await db.commit()
        
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
                "title": "Project Deleted",
                "message": "The project has been deleted.",
            },
            headers={"HX-Redirect": "/ui", "HX-Trigger": "refreshProjectList"}
        )
        
    except Exception as e:
        logger.error(f"Error deleting project: {e}", exc_info=True)
        return templates.TemplateResponse("components/alerts/error.html", {
            "request": request,
            "title": "Error Deleting Project",
            "message": str(e)
        })
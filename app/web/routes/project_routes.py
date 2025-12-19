"""
Project routes for The Combine UI - V2
Flat project list, editable names/icons, two-panel layout
"""

from fastapi import APIRouter, Depends, Query, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import logging

from database import get_db
from .shared import templates, get_template
from app.api.services import project_service
from app.api.services.document_status_service import (
    DocumentStatusService,
    document_status_service,
    ReadinessStatus
)

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


# ============================================================================
# DOCUMENT TYPE TO TEMPLATE MAPPING
# ============================================================================

DOCUMENT_TEMPLATES = {
    "project_discovery": "documents/_preliminary_architecture.html",
    "epic_backlog": "documents/_epic_backlog.html",
    "technical_architecture": "documents/_technical_architecture.html",
}

DOCUMENT_TITLES = {
    "project_discovery": "Project Discovery",
    "epic_backlog": "Epic Backlog", 
    "technical_architecture": "Technical Architecture",
}

DOCUMENT_ICONS = {
    "project_discovery": "compass",
    "epic_backlog": "layers",
    "technical_architecture": "building",
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _compute_document_summary(document_statuses: list) -> dict:
    """Compute summary counts from document statuses."""
    return {
        "ready_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.READY),
        "stale_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.STALE),
        "blocked_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.BLOCKED),
        "waiting_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.WAITING),
    }


async def _get_project_with_icon(db: AsyncSession, project_id: str) -> dict:
    """Get project with icon field using direct SQL."""
    from sqlalchemy import text
    
    result = await db.execute(
        text("""
            SELECT id, name, project_id, description, icon, created_at, updated_at
            FROM projects 
            WHERE id = :project_id
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


# ============================================================================
# PROJECT LIST (for sidebar)
# ============================================================================

@router.get("/list", response_class=HTMLResponse)
async def get_project_list(
    request: Request,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get list of projects for sidebar - simple flat list"""
    from sqlalchemy import text
    
    if search:
        result = await db.execute(
            text("""
                SELECT id, name, project_id, icon
                FROM projects
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
        {
            "id": str(row.id),
            "name": row.name,
            "project_id": row.project_id,
            "icon": row.icon or "folder"
        }
        for row in rows
    ]
    
    return templates.TemplateResponse(
        "components/project_list.html",
        {
            "request": request,
            "projects": projects
        }
    )


# ============================================================================
# PROJECT CRUD
# ============================================================================

@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Display form for creating a new project"""
    template = get_template(
        request,
        wrapper="pages/project_detail.html",
        partial="pages/partials/_project_new_content.html"
    )
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "project": None,
            "mode": "create"
        }
    )


@router.post("/create", response_class=HTMLResponse)
async def create_project_handler(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Handle form submission for creating a new project"""
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
                "message": f'Project "{name}" has been created successfully.',
                "redirect_url": f"/ui/projects/{project['id']}",
                "redirect_delay": 1000
            },
            headers={"HX-Redirect": f"/ui/projects/{project['id']}"}
        )
        
    except ValueError as e:
        return templates.TemplateResponse(
            "components/alerts/error.html",
            {
                "request": request,
                "title": "Error Creating Project",
                "message": str(e)
            }
        )


@router.get("/{project_id}", response_class=HTMLResponse)
async def get_project_detail(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Display project detail with document list sidebar"""
    try:
        project = await _get_project_with_icon(db, project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get document statuses for sidebar
        project_uuid = UUID(project_id)
        document_statuses = await document_status_service.get_project_document_statuses(
            db, project_uuid
        )
        
        context = {
            "request": request,
            "project": project,
            "document_statuses": document_statuses,
            "active_doc_type": None,  # No document selected on project view
        }
        
        # Use the wrapper that includes document sidebar
        template = get_template(
            request,
            wrapper="pages/project_detail.html",
            partial="pages/partials/_project_detail.html"
        )
        
        return templates.TemplateResponse(template, context)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}", response_class=HTMLResponse)
async def update_project(
    request: Request,
    project_id: str,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Update project name, description, and icon"""
    from sqlalchemy import text
    
    try:
        await db.execute(
            text("""
                UPDATE projects 
                SET name = :name, 
                    description = :description, 
                    icon = :icon,
                    updated_at = NOW()
                WHERE id = :project_id
            """),
            {
                "name": name.strip(),
                "description": description.strip(),
                "icon": icon,
                "project_id": project_id
            }
        )
        await db.commit()
        
        project = await _get_project_with_icon(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_uuid = UUID(project_id)
        document_statuses = await document_status_service.get_project_document_statuses(
            db, project_uuid
        )
        
        template = get_template(
            request,
            wrapper="pages/project_detail.html",
            partial="pages/partials/_project_detail.html"
        )
        
        return templates.TemplateResponse(
            template,
            {
                "request": request,
                "project": project,
                "document_statuses": document_statuses,
                "active_doc_type": None,
            },
            headers={"HX-Trigger": "refreshProjectList"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}", exc_info=True)
        return templates.TemplateResponse(
            "components/alerts/error.html",
            {
                "request": request,
                "title": "Error Updating Project",
                "message": str(e)
            }
        )


# ============================================================================
# DOCUMENT SIDEBAR REFRESH
# ============================================================================

@router.get("/{project_id}/documents/refresh-sidebar", response_class=HTMLResponse)
async def refresh_document_sidebar(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh just the document list sidebar component"""
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_uuid = UUID(project_id)
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_uuid
    )
    
    # Get active_doc_type from referer URL if possible
    active_doc_type = None
    referer = request.headers.get("referer", "")
    if "/documents/" in referer:
        parts = referer.split("/documents/")
        if len(parts) > 1:
            active_doc_type = parts[1].split("/")[0].split("?")[0]
    
    return templates.TemplateResponse(
        "components/document_list_sidebar.html",
        {
            "request": request,
            "project": project,
            "document_statuses": document_statuses,
            "active_doc_type": active_doc_type,
        }
    )


@router.get("/{project_id}/documents/refresh", response_class=HTMLResponse)
async def refresh_document_statuses(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh just the document status list (legacy)"""
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_uuid = UUID(project_id)
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_uuid
    )
    
    return templates.TemplateResponse(
        "components/sidebar/document_status_list.html",
        {
            "request": request,
            "project": project,
            "document_statuses": document_statuses,
        }
    )


# ============================================================================
# PROJECT DELETE
# ============================================================================

@router.delete("/{project_id}", response_class=HTMLResponse)
async def delete_project(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project"""
    from sqlalchemy import text
    
    try:
        await db.execute(
            text("DELETE FROM projects WHERE id = :project_id"),
            {"project_id": project_id}
        )
        await db.commit()
        
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
                "title": "Project Deleted",
                "message": "The project has been deleted.",
                "redirect_url": "/ui",
                "redirect_delay": 1000
            },
            headers={
                "HX-Redirect": "/ui",
                "HX-Trigger": "refreshProjectList"
            }
        )
        
    except Exception as e:
        logger.error(f"Error deleting project: {e}", exc_info=True)
        return templates.TemplateResponse(
            "components/alerts/error.html",
            {
                "request": request,
                "title": "Error Deleting Project",
                "message": str(e)
            }
        )
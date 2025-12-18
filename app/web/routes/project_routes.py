"""
Project routes for The Combine UI
Handles project CRUD, tree navigation, and project details

Updated to support document-centric architecture (ADR-007)
- Removed Artifact dependency (replaced by Document)
- Uses DocumentStatusService for status derivation
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
# HELPER FUNCTIONS
# ============================================================================

def _compute_document_summary(document_statuses: list) -> dict:
    """Compute summary counts from document statuses for collapsed view."""
    return {
        "ready_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.READY),
        "stale_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.STALE),
        "blocked_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.BLOCKED),
        "waiting_count": sum(1 for d in document_statuses if d.readiness == ReadinessStatus.WAITING),
    }


# ============================================================================
# TREE NAVIGATION
# ============================================================================

@router.get("/tree", response_class=HTMLResponse)
async def get_project_tree(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get projects for sidebar tree with infinite scroll"""
    logger.info(f"Loading project tree: offset={offset}, limit={limit}, search={search}")
    projects = await project_service.list_projects(
        db,
        offset=offset,
        limit=limit,
        search=search
    )
    has_more = len(projects) == limit
    next_offset = offset + limit if has_more else None
    return templates.TemplateResponse(
        "components/tree/project_list.html",
        {
            "request": request,
            "projects": projects,
            "has_more": has_more,
            "next_offset": next_offset
        }
    )


@router.get("/{project_id}/expand", response_class=HTMLResponse)
async def expand_project_tree_node(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get expanded project node with documents and epics"""
    project = await project_service.get_project_with_epics(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get document statuses for summary display
    project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_uuid
    )
    document_summary = _compute_document_summary(document_statuses)
    
    return templates.TemplateResponse(
        "components/tree/project_expanded.html",
        {
            "request": request,
            "project": project,
            "document_summary": document_summary
        }
    )


@router.get("/{project_id}/documents/expand", response_class=HTMLResponse)
async def expand_documents_tree_node(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Expand the Documents node to show individual document types with status.
    Returns the documents_expanded.html partial per ADR-007.
    """
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get document statuses for the project
    project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_uuid
    )
    
    return templates.TemplateResponse(
        "components/tree/documents_expanded.html",
        {
            "request": request,
            "project": project,
            "document_statuses": document_statuses
        }
    )


@router.get("/{project_id}/documents/collapse", response_class=HTMLResponse)
async def collapse_documents_tree_node(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Collapse the Documents node to show summary indicators.
    Returns the documents_collapsed.html partial.
    """
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get document statuses to compute summary
    project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_uuid
    )
    document_summary = _compute_document_summary(document_statuses)
    
    return templates.TemplateResponse(
        "components/tree/documents_collapsed.html",
        {
            "request": request,
            "project": project,
            "document_summary": document_summary
        }
    )


@router.get("/{project_id}/collapse", response_class=HTMLResponse)
async def collapse_project_tree_node(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get collapsed project node"""
    project = await project_service.get_project_summary(db, project_id)
    
    return templates.TemplateResponse(
        "components/tree/project_collapsed.html",
        {
            "request": request,
            "project": project
        }
    )


# ============================================================================
# PROJECT CRUD
# ============================================================================

# IMPORTANT: This route MUST come BEFORE /{project_id}
# so that "new" doesn't get interpreted as a project_id
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
    db: AsyncSession = Depends(get_db)
):
    """
    Handle form submission for creating a new project
    Returns HTML response for HTMX
    """
    try:
        # Use project service to create project
        project = await project_service.create_project(
            db=db,
            name=name.strip(),
            description=description.strip()
        )
        
        # Success response
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
                "title": "Project Created",
                "message": f'Project "{name}" (ID: {project["project_id"]}) has been created successfully.',
                "primary_action": {
                    "label": "View Project",
                    "url": f"/ui/projects/{project['id']}"
                },
                "secondary_action": {
                    "label": "Create Another",
                    "url": "/ui/projects/new"
                }
            }
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
        
    except Exception as e:
        return templates.TemplateResponse(
            "components/alerts/error.html",
            {
                "request": request,
                "title": "Unexpected Error",
                "message": f"Failed to create project: {str(e)}"
            }
        )


@router.get("/{project_id}", response_class=HTMLResponse)
async def get_project_detail(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Display project detail page
    Single route handles both full page and HTMX partial
    """
    try:
        # Use project service to get project
        project = await project_service.get_project_by_uuid(db, project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Load epics - use get_project_with_epics which includes them
        project_with_epics = await project_service.get_project_with_epics(db, project_id)
        epics = project_with_epics.get('epics', []) if project_with_epics else []
        
        # Get document statuses for the document-centric view
        project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
        document_statuses = await document_status_service.get_project_document_statuses(
            db, project_uuid
        )
        
        context = {
            "request": request,
            "project": project,
            "epics": epics or [],
            "document_statuses": document_statuses
        }
        
        template = get_template(
            request,
            wrapper="pages/project_detail.html",
            partial="pages/partials/_project_detail_content.html"
        )
        
        return templates.TemplateResponse(template, context)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading project: {e}", exc_info=True)
        error_html = f"""
        <div class="p-6">
            <div class="bg-red-50 border border-red-200 rounded-lg p-6">
                <h1 class="text-lg font-medium text-gray-900 mb-2">Error loading project</h1>
                <pre class="text-sm text-gray-700">{str(e)}</pre>
                <pre class="text-xs text-gray-500 mt-2">{traceback.format_exc()}</pre>
            </div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=500)
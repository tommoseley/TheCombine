"""
Project routes for The Combine UI
Handles project CRUD, tree navigation, and project details
"""

from fastapi import APIRouter, Depends, Query, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from database import get_db
from .shared import templates, get_template
from app.api.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


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
    """Get expanded project node with epics"""
    project = await project_service.get_project_with_epics(db, project_id)
    
    return templates.TemplateResponse(
        "components/tree/project_expanded.html",
        {
            "request": request,
            "project": project
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
        wrapper="pages/project_new.html",
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
        
        context = {
            "request": request,
            "project": project,
            "high_level_architecture": None,
            "detailed_architecture": None,
            "epics": []
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
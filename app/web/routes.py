"""
Web UI routes for The Combine
Handles project tree navigation, search, and code viewing
Uses path-based architecture (RSP-1)
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from .services import project_service, epic_service, story_service, search_service

# Initialize templates
templates = Jinja2Templates(directory="app/web/templates")

# Register custom filters
def pluralize(count, singular='', plural='s'):
    """Pluralize filter: {{ count|pluralize }} returns '' if count==1 else 's'"""
    if isinstance(count, (list, tuple)):
        count = len(count)
    return singular if count == 1 else plural

templates.env.filters['pluralize'] = pluralize

# Create router
router = APIRouter(prefix="/ui", tags=["web-ui"])


# ============================================================================
# PROJECT ROUTES
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - shows base layout with welcome content"""
    return templates.TemplateResponse(
        "layout/base.html",
        {"request": request}
    )

@router.get("/projects/tree", response_class=HTMLResponse)
async def get_project_tree(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get projects for sidebar tree with infinite scroll"""
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

@router.get("/projects/{project_id}/expand", response_class=HTMLResponse)
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

@router.get("/projects/{project_id}/collapse", response_class=HTMLResponse)
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

@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def get_project_detail(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full project details"""
    project = await project_service.get_project_full(db, project_id)
    
    return templates.TemplateResponse(
        "pages/project_detail.html",
        {
            "request": request,
            "project": project
        }
    )

@router.get("/projects/{project_id}/partial", response_class=HTMLResponse)
async def get_project_detail_partial(request: Request, project_id: str, db: AsyncSession = Depends(get_db)):
    project = await project_service.get_project_full(db, project_id)
    if not project:
        raise HTTPException(404)
    
    # Render the CONTENT BLOCK only
    return templates.TemplateResponse(
        "project_detail.html",
        {"request": request, "project": project},
        block="content"  # ← THIS IS THE KEY
    )

@router.get("/projects/{project_id}/architecture", response_class=HTMLResponse)
async def get_project_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get architecture view"""
    architecture = await project_service.get_architecture(db, project_id)
    
    return templates.TemplateResponse(
        "pages/architecture_view.html",
        {
            "request": request,
            "architecture": architecture
        }
    )


# ============================================================================
# EPIC ROUTES
# ============================================================================

@router.get("/epics/{epic_id}/expand", response_class=HTMLResponse)
async def expand_epic_tree_node(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get expanded epic node with stories"""
    epic = await epic_service.get_epic_with_stories(db, epic_id)
    
    return templates.TemplateResponse(
        "components/tree/epic_expanded.html",
        {
            "request": request,
            "epic": epic
        }
    )

@router.get("/epics/{epic_id}/collapse", response_class=HTMLResponse)
async def collapse_epic_tree_node(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get collapsed epic node"""
    epic = await epic_service.get_epic_summary(db, epic_id)
    
    return templates.TemplateResponse(
        "components/tree/epic_collapsed.html",
        {
            "request": request,
            "epic": epic
        }
    )

@router.get("/epics/{epic_id}", response_class=HTMLResponse)
async def get_epic_detail(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get epic details"""
    epic = await epic_service.get_epic_full(db, epic_id)
    
    return templates.TemplateResponse(
        "pages/epic_detail.html",
        {
            "request": request,
            "epic": epic
        }
    )

@router.get("/epics/{epic_id}/stories", response_class=HTMLResponse)
async def get_epic_stories(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get stories list"""
    data = await epic_service.get_stories(db, epic_id)
    
    return templates.TemplateResponse(
        "pages/epic_stories.html",
        {
            "request": request,
            **data
        }
    )

@router.get("/epics/{epic_id}/code", response_class=HTMLResponse)
async def get_epic_code(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all code deliverables for epic"""
    data = await epic_service.get_epic_code(db, epic_id)
    
    return templates.TemplateResponse(
        "pages/epic_code.html",
        {
            "request": request,
            **data
        }
    )


# ============================================================================
# STORY ROUTES
# ============================================================================

@router.get("/stories/{story_id}", response_class=HTMLResponse)
async def get_story_detail(
    request: Request,
    story_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get story details"""
    story = await story_service.get_story_full(db, story_id)
    
    return templates.TemplateResponse(
        "pages/story_detail.html",
        {
            "request": request,
            "story": story
        }
    )

@router.get("/stories/{story_id}/code", response_class=HTMLResponse)
async def get_story_code_view(
    request: Request,
    story_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get code view for story"""
    data = await story_service.get_code_deliverables(db, story_id)
    
    if not data["has_code"]:
        # Return empty state
        return templates.TemplateResponse(
            "pages/story_code.html",
            {
                "request": request,
                "story_uuid": story_id,
                "story_title": data.get("story_title", "Story"),
                "files": []
            }
        )
    
    return templates.TemplateResponse(
        "pages/story_code.html",
        {
            "request": request,
            **data
        }
    )

@router.get("/stories/{story_id}/code/file/{file_index}", response_class=HTMLResponse)
async def get_story_code_file(
    request: Request,
    story_id: str,
    file_index: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific code file for display"""
    try:
        data = await story_service.get_code_file(db, story_id, file_index)
    except ValueError as e:
        return templates.TemplateResponse(
            "components/code_file.html",
            {
                "request": request,
                "file": {
                    "filepath": "Error",
                    "content": str(e),
                    "language": "text"
                }
            }
        )
    
    return templates.TemplateResponse(
        "components/code_file.html",
        {
            "request": request,
            **data
        }
    )

@router.get("/stories/{story_id}/code/download")
async def download_story_code(
    story_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download all code files as zip"""
    try:
        zip_buffer = await story_service.create_code_zip(db, story_id)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=story-{story_id}-code.zip"
            }
        )
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# SEARCH ROUTES
# ============================================================================

@router.get("/search", response_class=HTMLResponse)
async def search_all(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db)
):
    """Global search across all entities"""
    results = await search_service.search_all(db, q, limit=10)
    
    # Get tree paths for highlighting
    affected_paths = results.get_tree_paths()
    
    return templates.TemplateResponse(
        "components/search_results.html",
        {
            "request": request,
            "query": q,
            "results": {
                "projects": results.projects,
                "epics": results.epics,
                "stories": results.stories
            },
            "affected_paths": affected_paths,
            "has_results": bool(results.projects or results.epics or results.stories)
        }
    )
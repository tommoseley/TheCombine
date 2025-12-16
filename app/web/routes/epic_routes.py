"""
Epic routes for The Combine UI
Handles epic details, tree navigation, and workflows
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates, get_template
from app.api.services import epic_service

router = APIRouter(prefix="/epics", tags=["epics"])


# ============================================================================
# TREE NAVIGATION
# ============================================================================

@router.get("/{epic_id}/expand", response_class=HTMLResponse)
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
            "epic": epic,
        }
    )


@router.get("/{epic_id}/collapse", response_class=HTMLResponse)
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


# ============================================================================
# EPIC DETAILS
# ============================================================================

@router.get("/{epic_id}", response_class=HTMLResponse)
async def get_epic_detail(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get epic details - single route for full page and HTMX"""
    epic = await epic_service.get_epic_full(db, epic_id)
    
    context = {
        "request": request,
        "epic": epic
    }
    
    template = get_template(
        request,
        wrapper="pages/epic_detail.html",
        partial="pages/partials/_epic_detail_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/{epic_id}/stories", response_class=HTMLResponse)
async def get_epic_stories(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get stories list"""
    data = await epic_service.get_stories(db, epic_id)
    
    context = {
        "request": request,
        **data
    }
    
    template = get_template(
        request,
        wrapper="pages/epic_stories.html",
        partial="pages/partials/_epic_stories_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/{epic_id}/code", response_class=HTMLResponse)
async def get_epic_code(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all code deliverables for epic"""
    data = await epic_service.get_epic_code(db, epic_id)
    
    # TODO: Create epic_code.html wrapper + partial
    return templates.TemplateResponse(
        "pages/epic_code.html",
        {
            "request": request,
            **data
        }
    )


# ============================================================================
# EPIC WORKFLOWS
# ============================================================================

@router.post("/{epic_id}/begin-work", response_class=HTMLResponse)
async def begin_epic_work(
    request: Request,
    epic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Start work on an epic - runs BA and Developer mentors
    Redirects to epic detail page
    """
    # TODO: Implement epic workflow
    # For now, just redirect to epic page
    return RedirectResponse(
        url=f"/ui/epics/{epic_id}",
        status_code=303
    )
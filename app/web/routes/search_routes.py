"""
Search routes for The Combine UI
Handles global search across all entities
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates
from app.api.services import search_service

router = APIRouter(tags=["search"])


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
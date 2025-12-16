"""
Story routes for The Combine UI
Handles story details and code deliverables
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates, get_template
from app.api.services import story_service

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("/{story_id}", response_class=HTMLResponse)
async def get_story_detail(
    request: Request,
    story_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get story details"""
    story = await story_service.get_story_full(db, story_id)
    
    context = {
        "request": request,
        "story": story
    }
    
    template = get_template(
        request,
        wrapper="pages/story_detail.html",
        partial="pages/partials/_story_detail_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/{story_id}/code", response_class=HTMLResponse)
async def get_story_code_view(
    request: Request,
    story_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get code view for story"""
    data = await story_service.get_code_deliverables(db, story_id)
    
    context = {
        "request": request,
        "story_uuid": story_id,
        "story_title": data.get("story_title", "Story"),
        "project_name": data.get("project_name", ""),
        "epic_name": data.get("epic_name", ""),
        "files": data.get("files", [])
    }
    
    template = get_template(
        request,
        wrapper="pages/story_code.html",
        partial="pages/partials/_story_code_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/{story_id}/code/file/{file_index}", response_class=HTMLResponse)
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


@router.get("/{story_id}/code/download")
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

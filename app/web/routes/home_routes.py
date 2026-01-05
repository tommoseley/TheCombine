"""
Home routes for The Combine UI
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_optional_user
from .shared import templates

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Home page - renders base.html with empty document container.
    The base template includes the projects sidebar and a welcome message.
    """
    # Get user info if logged in
    user_info = await get_optional_user(request, db)
    user = user_info[0] if user_info else None
    
    return templates.TemplateResponse(request, "layout/base.html", {
        "user": user,
    })
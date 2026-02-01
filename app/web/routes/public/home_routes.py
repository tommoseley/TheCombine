"""
Home routes for The Combine UI
"""

import pathlib
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_optional_user
from ..shared import templates

router = APIRouter(tags=["home"])

# Check if SPA is available
SPA_INDEX = pathlib.Path("spa/dist/index.html")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Home page - serves SPA for authenticated users, Jinja template for guests.
    """
    user_info = await get_optional_user(request, db)
    user = user_info[0] if user_info else None

    # Authenticated users get the SPA
    if user and SPA_INDEX.exists():
        return FileResponse(SPA_INDEX, media_type="text/html")

    # Guests get the original home page
    return templates.TemplateResponse(request, "public/pages/home.html", {
        "user": user,
    })
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
    Home page - serves SPA for all users.
    The SPA handles its own auth state (Lobby vs Production).
    """
    # Always serve SPA if available
    if SPA_INDEX.exists():
        return FileResponse(SPA_INDEX, media_type="text/html")

    # Fallback to Jinja template only if SPA not built
    user_info = await get_optional_user(request, db)
    user = user_info[0] if user_info else None

    return templates.TemplateResponse(request, "public/pages/home.html", {
        "user": user,
    })


@router.get("/learn", response_class=HTMLResponse)
async def learn():
    """
    Learn More page - serves SPA which handles client-side routing.
    This is a Lobby page (unauthenticated).
    """
    if SPA_INDEX.exists():
        return FileResponse(SPA_INDEX, media_type="text/html")

    # If SPA not built, redirect to home
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/")


@router.get("/admin/workbench", response_class=HTMLResponse)
async def admin_workbench():
    """
    Admin Workbench - serves SPA which handles client-side routing.
    Auth check is done by SPA (redirects to Lobby if not authenticated).
    """
    if SPA_INDEX.exists():
        return FileResponse(SPA_INDEX, media_type="text/html")

    # If SPA not built, redirect to home
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/")
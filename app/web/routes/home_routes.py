"""
Home routes for The Combine UI
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .shared import templates

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page - renders base.html with empty document container.
    The base template includes the projects sidebar and a welcome message.
    """
    print("HOME ROUTE HIT!")  # Add this
    return templates.TemplateResponse("layout/base.html", {"request": request})
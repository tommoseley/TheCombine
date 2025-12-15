"""
Home routes for The Combine UI
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .shared import templates, get_template

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - shows base layout with welcome content"""
    try:
        template = get_template(
            request,
            wrapper="pages/home.html",
            partial="pages/partials/_home_content.html"
        )
        return templates.TemplateResponse(template, {"request": request})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
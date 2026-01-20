"""
Concierge web routes - Legacy redirect.

Entry point: /start -> redirects to /intake (workflow engine)
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["concierge-ui"])


@router.get("/start")
async def start_concierge(request: Request):
    """
    Redirect to workflow-based intake.

    Legacy /start now redirects to /intake (ADR-039 workflow engine).
    """
    return RedirectResponse(url="/intake", status_code=302)

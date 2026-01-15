"""
Concierge web routes - Conversational intake interface.

Entry point: /start
- Creates new session and serves chat UI
- Redirects to login if not authenticated
- Returns partial for HTMX requests, full page otherwise
"""

import uuid as uuid_module
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_optional_user
from app.web.routes.shared import templates

router = APIRouter(tags=["concierge-ui"])


def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/start", response_class=HTMLResponse)
async def start_concierge(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Canonical entry point for new project creation.
    
    Creates a new concierge session and serves the chat UI.
    Redirects to login if not authenticated.
    Returns partial for HTMX, full page for direct navigation.
    """
    # Check authentication
    user_data = await get_optional_user(request, db)
    
    if not user_data:
        # Not logged in - redirect to login
        return RedirectResponse(url="/web/static/public/login.html", status_code=302)
    
    user, _, _ = user_data
    
    # Create new session
    session_id = uuid_module.uuid4()
    now = datetime.utcnow()
    expires = now + timedelta(hours=24)
    
    await db.execute(text("""
        INSERT INTO concierge_intake_session 
        (id, user_id, state, created_at, updated_at, expires_at, origin_route, version)
        VALUES (:id, :user_id, 'active', :now, :now, :expires, '/start', '1.0')
    """), {
        "id": session_id,
        "user_id": user.user_id,
        "now": now,
        "expires": expires
    })
    await db.commit()
    
    context = {
        "request": request,
        "session_id": str(session_id),
        "messages": []
    }
    
    # HTMX request - return just the content partial
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request,
            "concierge/partials/_chat_content.html",
            context
        )
    
    # Full page request - return page with base.html
    return templates.TemplateResponse(
        request,
        "concierge/chat.html",
        context
    )
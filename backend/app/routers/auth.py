"""
Authentication router for magic link flow.

Implements passwordless authentication via email magic links.
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone  
from typing import Optional
import secrets
import bcrypt
import logging
from uuid import uuid4
from app.dependencies import get_db

from app.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# These will be set by main.py after models are imported
SessionModel = None
PendingTokenModel = None


def set_auth_models(session_model, pending_token_model):
    """Set model references after they're created in main.py."""
    global SessionModel, PendingTokenModel
    SessionModel = session_model
    PendingTokenModel = pending_token_model


def _now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace('+00:00', 'Z')



@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Display magic link login form."""
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html"
    )


@router.post("/login")
async def send_magic_link(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Generate magic link token and send email.
    
    POST /login
    Form data: email
    
    Rate limit: 5 requests per email per 10 minutes
    """
    # Normalize email
    email = email.lower().strip()
    
    # Validate email format (basic)
    if '@' not in email or '.' not in email.split('@')[1]:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    # Check rate limit
    can_send, retry_after = email_service.can_send_magic_link(email)
    if not can_send:
        logger.warning(f"Rate limit exceeded for {email}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please try again in {retry_after} seconds."
        )
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    token_hash = bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
    
    # Delete any existing pending tokens for this email (cleanup)
    db.query(PendingTokenModel).filter(
        PendingTokenModel.email == email
    ).delete()
    db.commit()
    
    # Create pending token
    now = _now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat() + "Z"
    
    pending_token = PendingTokenModel(
        token_hash=token_hash,
        email=email,
        expires_at=expires_at,
        created_at=now
    )
    db.add(pending_token)
    db.commit()
    
    # Build magic link URL
    base_url = str(request.base_url).rstrip('/')
    magic_link = f"{base_url}/magic-login?token={token}"
    
    # Send email
    success = email_service.send_magic_link(email, magic_link)
    
    if not success:
        logger.error(f"Failed to send magic link to {email}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Please try again later."
        )
    
    logger.info(f"Magic link sent to {email}")
    
    # Return success
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "message": "Magic link sent! Check your email to log in.",
            "email": email
        }
    )

@router.get("/magic-login")
async def validate_magic_link(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate magic link token and create session.
    
    GET /magic-login?token=...
    
    On success: Sets session cookie and redirects to /workspaces
    On failure: Returns 401 with error message
    """
    now = datetime.now(timezone.utc)
    now_iso = _now_iso()
    
    pending_tokens = db.query(PendingTokenModel).filter(
        PendingTokenModel.expires_at > now_iso
    ).all()
    
    valid_token = None
    for pending in pending_tokens:
        try:
            if bcrypt.checkpw(token.encode(), pending.token_hash.encode()):
                valid_token = pending
                break
        except Exception as e:
            logger.warning(f"Error checking token: {e}")
            continue
    
    if not valid_token:
        logger.warning("Invalid or expired magic link token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please request a new magic link."
        )
    
    # Token is valid - create session
    session_id = str(uuid4())
    expires_at = (now + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
    
    session = SessionModel(
        id=session_id,
        email=valid_token.email,
        expires_at=expires_at,
        created_at=now_iso
    )
    db.add(session)
    
    # Delete used token (single-use enforcement)
    db.delete(valid_token)
    db.commit()
    
    logger.info(f"Session created for {valid_token.email}")
    
    # Create redirect response and set cookie on it
    response = RedirectResponse(url="/workspaces", status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,  # HTTPS only in production
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days in seconds
    )
    
    return response

@router.post("/logout")
async def logout(
    response: Response,
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Logout user by deleting session and clearing cookie.
    
    POST /logout
    """
    if session_id:
        # Delete session from database
        deleted_count = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).delete()
        db.commit()
        
        if deleted_count > 0:
            logger.info(f"Session {session_id} deleted")
    
    # Clear session cookie
    response.delete_cookie("session_id")
    
    return RedirectResponse(url="/login", status_code=303)


@router.get("/me")
async def get_me(
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Get information about the currently authenticated user.
    
    GET /me
    
    Returns:
        JSON with user email and session information
        
    Raises:
        HTTPException 401: If no valid session exists or session is expired
    
    Example response:
        {
            "email": "user@example.com",
            "session_id": "uuid-here",
            "expires_at": "2024-12-07T10:30:00Z",
            "created_at": "2024-11-30T15:30:00Z"
        }
    """
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    # Lookup session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )
    
    # Check expiration
    if session.is_expired():
        # Delete expired session
        db.delete(session)
        db.commit()
        logger.info(f"Expired session {session_id} deleted")
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again."
        )
    
    # Return user information
    return JSONResponse(
        status_code=200,
        content={
            "email": session.email,
            "session_id": session.id,
            "expires_at": session.expires_at,
            "created_at": session.created_at
        }
    )


async def get_current_user(
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> str:
    """
    FastAPI dependency to get current authenticated user.
    
    Returns user's email address.
    Raises HTTPException(401) if not authenticated.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user_email: str = Depends(get_current_user)):
            return {"user": user_email}
    """
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    # Lookup session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )
    
    # Check expiration
    if session.is_expired():
        # Delete expired session
        db.delete(session)
        db.commit()
        logger.info(f"Expired session {session_id} deleted")
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again."
        )
    
    return session.email

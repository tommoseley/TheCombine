"""
Authentication middleware dependencies.

ADR-008: Multi-Provider OAuth Authentication
FastAPI dependencies for route protection and user context.

Stage 5: Auth Middleware
"""
from typing import Optional, Tuple
from fastapi import Request, HTTPException, Depends, status
from uuid import UUID
import os
import logging

from app.auth.models import User, AuthContext
from app.auth.service import AuthService
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _get_cookie_name(name: str) -> str:
    """
    Get cookie name with __Host- prefix in production.
    
    Args:
        name: Base cookie name ('session' or 'csrf')
        
    Returns:
        Cookie name with __Host- prefix if production
    """
    production = os.getenv('HTTPS_ONLY', 'false').lower() == 'true'
    if production:
        return f"__Host-{name}"
    return name


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[Tuple[User, UUID, str]]:
    """
    Get current user from session cookie (optional).
    
    Returns None if not authenticated. Does NOT raise exceptions.
    Use this when authentication is optional for a route.
    
    Args:
        request: FastAPI Request
        db: Database session
        
    Returns:
        Tuple of (User, session_id, csrf_token) or None if not authenticated
    """
    # Get session token from cookie
    session_cookie_name = _get_cookie_name('session')
    session_token = request.cookies.get(session_cookie_name)
    
    if not session_token:
        return None
    
    # Verify session
    auth_service = AuthService(db)
    result = await auth_service.verify_session(session_token)
    
    if not result:
        # Invalid or expired session - don't raise error, just return None
        logger.debug(f"Invalid/expired session token from {request.client.host}")
        return None
    
    return result


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Tuple[User, UUID, str]:
    """
    Get current authenticated user (required).
    
    Raises 401 Unauthorized if not authenticated.
    Use this to protect routes that require authentication.
    
    Args:
        request: FastAPI Request
        db: Database session
        
    Returns:
        Tuple of (User, session_id, csrf_token)
        
    Raises:
        HTTPException: 401 if not authenticated
    """
    result = await get_optional_user(request, db)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return result


async def require_auth(
    user_data: Tuple[User, UUID, str] = Depends(get_current_user)
) -> User:
    """
    Require authentication and return just the User object.
    
    Convenience dependency that returns only the User (not session_id/csrf_token).
    Use this when you just need the user object.
    
    Args:
        user_data: User tuple from get_current_user
        
    Returns:
        User object
    """
    user, _, _ = user_data
    return user


async def get_auth_context(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AuthContext:
    """
    Get authentication context (user + session metadata).
    
    Returns full AuthContext with user, session_id, and auth type.
    Raises 401 if not authenticated.
    
    Args:
        request: FastAPI Request
        db: Database session
        
    Returns:
        AuthContext with user and session info
        
    Raises:
        HTTPException: 401 if not authenticated
    """
    user, session_id, csrf_token = await get_current_user(request, db)
    
    return AuthContext(
        user=user,
        session_id=session_id,
        token_id=None,  # Session auth, not token auth
        csrf_token=csrf_token
    )


async def get_optional_auth_context(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[AuthContext]:
    """
    Get optional authentication context.
    
    Returns AuthContext if authenticated, None otherwise.
    Does NOT raise exceptions.
    
    Args:
        request: FastAPI Request
        db: Database session
        
    Returns:
        AuthContext or None
    """
    result = await get_optional_user(request, db)
    
    if not result:
        return None
    
    user, session_id, csrf_token = result
    
    return AuthContext(
        user=user,
        session_id=session_id,
        token_id=None,  # Session auth, not token auth
        csrf_token=csrf_token
    )
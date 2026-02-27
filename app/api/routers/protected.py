"""
Example protected routes.

Demonstrates how to use authentication middleware.
"""
from fastapi import APIRouter, Depends
from typing import Optional

from app.auth.models import User, AuthContext
from app.auth.dependencies import (
    require_auth,
    get_auth_context,
    get_optional_auth_context
)

router = APIRouter(prefix="/api", tags=["examples"])


# ============================================================================
# EXAMPLE 1: Public route (no auth required)
# ============================================================================

@router.get("/public")
async def public_route():
    """
    Public route - anyone can access.
    
    No authentication required.
    """
    return {
        "message": "This is a public endpoint",
        "authenticated": False
    }


# ============================================================================
# EXAMPLE 2: Optional authentication
# ============================================================================

@router.get("/optional-auth")
async def optional_auth_route(
    auth_context: Optional[AuthContext] = Depends(get_optional_auth_context)
):
    """
    Route with optional authentication.
    
    Shows different content based on whether user is logged in.
    """
    if auth_context:
        return {
            "message": f"Hello, {auth_context.user.name}!",
            "authenticated": True,
            "user_id": str(auth_context.user.user_id),
            "email": auth_context.user.email,
            "name": auth_context.user.name,
            "avatar_url": auth_context.user.avatar_url,
            "is_admin": auth_context.user.is_admin
        }
    else:
        return {
            "message": "Hello, anonymous user!",
            "authenticated": False
        }


# ============================================================================
# EXAMPLE 3: Required authentication (simple)
# ============================================================================

@router.get("/profile")
async def get_profile(
    user: User = Depends(require_auth)
):
    """
    Protected route - authentication required.
    
    Returns 401 if not authenticated.
    Uses require_auth for simple user access.
    """
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "email_verified": user.email_verified,
        "created_at": user.user_created_at.isoformat(),
        "last_login": user.last_login_at.isoformat() if user.last_login_at else None
    }


# ============================================================================
# EXAMPLE 4: Required authentication (with session info)
# ============================================================================

@router.get("/me")
async def get_me(
    auth_context: AuthContext = Depends(get_auth_context)
):
    """
    Protected route with full auth context.
    
    Returns user info plus session metadata.
    """
    return {
        "user": {
            "user_id": str(auth_context.user.user_id),
            "email": auth_context.user.email,
            "name": auth_context.user.name,
            "avatar_url": auth_context.user.avatar_url,
            "is_admin": auth_context.user.is_admin
        },
        "session": {
            "session_id": str(auth_context.session_id),
            "is_session_auth": auth_context.is_session_auth,
            "is_token_auth": auth_context.is_token_auth
        }
    }


# ============================================================================
# EXAMPLE 5: Protected POST route (uses CSRF token)
# ============================================================================

@router.post("/update-profile")
async def update_profile(
    name: str,
    auth_context: AuthContext = Depends(get_auth_context)
):
    """
    Protected POST route.
    
    Would need CSRF token validation for state-changing operations.
    (CSRF validation would be added in a separate middleware)
    """
    # In a real app, you'd update the user in the database here
    return {
        "message": "Profile updated",
        "user_id": str(auth_context.user.user_id),
        "new_name": name,
        "csrf_token": auth_context.csrf_token  # Available for validation
    }


# ============================================================================
# EXAMPLE 6: Admin-only route
# ============================================================================

@router.get("/admin")
async def admin_route(
    user: User = Depends(require_auth)
):
    """
    Admin-only route.
    
    You could add custom role checking here.
    """
    # Example: Check if user has admin role
    # (You'd need to add roles to your User model)
    # if not user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "message": "Admin access granted",
        "user_email": user.email
    }
"""Authentication middleware for protecting routes."""

from functools import wraps
from typing import Callable, List, Optional

from fastapi import HTTPException, Request, status

from app.auth.models import User, AuthContext, PersonalAccessToken
from app.auth.permissions import Permission, has_permission
from app.auth.services import SessionService, hash_token
from app.auth.pat_service import PATService, hash_pat


class AuthMiddleware:
    """
    Middleware for authenticating requests via session cookie or PAT.
    
    Attaches user to request.state.user if authenticated.
    """
    
    def __init__(
        self,
        session_service: SessionService,
        pat_service: PATService,
        session_cookie_name: str = "session",
    ):
        self._session_service = session_service
        self._pat_service = pat_service
        self._cookie_name = session_cookie_name
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        """
        Attempt to authenticate the request.
        
        Checks:
        1. Authorization header for PAT (Bearer token)
        2. Session cookie for browser auth
        
        Returns:
            AuthContext if authenticated, None otherwise
        """
        # Check for PAT in Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Strip "Bearer "
            if token.startswith("pat_"):
                return await self._authenticate_pat(token)
        
        # Check for session cookie
        session_token = request.cookies.get(self._cookie_name)
        if session_token:
            return await self._authenticate_session(session_token)
        
        return None
    
    async def _authenticate_session(self, token: str) -> Optional[AuthContext]:
        """Authenticate via session token."""
        result = await self._session_service.validate_session(token)
        if not result:
            return None
        
        user, session = result
        return AuthContext(
            user=user,
            session_id=session.session_id,
            token_id=None,
            csrf_token=None,
        )
    
    async def _authenticate_pat(self, token: str) -> Optional[AuthContext]:
        """Authenticate via PAT."""
        pat = await self._pat_service.validate_token(token)
        if not pat:
            return None
        
        # Need to look up the user - for now create minimal user context
        # In production, PAT validation would include user lookup
        return AuthContext(
            user=None,  # Would be populated from user lookup
            session_id=None,
            token_id=pat.token_id,
            csrf_token=None,
        )


def _get_request_from_args(args, kwargs) -> Optional[Request]:
    """Extract request object from function arguments."""
    if "request" in kwargs:
        return kwargs["request"]
    if args:
        return args[0]
    return None


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication on a route.
    
    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_route(request: Request):
            user = request.state.user
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = _get_request_from_args(args, kwargs)
        
        if request is None:
            raise ValueError("Request object not found in arguments")
        
        if not hasattr(request.state, "auth_context") or request.state.auth_context is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_permission(permission: Permission) -> Callable:
    """
    Decorator to require a specific permission.
    
    Usage:
        @router.post("/admin-action")
        @require_permission(Permission.ADMIN)
        async def admin_action(request: Request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _get_request_from_args(args, kwargs)
            
            if request is None:
                raise ValueError("Request object not found in arguments")
            
            if not hasattr(request.state, "auth_context") or request.state.auth_context is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            auth_context: AuthContext = request.state.auth_context
            if not auth_context.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User context required",
                )
            
            if not has_permission(auth_context.user.roles, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value} required",
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_any_permission(permissions: List[Permission]) -> Callable:
    """
    Decorator to require any of the specified permissions.
    
    Usage:
        @router.get("/resource")
        @require_any_permission([Permission.EXECUTION_READ, Permission.ADMIN])
        async def get_resource(request: Request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _get_request_from_args(args, kwargs)
            
            if request is None:
                raise ValueError("Request object not found in arguments")
            
            if not hasattr(request.state, "auth_context") or request.state.auth_context is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            auth_context: AuthContext = request.state.auth_context
            if not auth_context.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User context required",
                )
            
            for permission in permissions:
                if has_permission(auth_context.user.roles, permission):
                    return await func(*args, **kwargs)
            
            perm_list = ", ".join(p.value for p in permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: one of [{perm_list}] required",
            )
        
        return wrapper
    
    return decorator

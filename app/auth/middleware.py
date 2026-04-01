"""Authentication middleware decorators for protecting routes."""

from functools import wraps
from typing import Callable, List, Optional

from fastapi import HTTPException, Request, status

from app.auth.models import AuthContext
from app.auth.permissions import Permission, has_permission


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

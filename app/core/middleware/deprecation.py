"""
Deprecation Middleware for WS-DOCUMENT-SYSTEM-CLEANUP Phase 5.

Adds Warning headers to deprecated routes and logs usage for monitoring.
Per HTTP RFC 7234: Warning: 299 - "message"
"""

import logging
from typing import Callable, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse

logger = logging.getLogger(__name__)


# =============================================================================
# DEPRECATED ROUTES REGISTRY
# =============================================================================
# Maps deprecated route patterns to their canonical replacements and messages.
# Format: { "path_pattern": {"redirect_to": "new_path", "message": "reason"} }

DEPRECATED_ROUTES: Dict[str, Dict[str, str]] = {
    # View routes -> document routes
    "/view/ArchitecturalSummaryView": {
        "redirect_to": "/projects/{project_id}/documents/technical_architecture",
        "message": "Use /projects/{project_id}/documents/technical_architecture instead",
    },
    "/view/ProjectDiscovery": {
        "redirect_to": "/projects/{project_id}/documents/project_discovery",
        "message": "Use /projects/{project_id}/documents/project_discovery instead",
    },
    # Phase 7: API document routes -> command routes
    "/api/documents/build/": {
        "redirect_to": "/api/commands/documents/{doc_type_id}/build",
        "message": "Use POST /api/commands/documents/{doc_type_id}/build instead",
    },
}


def get_deprecation_info(path: str) -> Optional[Dict[str, str]]:
    """
    Check if a path matches a deprecated route pattern.
    
    Returns deprecation info dict or None if not deprecated.
    """
    # Exact match first
    if path in DEPRECATED_ROUTES:
        return DEPRECATED_ROUTES[path]
    
    # Check for prefix matches (e.g., /view/ routes)
    for pattern, info in DEPRECATED_ROUTES.items():
        if path.startswith(pattern.rstrip("/")):
            return info
    
    return None


class DeprecationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds Warning headers to deprecated routes.
    
    Per WS-DOCUMENT-SYSTEM-CLEANUP Phase 5:
    - Adds Warning: 299 - "Deprecated" header
    - Logs all deprecated route hits for monitoring
    - Does NOT redirect (caller handles redirect if needed)
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and add deprecation warning if needed."""
        
        deprecation_info = get_deprecation_info(request.url.path)
        
        if deprecation_info:
            # Log deprecated route usage
            logger.warning(
                f"DEPRECATED_ROUTE_HIT: {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'} "
                f"-> {deprecation_info['message']}"
            )
        
        # Call the actual route handler
        response = await call_next(request)
        
        # Add warning header if deprecated
        if deprecation_info:
            # RFC 7234 Warning header format: warn-code warn-agent "warn-text"
            warning_value = f'299 - "Deprecated: {deprecation_info["message"]}"'
            response.headers["Warning"] = warning_value
            
            # Also add Deprecation header (draft standard)
            response.headers["Deprecation"] = "true"
            
            # Add Sunset header if we want to indicate removal date
            # response.headers["Sunset"] = "Sat, 01 Mar 2026 00:00:00 GMT"
        
        return response


def add_deprecation_warning(
    response: Response,
    message: str,
) -> Response:
    """
    Helper to add deprecation warning to a response.
    
    Use this in route handlers that need custom deprecation logic.
    """
    warning_value = f'299 - "Deprecated: {message}"'
    response.headers["Warning"] = warning_value
    response.headers["Deprecation"] = "true"
    return response


def create_deprecated_redirect(
    redirect_to: str,
    message: str,
    status_code: int = 307,  # Temporary redirect, preserves method
) -> RedirectResponse:
    """
    Create a redirect response with deprecation warning headers.
    
    Args:
        redirect_to: URL to redirect to
        message: Deprecation message
        status_code: HTTP status (307 = temporary, 308 = permanent)
        
    Returns:
        RedirectResponse with Warning header
    """
    response = RedirectResponse(
        url=redirect_to,
        status_code=status_code,
    )
    
    warning_value = f'299 - "Deprecated: {message}"'
    response.headers["Warning"] = warning_value
    response.headers["Deprecation"] = "true"
    
    logger.warning(f"DEPRECATED_REDIRECT: {message} -> {redirect_to}")
    
    return response
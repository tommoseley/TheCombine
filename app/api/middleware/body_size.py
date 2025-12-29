"""
Request body size limiting middleware.

Prevents memory exhaustion from large payloads.
"""

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class BodySizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce maximum request body size.
    
    Prevents memory exhaustion from large payloads.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Check request body size before processing."""
        # Only check POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            # Read body
            body = await request.body()
            
            # Get max size (default 10MB if not configured)
            max_size = getattr(settings, 'MAX_REQUEST_BODY_SIZE', 10 * 1024 * 1024)
            
            # Check size
            if len(body) > max_size:
                request_id = getattr(request.state, "request_id", "unknown")
                logger.warning(
                    f"[{request_id}] Request body too large: {len(body)} bytes "
                    f"(max: {max_size})"
                )
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "payload_too_large",
                        "message": f"Request body exceeds maximum size of {max_size} bytes",
                        "request_id": request_id
                    }
                )
            
            # Store body for later access (since we've already read it)
            request._body = body
        
        # Process request
        response = await call_next(request)
        return response
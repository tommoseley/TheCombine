"""Request body size limiting middleware."""

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from workforce.utils.logging import log_warning


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
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
            
            # Check size
            if len(body) > settings.MAX_REQUEST_BODY_SIZE:
                request_id = getattr(request.state, "request_id", "unknown")
                log_warning(
                    f"[{request_id}] Request body too large: {len(body)} bytes "
                    f"(max: {settings.MAX_REQUEST_BODY_SIZE})"
                )
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "payload_too_large",
                        "message": f"Request body exceeds maximum size of {settings.MAX_REQUEST_BODY_SIZE} bytes",
                        "request_id": request_id
                    }
                )
            
            # Store body for later access (since we've already read it)
            request._body = body
        
        # Process request
        response = await call_next(request)
        return response
"""Request logging middleware."""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from workforce.utils.logging import log_info


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests with request ID."""
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response with request ID."""
        start_time = time.time()
        
        # Get request ID from state (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        log_info(f"[{request_id}] Request: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration_ms = int((time.time() - start_time) * 1000)
        log_info(f"[{request_id}] Response: {response.status_code} ({duration_ms}ms)")
        
        return response
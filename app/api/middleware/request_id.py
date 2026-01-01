"""
Request ID and Correlation ID Middleware.

Generates/extracts unique identifiers for request tracing.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from uuid import uuid4

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate/extract request IDs and correlation IDs.
    
    Request ID: Unique per HTTP request (for HTTP tracing)
    Correlation ID: Tracks related operations (for LLM logging, cross-service tracing)
    
    Headers:
    - X-Request-ID: Client can provide, or we generate
    - X-Correlation-ID: Client can provide, or defaults to request_id
    
    Both stored in request.state as strings for downstream use.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        
        # Extract correlation ID, or default to request_id
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        
        # Store as strings (consistent types)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        # Call next middleware/endpoint
        response = await call_next(request)
        
        # Add headers to response for client tracing
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
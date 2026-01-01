"""
Correlation ID middleware.

Converts X-Correlation-ID header (string) to UUID once.
Stores as UUID in request.state for downstream use.
"""

from uuid import UUID, uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Extract or generate correlation ID from request.
    
    - Accepts X-Correlation-ID header as string
    - Converts to UUID (or generates new one)
    - Stores as UUID in request.state.correlation_id
    - Echoes back in response headers
    """
    
    async def dispatch(self, request: Request, call_next):
        header_value = request.headers.get("X-Correlation-ID")
        
        if header_value:
            try:
                correlation_id = UUID(header_value)
            except ValueError:
                logger.warning(f"Invalid correlation ID format: {header_value}, generating new")
                correlation_id = uuid4()
        else:
            correlation_id = uuid4()
        
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        
        response.headers["X-Correlation-ID"] = str(correlation_id)
        
        return response

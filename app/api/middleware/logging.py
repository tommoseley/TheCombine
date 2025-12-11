"""
Logging middleware for The Combine API.

Provides request/response logging and performance tracking.
"""

import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    
    Logs:
    - Request method, path, client IP
    - Response status code
    - Request duration
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log details."""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                f"Response: {response.status_code} "
                f"({duration_ms:.2f}ms) "
                f"for {request.method} {request.url.path}"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Error processing request: {request.method} {request.url.path} "
                f"({duration_ms:.2f}ms): {e}",
                exc_info=True
            )
            raise


# Legacy compatibility functions (for any code still using these)
def log_info(message: str) -> None:
    """Log info message."""
    logger.info(message)


def log_warning(message: str) -> None:
    """Log warning message."""
    logger.warning(message)


def log_error(message: str, exc_info: bool = False) -> None:
    """Log error message."""
    logger.error(message, exc_info=exc_info)


def log_debug(message: str) -> None:
    """Log debug message."""
    logger.debug(message)
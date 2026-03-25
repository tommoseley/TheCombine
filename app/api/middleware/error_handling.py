"""
Global exception handlers for The Combine API.

Provides consistent error responses across all endpoints.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI):
    """Add global exception handlers to FastAPI app."""

    # Import LLM error types for specific handling
    try:
        from app.llm.models import LLMOperationalError
    except ImportError:
        LLMOperationalError = None

    if LLMOperationalError:
        @app.exception_handler(LLMOperationalError)
        async def llm_operational_handler(request: Request, exc: LLMOperationalError):
            """Handle LLM operational errors (overloaded, rate limited, etc.)."""
            error_msg = str(exc).lower()
            if "overloaded" in error_msg or "529" in error_msg:
                logger.warning(f"LLM service overloaded: {exc}")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": "llm_overloaded",
                        "message": "The AI service is temporarily overloaded. Please wait a moment and try again.",
                        "retry_after": 30,
                        "request_id": getattr(request.state, "request_id", None),
                    },
                    headers={"Retry-After": "30"},
                )
            else:
                logger.error(f"LLM operational error: {exc}")
                return JSONResponse(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    content={
                        "error": "llm_error",
                        "message": "The AI service encountered an error. Please try again.",
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors."""
        logger.error(f"Validation error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )


class ErrorHandlingMiddleware:
    """
    Middleware for consistent error handling.
    
    This is used by FastAPI's add_middleware() method.
    """
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            logger.error(f"Middleware caught exception: {e}", exc_info=True)
            # Let FastAPI's exception handlers deal with it
            raise
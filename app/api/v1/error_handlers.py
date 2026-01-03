"""Error handlers for consistent API error responses."""

import logging
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from app.api.v1.exceptions import APIError


logger = logging.getLogger(__name__)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.to_dict(),
        },
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle FastAPI validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
            },
        },
    )


async def pydantic_error_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "error_code": "VALIDATION_ERROR",
                "message": "Data validation failed",
                "details": {"errors": errors},
            },
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    logger.exception(f"Unhandled error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with the app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_error_handler)
    # Note: Generic handler should be added carefully to avoid hiding errors during dev

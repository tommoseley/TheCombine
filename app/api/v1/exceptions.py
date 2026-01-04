"""Custom exceptions for API layer."""

from typing import Any, Dict, Optional


class APIError(Exception):
    """Base class for API errors."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(APIError):
    """Resource not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            message=f"{resource_type.title()} '{resource_id}' not found",
            status_code=404,
            details=details,
        )


class ValidationError(APIError):
    """Request validation failed."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class ConflictError(APIError):
    """Operation conflicts with current state."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            error_code="CONFLICT",
            message=message,
            status_code=409,
            details=details,
        )


class InvalidStateError(APIError):
    """Resource is in invalid state for operation."""
    
    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if current_state:
            details["current_state"] = current_state
        super().__init__(
            error_code="INVALID_STATE",
            message=message,
            status_code=409,
            details=details,
        )


class ServiceUnavailableError(APIError):
    """External service unavailable."""
    
    def __init__(
        self,
        service: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            error_code="SERVICE_UNAVAILABLE",
            message=message or f"{service} service is temporarily unavailable",
            status_code=503,
            details=details,
        )


class InternalError(APIError):
    """Internal server error."""
    
    def __init__(
        self,
        message: str = "An internal error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=500,
            details=details,
        )

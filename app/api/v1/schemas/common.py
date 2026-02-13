"""Common schema types for API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response format."""
    
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    
    model_config = {"json_schema_extra": {
        "example": {
            "error_code": "WORKFLOW_NOT_FOUND",
            "message": "Workflow 'unknown_wf' not found",
            "details": None,
            "request_id": "req_abc123"
        }
    }}


class PaginatedResponse(BaseModel):
    """Base for paginated responses."""
    
    total: int = Field(..., description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

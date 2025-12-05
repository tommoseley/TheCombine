"""Response Pydantic models for API endpoints."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for traceability")


class ArtifactMetadata(BaseModel):
    """
    Full artifact metadata (QA-Blocker #3 fix).
    
    Includes both artifact metadata and payload for complete traceability.
    """
    artifact_id: str
    artifact_type: str
    phase: str
    mentor_role: Optional[str]
    validation_status: str
    created_at: datetime
    payload: Dict[str, Any]


class PipelineCreatedResponse(BaseModel):
    """Response after creating a new pipeline."""
    pipeline_id: str
    epic_id: str
    state: str
    current_phase: str
    created_at: datetime


class PipelineStatusResponse(BaseModel):
    """
    Complete pipeline status response.
    
    QA-Blocker #3 fix: artifacts now include full metadata, not just payloads.
    """
    pipeline_id: str
    epic_id: str
    state: str
    current_phase: str
    artifacts: Dict[str, ArtifactMetadata] = Field(
        default_factory=dict,
        description="Artifacts keyed by artifact_type, with full metadata"
    )
    phase_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class PhaseAdvancedResponse(BaseModel):
    """Response after advancing pipeline phase."""
    pipeline_id: str
    previous_phase: str
    current_phase: str
    state: str
    updated_at: datetime


class ArtifactSubmittedResponse(BaseModel):
    """Response after submitting an artifact."""
    artifact_id: str
    pipeline_id: str
    artifact_type: str
    phase: str
    validation_status: str
    stored_at: datetime


class ResetResponse(BaseModel):
    """Response from reset operation."""
    success: bool
    canon_version: Optional[str] = None
    reason: Optional[str] = None
    in_flight_discarded: int = 0
    warnings: List[str] = Field(default_factory=list)


class CanonVersionResponse(BaseModel):
    """Canon version information."""
    version: str
    loaded_at: datetime
    source_path: str
    file_size_bytes: int
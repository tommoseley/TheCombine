"""Request Pydantic models for API endpoints."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# Maximum request body size (10MB)
MAX_ARTIFACT_SIZE_BYTES = 10 * 1024 * 1024


class PipelineStartRequest(BaseModel):
    """Request to start a new pipeline."""
    epic_id: str = Field(..., description="Epic identifier", json_schema_extra={"example": "PIPELINE-150"})
    initial_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context or human intent",
        json_schema_extra={
            "example": {"description": "Implement HTTP API Foundation"}
    }
)
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "epic_id": "PIPELINE-150",
                "initial_context": {
                    "description": "Create REST API for Orchestrator"
                }
            }
        }
    )


class ArtifactSubmissionRequest(BaseModel):
    """Request to submit an artifact for a pipeline phase."""
    phase: str = Field(..., description="Phase this artifact belongs to", json_schema_extra={"example": "pm_phase"})
    mentor_role: str = Field(..., description="Mentor role: pm, architect, ba, dev, qa", json_schema_extra={"example": "pm"})
    artifact_type: str = Field(
        ...,
        description="Artifact type: epic, arch_notes, ba_spec, proposed_change_set, qa_result",
        json_schema_extra={"example": "epic"}
    )
    payload: Dict[str, Any] = Field(..., description="Artifact content matching schema")
    
    @field_validator('payload')
    @classmethod
    def validate_payload_size(cls, v):
        """Validate payload size."""
        import json
        payload_size = len(json.dumps(v).encode('utf-8'))
        if payload_size > MAX_ARTIFACT_SIZE_BYTES:
            raise ValueError(f"Artifact payload exceeds maximum size of {MAX_ARTIFACT_SIZE_BYTES} bytes")
        return v
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "phase": "pm_phase",
                "mentor_role": "pm",
                "artifact_type": "epic",
                "payload": {
                    "epic_Id": "PIPELINE-150",
                    "title": "HTTP API Foundation",
                    "version": "v1.0",
                    "stories": []
                }
            }
        }
    )
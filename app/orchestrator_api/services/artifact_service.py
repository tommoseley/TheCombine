"""Artifact service: validation and storage."""

from typing import Dict, Any

from pydantic import ValidationError
from workforce.state import PipelineState
from workforce.schemas.artifacts import Epic, ArchitecturalNotes, BASpecification, ProposedChangeSet, QAResult
from app.orchestrator_api.persistence.repositories import ArtifactRepository, PipelineRepository
from app.orchestrator_api.schemas.responses import ArtifactSubmittedResponse
from workforce.utils.logging import log_info, log_error


# QA-Blocker #2: Artifact schema version tracking
# These schemas MUST match workforce/schemas/artifacts.py definitions
# Schema version: PIPELINE-100 v1.1 (December 2025)
# If schemas evolve, update this version and validate compatibility


class ArtifactValidationError(Exception):
    """Artifact validation failed."""
    def __init__(self, message: str, details: Dict[str, Any]):
        self.message = message
        self.details = details
        super().__init__(message)


class ArtifactService:
    """
    Service for artifact validation and storage.
    
    QA-Blocker #2: Schemas validated against workforce/schemas/artifacts.py
    """
    
    # Map artifact types to Pydantic models
    # QA-Blocker #2: These MUST match canonical schema definitions
    ARTIFACT_SCHEMAS = {
        "epic": Epic,
        "arch_notes": ArchitecturalNotes,
        "ba_spec": BASpecification,
        "proposed_change_set": ProposedChangeSet,
        "qa_result": QAResult,
    }
    
    # Map phases to expected artifact types
    PHASE_ARTIFACTS = {
        "pm_phase": "epic",
        "arch_phase": "arch_notes",
        "ba_phase": "ba_spec",
        "dev_phase": "proposed_change_set",
        "qa_phase": "qa_result",
    }
    
    def __init__(self):
        self.artifact_repo = ArtifactRepository()
        self.pipeline_repo = PipelineRepository()
    
    def submit_artifact(
        self,
        pipeline_id: str,
        phase: str,
        mentor_role: str,
        artifact_type: str,
        payload: Dict[str, Any]
    ) -> ArtifactSubmittedResponse:
        """
        Submit and validate artifact for a pipeline phase.
        
        Validates:
        1. Pipeline exists
        2. Phase is valid PipelineState enum value
        3. Phase matches pipeline's current phase
        4. Artifact type matches expected type for phase
        5. Payload conforms to artifact schema (QA-Blocker #2)
        6. Artifact epicId matches pipeline epic_id (if applicable)
        """
        # Check pipeline exists
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        # Validate phase is valid enum value
        try:
            phase_enum = PipelineState(phase)
        except ValueError:
            raise ArtifactValidationError(
                f"Invalid phase: {phase}",
                {"valid_phases": [p.value for p in PipelineState]}
            )
        
        # Validate phase matches current phase
        if phase_enum.value != pipeline.current_phase:
            raise ArtifactValidationError(
                f"Cannot submit {phase} artifact when pipeline is in {pipeline.current_phase}",
                {
                    "artifact_phase": phase,
                    "current_phase": pipeline.current_phase
                }
            )
        
        # Validate artifact type matches phase
        expected_type = self.PHASE_ARTIFACTS.get(phase)
        if artifact_type != expected_type:
            raise ArtifactValidationError(
                f"Phase {phase} expects artifact type '{expected_type}', got '{artifact_type}'",
                {
                    "expected_type": expected_type,
                    "actual_type": artifact_type
                }
            )
        
        # Validate payload against schema (QA-Blocker #2)
        schema = self.ARTIFACT_SCHEMAS.get(artifact_type)
        if not schema:
            raise ArtifactValidationError(
                f"Unknown artifact type: {artifact_type}",
                {"artifact_type": artifact_type}
            )
        
        try:
            # Validate with Pydantic against canonical schema
            validated = schema(**payload)
            log_info(f"Artifact {artifact_type} validated against schema version PIPELINE-100 v1.1")
        except ValidationError as e:
            log_error(f"Artifact validation failed: {e}")
            raise ArtifactValidationError(
                f"Artifact does not match {artifact_type} schema",
                {"validation_errors": e.errors()}  # ← Line 127: Make sure it says e.errors()
            )
        
        # Validate epicId matches pipeline epic_id (if artifact has epicId)
        if "epicId" in payload:
            if payload["epicId"] != pipeline.epic_id:
                raise ArtifactValidationError(
                    f"Artifact epicId '{payload['epicId']}' does not match pipeline epic_id '{pipeline.epic_id}'",
                    {
                        "artifact_epic_id": payload["epicId"],
                        "pipeline_epic_id": pipeline.epic_id
                    }
                )
        
        # Store artifact
        artifact = self.artifact_repo.create(
            pipeline_id=pipeline_id,
            artifact_type=artifact_type,
            phase=phase,
            payload=payload,
            mentor_role=mentor_role,
            validation_status="valid"
        )
        
        log_info(f"Artifact {artifact.artifact_id} stored for pipeline {pipeline_id}")
        
        return ArtifactSubmittedResponse(
            artifact_id=artifact.artifact_id,
            pipeline_id=artifact.pipeline_id,
            artifact_type=artifact.artifact_type,
            phase=artifact.phase,
            validation_status=artifact.validation_status,
            stored_at=artifact.created_at
        )
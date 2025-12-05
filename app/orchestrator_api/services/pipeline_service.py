"""Pipeline service: business logic for pipeline lifecycle."""

from typing import Optional, Dict, Any
from datetime import datetime

from workforce.orchestrator import Orchestrator
from workforce.state import PipelineState, validate_transition
from workforce.schemas.artifacts import Epic
from app.orchestrator_api.persistence.repositories import PipelineRepository, PhaseTransitionRepository
from app.orchestrator_api.schemas.responses import (
    PipelineCreatedResponse,
    PipelineStatusResponse,
    ArtifactMetadata,
    PhaseAdvancedResponse
)
from app.orchestrator_api.services.role_prompt_service import RolePromptService
from workforce.utils.logging import log_info, log_error
from workforce.utils.errors import InvalidStateTransitionError


class PipelineService:
    """
    Service for pipeline lifecycle management.
    
    Note: Orchestrator is stateless. All pipeline state lives in database.
    """
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.pipeline_repo = PipelineRepository()
        self.transition_repo = PhaseTransitionRepository()
        self.prompt_service = RolePromptService()
    
    def start_pipeline(self, epic_id: str, initial_context: Optional[Dict[str, Any]] = None) -> PipelineCreatedResponse:
        """
        Start a new pipeline.
        
        Creates database record as source of truth.
        """
        log_info(f"Starting pipeline for Epic {epic_id}")
        
        # Get current canon version
        canon_version = str(self.orchestrator.canon_manager.version_store.get_current_version())
        
        # Create database record (source of truth)
        pipeline = self.pipeline_repo.create(
            epic_id=epic_id,
            initial_context=initial_context,
            canon_version=canon_version
        )
        
        log_info(f"Pipeline {pipeline.pipeline_id} created for Epic {epic_id}")
        
        return PipelineCreatedResponse(
            pipeline_id=pipeline.pipeline_id,
            epic_id=pipeline.epic_id,
            state=pipeline.state,
            current_phase=pipeline.current_phase,
            created_at=pipeline.created_at
        )
    
    def get_status(self, pipeline_id: str) -> Optional[PipelineStatusResponse]:
        """
        Get pipeline status with artifacts and history.
        
        QA-Blocker #3 fix: Returns full artifact metadata, not just payloads.
        """
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None
        
        # Get artifacts with full metadata
        from app.orchestrator_api.persistence.repositories import ArtifactRepository
        artifacts = ArtifactRepository.get_by_pipeline_id(pipeline_id)
        
        # Build artifact metadata dict (QA-Blocker #3 fix)
        artifacts_dict = {
            artifact.artifact_type: ArtifactMetadata(
                artifact_id=artifact.artifact_id,
                artifact_type=artifact.artifact_type,
                phase=artifact.phase,
                mentor_role=artifact.mentor_role,
                validation_status=artifact.validation_status,
                created_at=artifact.created_at,
                payload=artifact.payload
            )
            for artifact in artifacts
        }
        
        # Get phase history
        transitions = self.transition_repo.get_by_pipeline_id(pipeline_id)
        phase_history = [
            {
                "from": t.from_state,
                "to": t.to_state,
                "timestamp": t.timestamp.isoformat(),
                "reason": t.reason
            }
            for t in transitions
        ]
        
        return PipelineStatusResponse(
            pipeline_id=pipeline.pipeline_id,
            epic_id=pipeline.epic_id,
            state=pipeline.state,
            current_phase=pipeline.current_phase,
            artifacts=artifacts_dict,
            phase_history=phase_history,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
            completed_at=pipeline.completed_at
        )
    
    def advance_phase(self, pipeline_id: str) -> PhaseAdvancedResponse:
        """
        Advance pipeline to next phase.
        
        Validates transition, updates database, records transition.
        
        Note: For MVP, state == current_phase (both store phase value).
        """
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        # Determine next phase based on current state
        current_state = PipelineState(pipeline.current_phase)
        next_state = self._get_next_phase(current_state)
        
        # Validate transition
        if not validate_transition(current_state, next_state):
            raise InvalidStateTransitionError(
                f"Cannot advance from {current_state.value} to {next_state.value}"
            )
        
        # Update pipeline (for MVP: state = phase)
        previous_phase = pipeline.current_phase
        updated_pipeline = self.pipeline_repo.update_state(
            pipeline_id=pipeline_id,
            new_state=next_state.value,  # For MVP: state stores phase
            new_phase=next_state.value
        )
        
        # Record transition
        self.transition_repo.create(
            pipeline_id=pipeline_id,
            from_state=previous_phase,
            to_state=next_state.value,
            reason="Phase advancement"
        )
        
        log_info(f"Pipeline {pipeline_id} transitioned from {previous_phase} to {next_state.value}")
        
        return PhaseAdvancedResponse(
            pipeline_id=updated_pipeline.pipeline_id,
            previous_phase=previous_phase,
            current_phase=updated_pipeline.current_phase,
            state=updated_pipeline.state,
            updated_at=updated_pipeline.updated_at
        )
    
    def _get_next_phase(self, current_phase: PipelineState) -> PipelineState:
        """Get next phase in sequence."""
        phase_sequence = {
            PipelineState.IDLE: PipelineState.PM_PHASE,
            PipelineState.PM_PHASE: PipelineState.ARCH_PHASE,
            PipelineState.ARCH_PHASE: PipelineState.BA_PHASE,
            PipelineState.BA_PHASE: PipelineState.DEV_PHASE,
            PipelineState.DEV_PHASE: PipelineState.QA_PHASE,
            PipelineState.QA_PHASE: PipelineState.COMMIT_PHASE,
            PipelineState.COMMIT_PHASE: PipelineState.COMPLETE,
        }
        
        next_phase = phase_sequence.get(current_phase)
        if next_phase is None:
            raise ValueError(f"Cannot advance from {current_phase.value}")
        
        return next_phase
    
    
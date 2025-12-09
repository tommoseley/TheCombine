"""Pipeline service: business logic for pipeline lifecycle."""

from typing import Optional, Dict, Any
from datetime import datetime
import os

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
from workforce.utils.logging import log_info, log_error, log_warning
from workforce.utils.errors import InvalidStateTransitionError

# PIPELINE-175B: Data-driven orchestration imports
from app.orchestrator_api.services.phase_execution_orchestrator import (
    PhaseExecutionOrchestrator,
    ExecutionError,
    PhaseExecutionResult
)
from app.orchestrator_api.services.llm_response_parser import LLMResponseParser
from app.orchestrator_api.services.llm_caller import LLMCaller
from app.orchestrator_api.services.configuration_loader import (
    ConfigurationLoader,
    ConfigurationError
)
from app.orchestrator_api.services.usage_recorder import UsageRecorder
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import (
    PhaseConfigurationRepository
)
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import (
    PipelinePromptUsageRepository
)

# Anthropic SDK import (optional - for data-driven mode)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False

# Feature flag (default: disabled for safety)
DATA_DRIVEN_ORCHESTRATION = os.getenv('DATA_DRIVEN_ORCHESTRATION', 'false').lower() == 'true'


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
        
        PIPELINE-175B: Routes to data-driven execution when feature flag enabled.
        
        Validates transition, updates database, records transition.
        
        Note: For MVP, state == current_phase (both store phase value).
        """
        # Check feature flag
        if DATA_DRIVEN_ORCHESTRATION:
            if not ANTHROPIC_AVAILABLE:
                log_error("DATA_DRIVEN_ORCHESTRATION enabled but anthropic SDK not available")
                raise RuntimeError(
                    "Data-driven orchestration requires anthropic SDK. "
                    "Install with: pip install anthropic"
                )
            return self._advance_phase_data_driven(pipeline_id)
        else:
            return self._advance_phase_legacy(pipeline_id)
    
    def _advance_phase_data_driven(self, pipeline_id: str) -> PhaseAdvancedResponse:
        """
        Data-driven phase advancement (PIPELINE-175B).
        
        Uses PhaseExecutionOrchestrator with configuration from database.
        """
        log_info(f"Using data-driven orchestration for pipeline {pipeline_id}")
        
        # Load pipeline
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        # Instantiate dependencies
        parser = LLMResponseParser()  # Default strategy ordering
        
        # Get Anthropic API key from environment
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        
        anthropic_client = anthropic.Anthropic(api_key=api_key)
        llm_caller = LLMCaller(anthropic_client)
        
        config_loader = ConfigurationLoader(PhaseConfigurationRepository())
        usage_recorder = UsageRecorder(PipelinePromptUsageRepository())
        prompt_builder = RolePromptService()
        
        # Instantiate orchestrator with all dependencies
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=config_loader,
            prompt_builder=prompt_builder,
            llm_caller=llm_caller,
            parser=parser,
            usage_recorder=usage_recorder
        )
        
        # Get current phase from pipeline
        current_phase = pipeline.current_phase
        
        # Execute phase
        try:
            result = orchestrator.execute_phase(
                pipeline_id=pipeline.pipeline_id,
                phase_name=current_phase,
                epic_context=pipeline.initial_context.get("epic_description", "") if pipeline.initial_context else "",
                pipeline_state=pipeline.state or {},
                artifacts=pipeline.state.get("artifacts", {}) if pipeline.state else {}
            )
            
            # QA Issue #5: State mutation happens HERE, not in orchestrator
            # Atomic update: either full success or no change
            if pipeline.state is None:
                pipeline.state = {}
            if "artifacts" not in pipeline.state:
                pipeline.state["artifacts"] = {}
            
            pipeline.state["artifacts"][result.artifact_type] = result.artifact
            previous_phase = pipeline.current_phase
            pipeline.current_phase = result.next_phase
            
            # QA Issue #8: Validate next_phase if not None
            if result.next_phase is not None:
                try:
                    config_loader.load_config(result.next_phase)
                except ConfigurationError as ce:
                    log_error(f"Invalid next_phase: {result.next_phase} does not exist")
                    raise ExecutionError(
                        f"Invalid next_phase configuration: {result.next_phase}",
                        previous_phase,
                        pipeline_id
                    )
            
            # Update pipeline state
            updated_pipeline = self.pipeline_repo.update_state(
                pipeline_id=pipeline_id,
                new_state=result.next_phase if result.next_phase else "complete",
                new_phase=result.next_phase if result.next_phase else "complete"
            )
            
            # Record transition
            self.transition_repo.create(
                pipeline_id=pipeline_id,
                from_state=previous_phase,
                to_state=result.next_phase if result.next_phase else "complete",
                reason="Data-driven phase execution"
            )
            
            log_info(f"Pipeline {pipeline_id} advanced from {previous_phase} to {result.next_phase}")
            
            return PhaseAdvancedResponse(
                pipeline_id=updated_pipeline.pipeline_id,
                previous_phase=previous_phase,
                current_phase=updated_pipeline.current_phase,
                state=updated_pipeline.state,
                updated_at=updated_pipeline.updated_at
            )
            
        except ExecutionError as e:
            log_error(f"Execution failed for pipeline {pipeline_id}: {e}")
            # Pipeline state unchanged (atomic operation)
            raise
    
    def _advance_phase_legacy(self, pipeline_id: str) -> PhaseAdvancedResponse:
        """
        Legacy phase advancement (PIPELINE-150 baseline).
        
        Uses hardcoded phase sequence and execution methods.
        Preserved for backward compatibility and safe rollback.
        """
        log_warning(
            f"Using legacy orchestration for pipeline {pipeline_id}. "
            "Consider enabling DATA_DRIVEN_ORCHESTRATION for enhanced capabilities."
        )
        
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
            reason="Phase advancement (legacy)"
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
        """Get next phase in sequence (legacy logic)."""
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
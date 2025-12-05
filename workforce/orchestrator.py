# workforce/orchestrator.py

"""Main Orchestrator for The Combine."""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field

from workforce.state import PipelineState, StateTransition, validate_transition
from workforce.canon_version_manager import CanonVersionManager
from workforce.mentor_dispatcher import MentorDispatcher
from workforce.schemas.artifacts import (
    Epic,
    PipelineResult,
    CommitResult,
    QAFeedback
)
from workforce.utils.errors import InvalidStateTransitionError
from workforce.utils.logging import get_logger, log_info, log_warning, log_error


@dataclass
class ClearedState:
    """State cleared by reset operation."""
    phase: PipelineState
    artifact_count: int


@dataclass
class ResetResult:
    """Result of /reset command."""
    success: bool
    canon_version: Optional[str] = None
    reason: Optional[str] = None
    in_flight_discarded: int = 0
    warnings: list = field(default_factory=list)


class Orchestrator:
    """
    Main Orchestrator managing pipeline execution through phases.
    
    Enforces canonical Pipeline Flow v1 with strict phase sequencing.
    """
    
    # Configuration
    MAX_QA_ATTEMPTS = 3
    ALLOW_RESET_IN_CRITICAL_PHASES = False  # Production: False, Dev: True
    
    def __init__(self, canon_manager: Optional[CanonVersionManager] = None):
        self.canon_manager = canon_manager or CanonVersionManager()
        self.mentor_dispatcher = MentorDispatcher()
        self.state = PipelineState.IDLE
        self.current_epic: Optional[Epic] = None
        self.artifacts = {}
        self.phase_history = []
        self.logger = get_logger("orchestrator")
        self._pipeline_counter = 0
    
    def initialize(self) -> None:
        """Initialize Orchestrator with canon loading."""
        log_info("Initializing Orchestrator...")
        self.canon_manager.load_canon()
        self._build_system_prompt()
        self._report_status()
        log_info("Orchestrator initialized successfully")
    
    def _generate_pipeline_id(self, epic: Epic) -> str:
        """Generate unique pipeline ID."""
        self._pipeline_counter += 1
        return f"pipeline-{epic.epic_id}-{self._pipeline_counter}"
    
    def execute_pipeline(self, epic: Epic) -> PipelineResult:
        """
        Execute complete pipeline for Epic with bounded QA rework.
        
        Phases: PM → Architect → BA → Dev → QA (loop if rejected) → Commit
        
        Returns:
            PipelineResult with success status and artifacts
        """
        # Generate unique pipeline ID
        pipeline_id = self._generate_pipeline_id(epic)
        
        log_info(f"Starting pipeline {pipeline_id} for Epic {epic.epic_id}")
        
        # STEP 1: Pre-execution version check
        if self.canon_manager.version_changed():
            log_info("Canon version changed, reloading...")
            self.canon_manager.reload_canon_with_buffer_swap()
        
        # STEP 2: Acquire canon buffer reference (CRITICAL)
        canon_buffer = self.canon_manager.buffer_manager.register_pipeline_reference(pipeline_id)
        
        log_info(
            f"Pipeline {pipeline_id} acquired canon buffer: "
            f"version={canon_buffer.version}, state={canon_buffer.state}"
        )
        
        try:
            result = self._execute_phases(epic, pipeline_id)
            
            log_info(f"Pipeline {pipeline_id} completed: success={result.success}")
            return result
        
        except Exception as e:
            log_error(f"Pipeline {pipeline_id} failed with exception: {e}")
            self._transition_to(PipelineState.FAILED)
            
            return PipelineResult(
                success=False,
                epic_id=epic.epic_id,
                failure_reason=str(e),
                pipeline_id=pipeline_id
            )
        
        finally:
            # STEP 3: Always unregister pipeline reference (CRITICAL)
            self.canon_manager.buffer_manager.unregister_pipeline_reference(pipeline_id)
            log_info(f"Pipeline {pipeline_id} released canon buffer reference")
    
    def _execute_phases(self, epic: Epic, pipeline_id: str) -> PipelineResult:
        """Execute all phases with bounded QA loop."""
        # PM Phase
        self._transition_to(PipelineState.PM_PHASE)
        # TODO: Invoke PM Mentor
        epic_result = epic
        
        # Architect Phase
        self._transition_to(PipelineState.ARCH_PHASE)
        # TODO: Invoke Architect Mentor
        # arch_notes = self.mentor_dispatcher.invoke_architect_mentor(epic_result)
        
        # BA Phase
        self._transition_to(PipelineState.BA_PHASE)
        # TODO: Invoke BA Mentor
        # ba_spec = self.mentor_dispatcher.invoke_ba_mentor(epic_result, arch_notes)
        
        # Developer → QA Loop (bounded)
        qa_attempt = 0
        qa_feedback = None
        
        while qa_attempt < self.MAX_QA_ATTEMPTS:
            qa_attempt += 1
            
            # Developer Phase
            self._transition_to(PipelineState.DEV_PHASE)
            # TODO: Invoke Dev Mentor with feedback
            # change_set = self.mentor_dispatcher.invoke_dev_mentor(ba_spec, qa_feedback)
            
            # QA Phase
            self._transition_to(PipelineState.QA_PHASE)
            # TODO: Invoke QA Mentor
            # qa_result = self.mentor_dispatcher.invoke_qa_mentor(change_set, ba_spec)
            
            # Simulated approval for now
            qa_approved = True
            
            if qa_approved:
                # QA approved → proceed to commit
                self._transition_to(PipelineState.COMMIT_PHASE)
                commit_result = self._execute_commit()
                self._transition_to(PipelineState.COMPLETE)
                
                return PipelineResult(
                    success=True,
                    epic_id=epic.epic_id,
                    commit=commit_result,
                    qa_attempts=qa_attempt,
                    pipeline_id=pipeline_id
                )
            else:
                # QA rejected → prepare feedback
                # TODO: Get actual feedback from QA result
                log_warning(
                    f"QA rejected Change Set (attempt {qa_attempt}/{self.MAX_QA_ATTEMPTS})"
                )
                continue
        
        # Max QA attempts exceeded
        self._transition_to(PipelineState.FAILED)
        log_error(f"Pipeline failed: Max QA attempts ({self.MAX_QA_ATTEMPTS}) exceeded")
        
        return PipelineResult(
            success=False,
            epic_id=epic.epic_id,
            failure_reason=f"QA rejected after {self.MAX_QA_ATTEMPTS} attempts",
            qa_attempts=qa_attempt,
            pipeline_id=pipeline_id
        )
    
    def _execute_commit(self) -> CommitResult:
        """Execute commit via /workforce/commit backend."""
        log_info("Executing commit...")
        # TODO: Implement actual commit execution
        return CommitResult(success=True, commit_sha="simulated", branch="feature/branch")
    
    def _transition_to(self, new_state: PipelineState) -> None:
        """
        Transition to new state with validation.
        
        Args:
            new_state: Target state
            
        Raises:
            InvalidStateTransitionError: If transition is invalid
        """
        if not validate_transition(self.state, new_state):
            raise InvalidStateTransitionError(
                f"Invalid transition: {self.state.value} → {new_state.value}"
            )
        
        transition = StateTransition(
            from_state=self.state,
            to_state=new_state,
            timestamp=datetime.now(),
            reason="Phase progression"
        )
        
        self.phase_history.append(transition)
        self.state = new_state
        
        log_info(f"State transition: {transition.from_state.value} → {transition.to_state.value}")
    
    def _build_system_prompt(self) -> None:
        """Build system prompt with current canon."""
        # TODO: Implement system prompt building
        log_info("System prompt built with canon content")
    
    def _report_status(self) -> None:
        """Report Orchestrator status."""
        current_version = self.canon_manager.version_store.get_current_version()
        log_info(f"Orchestrator ready: PIPELINE_FLOW_VERSION={current_version}, state={self.state.value}")
    
    def handle_reset(self) -> ResetResult:
        """
        Handle /reset command with guardrails.
        
        Guardrails:
        1. Warn if in-flight work exists
        2. Block if in critical phase (QA → Commit) in production
        3. Log reset event
        4. Reload canon and rebuild prompt
        5. Report readiness
        
        Returns:
            ResetResult with status and warnings
        """
        log_info("/reset command received")
        
        # GUARDRAIL 1: Check for in-flight work
        in_flight_count = len(self.canon_manager.buffer_manager._pipeline_refs)
        
        if in_flight_count > 0:
            log_warning(f"/reset requested with {in_flight_count} in-flight pipeline(s)")
        
        # GUARDRAIL 2: Block if in critical phase (production only)
        if not self.ALLOW_RESET_IN_CRITICAL_PHASES:
            if self.state in [PipelineState.QA_PHASE, PipelineState.COMMIT_PHASE]:
                log_error(
                    f"/reset blocked: cannot reset during critical phase {self.state.value}"
                )
                return ResetResult(
                    success=False,
                    reason=f"Reset blocked in critical phase: {self.state.value}",
                    in_flight_discarded=0
                )
        
        # STEP 1: Clear ephemeral state
        cleared_state = self._clear_ephemeral_state()
        
        log_info(
            f"Ephemeral state cleared: "
            f"phase={cleared_state.phase.value}, "
            f"artifacts={cleared_state.artifact_count}"
        )
        
        # STEP 2: Reload canon
        try:
            self.canon_manager.reload_canon_with_buffer_swap()
        except Exception as e:
            log_error(f"Canon reload failed during /reset: {e}")
            return ResetResult(
                success=False,
                reason=f"Canon reload failed: {e}",
                in_flight_discarded=in_flight_count
            )
        
        # STEP 3: Rebuild system prompt
        self._build_system_prompt()
        
        # STEP 4: Reset to IDLE state (direct assignment, no transition validation)
        self.state = PipelineState.IDLE
        
        # STEP 5: Report readiness
        current_version = self.canon_manager.version_store.get_current_version()
        
        log_info(
            f"/reset complete: PIPELINE_FLOW_VERSION={current_version}, "
            f"state=IDLE, ready for new work"
        )
        
        return ResetResult(
            success=True,
            canon_version=str(current_version),
            in_flight_discarded=in_flight_count,
            warnings=self._generate_reset_warnings(in_flight_count)
        )
    
    def _clear_ephemeral_state(self) -> ClearedState:
        """Clear all ephemeral Orchestrator state."""
        cleared = ClearedState(
            phase=self.state,
            artifact_count=len(self.artifacts)
        )
        
        self.current_epic = None
        self.artifacts.clear()
        self.phase_history.clear()
        
        return cleared
    
    def _generate_reset_warnings(self, in_flight_count: int) -> list:
        """Generate warnings for reset operation."""
        warnings = []
        
        if in_flight_count > 0:
            warnings.append(
                f"{in_flight_count} in-flight pipeline(s) were discarded. "
                f"Work was not committed."
            )
        
        return warnings
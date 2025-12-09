"""Reset service: orchestrator reset coordination."""

from typing import List
from workforce.orchestrator import Orchestrator
from workforce.utils.logging import log_info, log_warning
from app.orchestrator_api.schemas.responses import ResetResponse
from app.orchestrator_api.persistence.repositories import PipelineRepository
from config import settings


class ResetService:
    """
    Service for coordinating reset operations.
    
    Reset behavior (MVP):
    - Reloads canon from disk
    - Clears Orchestrator's in-memory cache (if any)
    - Does NOT delete persisted pipeline/artifact data
    - Counts in-flight pipelines and warns
    - Respects guardrails (blocks in critical phases if configured) - Moderate Issue #5 fix
    """
    
    # Critical phases that block reset (unless override enabled)
    CRITICAL_PHASES = ["qa_phase", "commit_phase"]
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.pipeline_repo = PipelineRepository()
    
    def perform_reset(self) -> ResetResponse:
        """
        Perform orchestrator reset with guardrail enforcement.
        
        Note: This preserves all persisted data (pipelines, artifacts, transitions).
        Only clears ephemeral cache and reloads canon.
        
        Moderate Issue #5 fix: Enforces critical phase guardrails.
        """
        log_info("Reset requested")
        
        # Check critical phase guardrails (Moderate Issue #5 fix)
        if not settings.ALLOW_RESET_IN_CRITICAL_PHASES:
            # Count pipelines in critical phases
            critical_pipelines = []
            for phase in self.CRITICAL_PHASES:
                pipelines_in_phase = self.pipeline_repo.list_by_state(phase)
                critical_pipelines.extend(pipelines_in_phase)
            
            if critical_pipelines:
                log_warning(
                    f"Reset blocked: {len(critical_pipelines)} pipeline(s) in critical phases "
                    f"({', '.join(self.CRITICAL_PHASES)})"
                )
                return ResetResponse(
                    success=False,
                    reason=f"Reset blocked: {len(critical_pipelines)} pipeline(s) in critical phases "
                           f"({', '.join(self.CRITICAL_PHASES)}). "
                           f"Set ALLOW_RESET_IN_CRITICAL_PHASES=true to override.",
                    in_flight_discarded=0,
                    warnings=[]
                )
        
        # Count all in-flight pipelines (not complete, not failed)
        in_flight_states = ["idle", "pm_phase", "arch_phase", "ba_phase", "dev_phase", "qa_phase", "commit_phase"]
        in_flight_count = 0
        for state in in_flight_states:
            in_flight_count += len(self.pipeline_repo.list_by_state(state))
        
        # Call Orchestrator reset (reloads canon, clears cache)
        result = self.orchestrator.handle_reset()
        
        # Build warnings if in-flight pipelines exist
        warnings = []
        if in_flight_count > 0:
            warnings.append(
                f"{in_flight_count} in-flight pipeline(s) detected. "
                "Reset clears cache but preserves all persisted data."
            )
        
        if result.success:
            log_info(f"Reset successful. Canon version: {result.canon_version}. In-flight: {in_flight_count}")
        else:
            log_warning(f"Reset blocked: {result.reason}")
        
        return ResetResponse(
            success=result.success,
            canon_version=result.canon_version if result.success else None,
            reason=result.reason if not result.success else None,
            in_flight_discarded=0,  # MVP: data not discarded, just counted
            warnings=warnings
        )
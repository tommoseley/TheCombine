"""Outcome Recorder for Document Interaction Workflows (ADR-037, ADR-039).

Records dual outcomes (governance + execution) for audit compliance.

INVARIANTS (WS-ADR-025 Phase 4):
- Gate outcome (governance vocabulary) recorded to governance_outcomes table
- Terminal outcome (execution vocabulary) recorded atomically with gate outcome
- Mapping verified against workflow plan's outcome_mapping
- Full audit trail per ADR-037 requirements
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import DocumentWorkflowState
from app.domain.workflow.outcome_mapper import OutcomeMapper, OutcomeMapperError
from app.domain.workflow.plan_models import WorkflowPlan

logger = logging.getLogger(__name__)


class OutcomeRecorderError(Exception):
    """Error during outcome recording."""
    pass


class OutcomeRecorder:
    """Records dual outcomes for governance audit via ORM.

    Per ADR-037:
    - Records the full available_options[] snapshot at decision time
    - Records the chosen option_id
    - Records selection method (auto, recommended, user_confirmed)
    - Records retry counts and circuit breaker status

    Per ADR-039:
    - Maps gate outcome to terminal outcome using plan's outcome_mapping
    - Records both outcomes atomically
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def record_outcome(
        self,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
        gate_type: str = "intake_gate",
        options_offered: Optional[List[Dict[str, Any]]] = None,
        option_selected: Optional[str] = None,
        selection_method: Optional[str] = None,
        recorded_by: Optional[str] = None,
    ) -> str:
        """Record governance and execution outcomes via ORM."""
        # Lazy import to avoid circular dependency
        from app.api.models.governance_outcome import GovernanceOutcome
        
        # Validate gate outcome exists
        if not state.gate_outcome:
            raise OutcomeRecorderError(
                "Cannot record outcome: state has no gate_outcome"
            )

        # Validate terminal outcome exists
        if not state.terminal_outcome:
            raise OutcomeRecorderError(
                "Cannot record outcome: state has no terminal_outcome"
            )

        # Verify outcome mapping is consistent
        mapper = OutcomeMapper.from_plan(plan)
        try:
            expected_terminal = mapper.map(state.gate_outcome)
            if expected_terminal != state.terminal_outcome:
                logger.warning(
                    f"Terminal outcome mismatch: expected {expected_terminal} "
                    f"for gate outcome {state.gate_outcome}, "
                    f"got {state.terminal_outcome}"
                )
        except OutcomeMapperError as e:
            logger.warning(f"Outcome mapping validation failed: {e}")

        # Determine ready_for based on gate outcome
        ready_for = None
        if state.gate_outcome == "qualified":
            ready_for = "pm_discovery"

        # Get retry count for current node
        retry_count = state.get_retry_count(state.current_node_id)

        # Check if circuit breaker was active
        circuit_breaker_active = state.escalation_active

        # Create via ORM
        outcome = GovernanceOutcome(
            execution_id=state.execution_id,
            document_id=state.project_id,
            document_type=state.document_type,
            workflow_id=state.workflow_id,
            thread_id=state.thread_id,
            gate_type=gate_type,
            gate_outcome=state.gate_outcome,
            terminal_outcome=state.terminal_outcome,
            ready_for=ready_for,
            routing_rationale=self._build_routing_rationale(state),
            options_offered=options_offered,
            option_selected=option_selected,
            selection_method=selection_method,
            retry_count=retry_count,
            circuit_breaker_active=circuit_breaker_active,
            recorded_by=recorded_by or "workflow_engine",
        )

        self._db.add(outcome)
        await self._db.commit()
        await self._db.refresh(outcome)

        outcome_id = str(outcome.id)

        logger.info(
            f"Recorded governance outcome {outcome_id}: "
            f"gate={state.gate_outcome}, terminal={state.terminal_outcome}, "
            f"ready_for={ready_for}"
        )

        return outcome_id

    async def get_outcome_by_execution(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get governance outcome for an execution via ORM."""
        from app.api.models.governance_outcome import GovernanceOutcome
        
        result = await self._db.execute(
            select(GovernanceOutcome)
            .where(GovernanceOutcome.execution_id == execution_id)
            .order_by(GovernanceOutcome.recorded_at.desc())
            .limit(1)
        )

        outcome = result.scalar_one_or_none()
        if not outcome:
            return None

        return outcome.to_dict()

    async def list_outcomes_by_document(
        self,
        document_type: str,
        project_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List governance outcomes for a document via ORM."""
        from app.api.models.governance_outcome import GovernanceOutcome
        
        result = await self._db.execute(
            select(GovernanceOutcome)
            .where(
                and_(
                    GovernanceOutcome.document_type == document_type,
                    GovernanceOutcome.document_id == project_id
                )
            )
            .order_by(GovernanceOutcome.recorded_at.desc())
            .limit(limit)
        )

        outcomes = result.scalars().all()
        return [
            {
                "id": str(o.id),
                "execution_id": o.execution_id,
                "gate_type": o.gate_type,
                "gate_outcome": o.gate_outcome,
                "terminal_outcome": o.terminal_outcome,
                "ready_for": o.ready_for,
                "recorded_at": o.recorded_at.isoformat() if o.recorded_at else None,
            }
            for o in outcomes
        ]

    def _build_routing_rationale(
        self,
        state: DocumentWorkflowState,
    ) -> str:
        """Build routing rationale from state."""
        parts = []

        if state.gate_outcome == "qualified":
            parts.append("Project request qualified for PM Discovery.")
        elif state.gate_outcome == "not_ready":
            parts.append("Project request not ready - additional information needed.")
        elif state.gate_outcome == "out_of_scope":
            parts.append("Project request determined to be out of scope.")
        elif state.gate_outcome == "redirect":
            parts.append("Project request redirected to different engagement type.")

        if state.escalation_active:
            parts.append("Circuit breaker was active.")

        retry_count = state.get_retry_count(state.current_node_id)
        if retry_count > 0:
            parts.append(f"Retry count: {retry_count}.")

        return " ".join(parts)
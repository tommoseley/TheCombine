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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import DocumentWorkflowState
from app.domain.workflow.outcome_mapper import OutcomeMapper, OutcomeMapperError
from app.domain.workflow.plan_models import WorkflowPlan

logger = logging.getLogger(__name__)


class OutcomeRecorderError(Exception):
    """Error during outcome recording."""
    pass


class OutcomeRecorder:
    """Records dual outcomes for governance audit.

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
        """Initialize outcome recorder.

        Args:
            db: Database session
        """
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
        """Record governance and execution outcomes.

        Args:
            state: The workflow state with outcomes
            plan: The workflow plan for outcome mapping validation
            gate_type: Type of gate (intake_gate, qa_gate, etc.)
            options_offered: Snapshot of available_options[] at decision time
            option_selected: The option_id that was selected
            selection_method: How selection was made (auto, recommended, user_confirmed)
            recorded_by: Who/what recorded this outcome

        Returns:
            The ID of the recorded governance outcome

        Raises:
            OutcomeRecorderError: If outcome is invalid or recording fails
        """
        # Validate gate outcome exists
        if not state.gate_outcome:
            raise OutcomeRecorderError(
                f"Cannot record outcome: state has no gate_outcome"
            )

        # Validate terminal outcome exists
        if not state.terminal_outcome:
            raise OutcomeRecorderError(
                f"Cannot record outcome: state has no terminal_outcome"
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

        # Insert governance outcome record
        result = await self._db.execute(
            text("""
                INSERT INTO governance_outcomes (
                    execution_id,
                    document_id,
                    document_type,
                    workflow_id,
                    thread_id,
                    gate_type,
                    gate_outcome,
                    terminal_outcome,
                    ready_for,
                    routing_rationale,
                    options_offered,
                    option_selected,
                    selection_method,
                    retry_count,
                    circuit_breaker_active,
                    recorded_by
                ) VALUES (
                    :execution_id,
                    :document_id,
                    :document_type,
                    :workflow_id,
                    :thread_id,
                    :gate_type,
                    :gate_outcome,
                    :terminal_outcome,
                    :ready_for,
                    :routing_rationale,
                    :options_offered,
                    :option_selected,
                    :selection_method,
                    :retry_count,
                    :circuit_breaker_active,
                    :recorded_by
                )
                RETURNING id
            """),
            {
                "execution_id": state.execution_id,
                "document_id": state.document_id,
                "document_type": state.document_type,
                "workflow_id": state.workflow_id,
                "thread_id": state.thread_id,
                "gate_type": gate_type,
                "gate_outcome": state.gate_outcome,
                "terminal_outcome": state.terminal_outcome,
                "ready_for": ready_for,
                "routing_rationale": self._build_routing_rationale(state),
                "options_offered": options_offered,
                "option_selected": option_selected,
                "selection_method": selection_method,
                "retry_count": retry_count,
                "circuit_breaker_active": circuit_breaker_active,
                "recorded_by": recorded_by or "workflow_engine",
            },
        )

        row = result.fetchone()
        outcome_id = str(row[0])

        await self._db.commit()

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
        """Get governance outcome for an execution.

        Args:
            execution_id: The workflow execution ID

        Returns:
            Outcome record dict or None if not found
        """
        result = await self._db.execute(
            text("""
                SELECT
                    id,
                    execution_id,
                    document_id,
                    document_type,
                    workflow_id,
                    thread_id,
                    gate_type,
                    gate_outcome,
                    terminal_outcome,
                    ready_for,
                    routing_rationale,
                    options_offered,
                    option_selected,
                    selection_method,
                    retry_count,
                    circuit_breaker_active,
                    recorded_at,
                    recorded_by
                FROM governance_outcomes
                WHERE execution_id = :execution_id
                ORDER BY recorded_at DESC
                LIMIT 1
            """),
            {"execution_id": execution_id},
        )

        row = result.fetchone()
        if not row:
            return None

        return {
            "id": str(row[0]),
            "execution_id": row[1],
            "document_id": row[2],
            "document_type": row[3],
            "workflow_id": row[4],
            "thread_id": row[5],
            "gate_type": row[6],
            "gate_outcome": row[7],
            "terminal_outcome": row[8],
            "ready_for": row[9],
            "routing_rationale": row[10],
            "options_offered": row[11],
            "option_selected": row[12],
            "selection_method": row[13],
            "retry_count": row[14],
            "circuit_breaker_active": row[15],
            "recorded_at": row[16].isoformat() if row[16] else None,
            "recorded_by": row[17],
        }

    async def list_outcomes_by_document(
        self,
        document_type: str,
        document_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List governance outcomes for a document.

        Args:
            document_type: Type of document
            document_id: Document ID
            limit: Maximum results to return

        Returns:
            List of outcome records
        """
        result = await self._db.execute(
            text("""
                SELECT
                    id,
                    execution_id,
                    gate_type,
                    gate_outcome,
                    terminal_outcome,
                    ready_for,
                    recorded_at
                FROM governance_outcomes
                WHERE document_type = :document_type
                  AND document_id = :document_id
                ORDER BY recorded_at DESC
                LIMIT :limit
            """),
            {
                "document_type": document_type,
                "document_id": document_id,
                "limit": limit,
            },
        )

        return [
            {
                "id": str(row[0]),
                "execution_id": row[1],
                "gate_type": row[2],
                "gate_outcome": row[3],
                "terminal_outcome": row[4],
                "ready_for": row[5],
                "recorded_at": row[6].isoformat() if row[6] else None,
            }
            for row in result.fetchall()
        ]

    def _build_routing_rationale(
        self,
        state: DocumentWorkflowState,
    ) -> str:
        """Build routing rationale from state.

        Args:
            state: The workflow state

        Returns:
            Human-readable routing rationale
        """
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

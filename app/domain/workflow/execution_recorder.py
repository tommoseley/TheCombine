"""Audit trail and thread lifecycle recording.

Extracted from PlanExecutor (WS-CRAP decomposition).
Handles conversation persistence, thread status sync,
and governance outcome recording.
"""

import logging
from typing import Optional

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
)
from app.domain.workflow.plan_models import Node, WorkflowPlan
from app.domain.workflow.nodes.base import DocumentWorkflowContext, NodeResult
from app.domain.workflow.thread_manager import ThreadManager
from app.domain.workflow.outcome_recorder import OutcomeRecorder

logger = logging.getLogger(__name__)


async def persist_conversation(
    result: NodeResult,
    node: Node,
    state: DocumentWorkflowState,
    context: DocumentWorkflowContext,
    thread_manager: Optional[ThreadManager],
) -> None:
    """Persist conversation turns to thread.

    Records user input and assistant responses to the thread ledger
    for conversation continuity.

    Args:
        result: The node execution result
        node: The executed node
        state: Current execution state
        context: Execution context with user input
        thread_manager: Thread manager instance (may be None)
    """
    if not state.thread_id or not thread_manager:
        return

    try:
        # Record user input if present
        user_input = context.extra.get("user_input")
        if user_input:
            # Convert dict to JSON string for thread recording
            import json
            content = json.dumps(user_input, indent=2) if isinstance(user_input, dict) else user_input
            await thread_manager.record_conversation_turn(
                thread_id=state.thread_id,
                role="user",
                content=content,
                node_id=node.node_id,
            )

        # Record assistant response if produced
        if result.produced_document:
            # For concierge nodes, the response might be in the document
            response_content = result.produced_document.get("response")
            if response_content:
                await thread_manager.record_conversation_turn(
                    thread_id=state.thread_id,
                    role="assistant",
                    content=response_content,
                    node_id=node.node_id,
                )

        # Record user prompt for paused states
        if result.requires_user_input and result.user_prompt:
            await thread_manager.record_conversation_turn(
                thread_id=state.thread_id,
                role="assistant",
                content=result.user_prompt,
                node_id=node.node_id,
            )

    except Exception as e:
        logger.warning(f"Failed to persist conversation to thread: {e}")


async def sync_thread_status(
    state: DocumentWorkflowState,
    thread_manager: Optional[ThreadManager],
) -> None:
    """Sync thread status with workflow status.

    Updates thread status to match workflow completion/failure.

    Args:
        state: Current execution state
        thread_manager: Thread manager instance (may be None)
    """
    if not state.thread_id or not thread_manager:
        return

    try:
        if state.status == DocumentWorkflowStatus.RUNNING:
            await thread_manager.start_thread(state.thread_id)
        elif state.status == DocumentWorkflowStatus.COMPLETED:
            await thread_manager.complete_thread(state.thread_id)
        elif state.status == DocumentWorkflowStatus.FAILED:
            await thread_manager.fail_thread(state.thread_id)
    except Exception as e:
        logger.warning(f"Failed to sync thread status: {e}")


async def record_governance_outcome(
    state: DocumentWorkflowState,
    plan: WorkflowPlan,
    result: NodeResult,
    outcome_recorder: Optional[OutcomeRecorder],
) -> None:
    """Record governance outcome for audit (ADR-037).

    Records both gate outcome (governance vocabulary) and terminal outcome
    (execution vocabulary) to the governance_outcomes table.

    Args:
        state: The completed workflow state
        plan: The workflow plan
        result: The final node result
        outcome_recorder: Outcome recorder instance (may be None)
    """
    if not outcome_recorder:
        return

    if not state.gate_outcome or not state.terminal_outcome:
        logger.debug("Skipping outcome recording: no outcomes set")
        return

    try:
        # Extract options offered from result metadata if available
        options_offered = result.metadata.get("options_offered")
        option_selected = result.metadata.get("option_selected")
        selection_method = result.metadata.get("selection_method")

        await outcome_recorder.record_outcome(
            state=state,
            plan=plan,
            gate_type="intake_gate",  # Default for concierge intake
            options_offered=options_offered,
            option_selected=option_selected,
            selection_method=selection_method,
            recorded_by="workflow_engine",
        )
    except Exception as e:
        logger.warning(f"Failed to record governance outcome: {e}")

"""QA retry tracking and feedback circuit handling.

Extracted from PlanExecutor (WS-CRAP decomposition).
Handles QA feedback circuits, retry counting, and generating node identification.
"""

import logging
from typing import Any, Dict, Optional

from app.domain.workflow.document_workflow_state import DocumentWorkflowState
from app.domain.workflow.plan_models import Node, NodeType, WorkflowPlan
from app.domain.workflow.nodes.base import NodeResult

logger = logging.getLogger(__name__)


def prepare_qa_retry_tracking(
    result: NodeResult,
    current_node: Node,
    state: DocumentWorkflowState,
    plan: WorkflowPlan,
) -> None:
    """Set generating_node_id on state if QA failed (needed by EdgeRouter).

    Note: GateNodeExecutor remaps "failed" -> "fail".  Accept both forms.
    """
    if not current_node.is_qa_gate() or result.outcome not in ("failed", "fail"):
        return
    generating_node_id = find_generating_node(state, plan)
    if generating_node_id:
        state.generating_node_id = generating_node_id
        current_retries = state.get_retry_count(generating_node_id)
        logger.info(
            f"Circuit breaker check: {generating_node_id} has {current_retries} retries "
            f"(threshold: 2)"
        )


def handle_qa_retry_feedback(
    result: NodeResult,
    current_node: Node,
    state: DocumentWorkflowState,
) -> None:
    """Handle QA retry counting and feedback storage/clearing.

    Note: GateNodeExecutor remaps outcomes before the plan executor sees
    them: "failed" -> "fail", "success" -> "pass".  We accept both forms
    so this works regardless of whether the QA runs as a bare QA node or
    wrapped in a gate.
    """
    if (
        current_node.is_qa_gate()
        and result.outcome in ("failed", "fail")
        and state.generating_node_id
    ):
        retry_count = state.increment_retry(state.generating_node_id)
        logger.info(
            f"QA failed, incremented retry for {state.generating_node_id} "
            f"to {retry_count}"
        )

        qa_feedback = extract_qa_feedback(result)
        if qa_feedback:
            state.update_context_state({"qa_feedback": qa_feedback})
            logger.info(
                f"Stored QA feedback for remediation: "
                f"{len(qa_feedback.get('issues', []))} issues"
            )

    elif current_node.is_qa_gate() and result.outcome in ("success", "pass"):
        if state.context_state.get("qa_feedback"):
            state.context_state.pop("qa_feedback", None)
            logger.debug("Cleared QA feedback after successful validation")


def extract_qa_feedback(result: NodeResult) -> Optional[Dict[str, Any]]:
    """Extract actionable QA feedback from failed result.

    Delegates to result_handling.extract_qa_feedback pure function.

    Args:
        result: The failed QA NodeResult

    Returns:
        Dict with issues, summary, and remediation hints, or None
    """
    from app.domain.workflow.result_handling import extract_qa_feedback as _extract

    return _extract(result.metadata)


def find_generating_node(
    state: DocumentWorkflowState,
    plan: WorkflowPlan,
) -> Optional[str]:
    """Find the generating node for QA retry tracking.

    Returns a STABLE identifier for the QA loop to track retries correctly.

    FIX: Previously returned the "last task node" which changed from
    "generation" to "remediation" after each retry, resetting the counter.
    Now returns the FIRST task node that produces the document being QA'd,
    giving a stable ID for the entire QA loop.

    Args:
        state: Current execution state
        plan: Workflow plan

    Returns:
        Node ID of generating node or None
    """
    # Find the FIRST task node that produces content (stable for retry tracking)
    # This ensures retries are counted correctly across generation -> remediation cycles
    for execution in state.node_history:  # Forward order, not reversed
        node = plan.get_node(execution.node_id)
        if node and node.type == NodeType.TASK:
            # Check if this node produces something (is a generating node)
            if hasattr(node, 'produces') and node.produces:
                return execution.node_id

    # Fallback: return first task node
    for execution in state.node_history:
        node = plan.get_node(execution.node_id)
        if node and node.type == NodeType.TASK:
            return execution.node_id
    return None

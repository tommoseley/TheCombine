"""Read-only execution query functions extracted from PlanExecutor.

Provides get_execution_status and list_executions.
Extracted in second-pass decomposition of plan_executor.py.
"""

import logging
from typing import Any, Dict, List, Optional

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowStatus,
)

logger = logging.getLogger(__name__)


async def get_execution_status(
    persistence: Any,
    execution_id: str,
) -> Optional[Dict[str, Any]]:
    """Get current execution status.

    Args:
        persistence: State persistence backend
        execution_id: The execution ID

    Returns:
        Status dict or None if not found
    """
    state = await persistence.load(execution_id)
    if not state:
        return None

    return {
        "execution_id": state.execution_id,
        "project_id": state.project_id,
        "document_type": state.document_type,
        "workflow_id": state.workflow_id,
        "status": state.status.value,
        "current_node_id": state.current_node_id,
        "terminal_outcome": state.terminal_outcome,
        "gate_outcome": state.gate_outcome,
        "pending_user_input": state.pending_user_input,
        "pending_user_input_rendered": state.pending_user_input_rendered,
        "pending_choices": state.pending_choices,
        "pending_user_input_payload": state.pending_user_input_payload,
        "pending_user_input_schema_ref": state.pending_user_input_schema_ref,
        "escalation_active": state.escalation_active,
        "escalation_options": state.escalation_options,
        "step_count": len(state.node_history),
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "produced_documents": {k: v for k, v in state.context_state.items() if k.startswith("document_")},
    }


async def list_executions(
    persistence: Any,
    status_filter: Optional[List[str]] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List workflow executions.

    Args:
        persistence: State persistence backend
        status_filter: Optional list of status values to filter by
                      (e.g., ["running", "paused"])
        limit: Maximum number of executions to return

    Returns:
        List of execution status dicts, sorted by most recent first
    """
    # Convert string statuses to enum if provided
    enum_filter = None
    if status_filter:
        enum_filter = [DocumentWorkflowStatus(s) for s in status_filter]

    states = await persistence.list_executions(
        status_filter=enum_filter,
        limit=limit,
    )

    return [
        {
            "execution_id": state.execution_id,
            "project_id": state.project_id,
            "document_type": state.document_type,
            "workflow_id": state.workflow_id,
            "status": state.status.value,
            "current_node_id": state.current_node_id,
            "terminal_outcome": state.terminal_outcome,
            "pending_user_input": state.pending_user_input,
            "step_count": len(state.node_history),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }
        for state in states
    ]

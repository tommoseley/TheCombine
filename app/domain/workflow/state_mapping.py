"""Pure data transformation for converting persistence rows to DocumentWorkflowState.

Extracted from pg_state_persistence._row_to_state() for testability (WS-CRAP-007).
No I/O, no DB, no logging.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)


def parse_json_field(value: Any, default: Any) -> Any:
    """Parse a JSON field that may already be deserialized or may be a string.

    Args:
        value: The raw field value (dict/list or JSON string or None)
        default: Default value if field is None or empty

    Returns:
        Parsed value or default
    """
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value) if value else default


def build_node_history(execution_log: List[Dict[str, Any]]) -> List[NodeExecution]:
    """Build NodeExecution list from execution log entries.

    Args:
        execution_log: List of dicts with node_id, outcome, timestamp, metadata

    Returns:
        List of NodeExecution dataclass instances
    """
    return [
        NodeExecution(
            node_id=entry["node_id"],
            outcome=entry["outcome"],
            timestamp=datetime.fromisoformat(entry["timestamp"]),
            metadata=entry.get("metadata", {}),
        )
        for entry in execution_log
    ]


def derive_timestamps(
    execution_log: List[Dict[str, Any]],
) -> tuple:
    """Derive created_at and updated_at from execution log.

    Args:
        execution_log: List of execution log entries

    Returns:
        Tuple of (created_at, updated_at) datetimes
    """
    if execution_log:
        created_at = datetime.fromisoformat(execution_log[0]["timestamp"])
        updated_at = datetime.fromisoformat(execution_log[-1]["timestamp"])
    else:
        now = datetime.now(timezone.utc)
        created_at = now
        updated_at = now
    return created_at, updated_at


def row_dict_to_state(row_data: Dict[str, Any]) -> DocumentWorkflowState:
    """Convert a dict of row fields to DocumentWorkflowState.

    This is the pure-logic core of _row_to_state. It receives already-extracted
    field values (no ORM object dependency).

    Args:
        row_data: Dict with keys matching ORM column names:
            execution_id, document_id, document_type, workflow_id,
            user_id, current_node_id, status, execution_log,
            retry_counts, gate_outcome, terminal_outcome, thread_id,
            context_state, pending_user_input, pending_user_input_rendered,
            pending_choices, pending_user_input_payload,
            pending_user_input_schema_ref

    Returns:
        DocumentWorkflowState instance
    """
    # Parse JSON fields
    execution_log = parse_json_field(
        row_data.get("execution_log"), []
    )
    retry_counts = parse_json_field(
        row_data.get("retry_counts"), {}
    )
    pending_choices = parse_json_field(
        row_data.get("pending_choices"), None
    )
    context_state = parse_json_field(
        row_data.get("context_state"), {}
    )

    # Build node history
    node_history = build_node_history(execution_log)

    # Derive timestamps
    created_at, updated_at = derive_timestamps(execution_log)

    # Parse status
    raw_status = row_data.get("status")
    status = (
        DocumentWorkflowStatus(raw_status)
        if raw_status
        else DocumentWorkflowStatus.RUNNING
    )

    return DocumentWorkflowState(
        execution_id=row_data.get("execution_id"),
        project_id=row_data.get("document_id") or "unknown",
        document_type=row_data.get("document_type") or "unknown",
        workflow_id=row_data.get("workflow_id") or "unknown",
        user_id=str(row_data["user_id"]) if row_data.get("user_id") else None,
        current_node_id=row_data.get("current_node_id"),
        status=status,
        node_history=node_history,
        retry_counts=retry_counts,
        gate_outcome=row_data.get("gate_outcome"),
        terminal_outcome=row_data.get("terminal_outcome"),
        thread_id=row_data.get("thread_id"),
        context_state=context_state,
        pending_user_input=row_data.get("pending_user_input") or False,
        pending_user_input_rendered=row_data.get("pending_user_input_rendered"),
        pending_choices=pending_choices,
        pending_user_input_payload=row_data.get("pending_user_input_payload"),
        pending_user_input_schema_ref=row_data.get("pending_user_input_schema_ref"),
        created_at=created_at,
        updated_at=updated_at,
    )

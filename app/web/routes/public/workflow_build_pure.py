"""
Pure data transformation functions extracted from workflow_build_routes.py.

No I/O, no DB, no logging. All functions are deterministic and testable in isolation.

WS-CRAP-006: Testability refactoring for CRAP score reduction.
"""

from typing import Any, Dict


# =============================================================================
# PGC Form Parsing
# =============================================================================

def parse_pgc_form_data(raw_items: list[tuple[str, str]]) -> Dict[str, Any]:
    """Parse raw form key-value pairs into a structured answers dict.

    Handles:
    - answers[QUESTION_ID] = "value" (single value)
    - answers[QUESTION_ID][] = ["a", "b"] (multi-select)
    - answers[QUESTION_ID] = "true"/"false" (boolean conversion)

    Args:
        raw_items: List of (key, value) tuples from form.multi_items().

    Returns:
        Dict mapping question_id -> value (str, bool, or list[str]).
    """
    answers: Dict[str, Any] = {}
    multi_values: Dict[str, list[str]] = {}

    for key, value in raw_items:
        if not key.startswith("answers["):
            continue

        if key.endswith("[]"):
            # Multi-select: answers[X][] -> X
            q_id = key[8:-3]
            if q_id not in multi_values:
                multi_values[q_id] = []
            multi_values[q_id].append(value)
        else:
            # Single value: answers[X] -> X
            q_id = key[8:-1]
            if value == "true":
                answers[q_id] = True
            elif value == "false":
                answers[q_id] = False
            else:
                answers[q_id] = value

    answers.update(multi_values)
    return answers


# =============================================================================
# Workflow State Classification
# =============================================================================

# Document type display config
DOC_TYPE_DISPLAY = {
    "project_discovery": {
        "name": "Project Discovery",
        "icon": "compass",
    },
}

DEFAULT_DOC_TYPE_DISPLAY = {
    "name": None,  # Will be filled with doc_type_id
    "icon": "file-text",
}

# Node-based progress estimation
NODE_PROGRESS = {
    "pgc": 10,
    "generation": 50,
    "qa": 80,
    "persist": 95,
    "end": 100,
}

NODE_STATUS_MESSAGES = {
    "pgc": "Preparing questions...",
    "generation": "Generating document...",
    "qa": "Validating quality...",
    "persist": "Saving document...",
    "end": "Completing...",
}


def estimate_progress(current_node_id: str) -> int:
    """Estimate progress percentage based on current workflow node.

    Returns a percentage (0-100).
    """
    return NODE_PROGRESS.get(current_node_id, 30)


def get_status_message(current_node_id: str) -> str:
    """Get human-readable status message for a workflow node."""
    return NODE_STATUS_MESSAGES.get(current_node_id, "Processing...")


def get_doc_type_display(doc_type_id: str) -> dict:
    """Get display name and icon for a document type.

    Returns dict with 'name' and 'icon' keys.
    """
    config = DOC_TYPE_DISPLAY.get(doc_type_id)
    if config:
        return dict(config)
    return {"name": doc_type_id, "icon": "file-text"}


def classify_workflow_state(
    status_value: str,
    pending_user_input_payload: dict | None,
    terminal_outcome: str | None,
    current_node_id: str | None,
) -> dict:
    """Classify workflow state into template variables.

    Given raw workflow state fields, returns a dict with:
    - workflow_state: one of 'complete', 'failed', 'paused_pgc', 'stale_paused', 'running'
    - error_message: present only for 'failed' or 'stale_paused'
    - questions: present only for 'paused_pgc'
    - pending_user_input_payload: present only for 'paused_pgc'
    - progress: present only for 'running'
    - status_message: present only for 'running'

    Args:
        status_value: The DocumentWorkflowStatus value string.
        pending_user_input_payload: Payload dict from workflow state, or None.
        terminal_outcome: Terminal outcome string, or None.
        current_node_id: Current node ID string, or None.

    Returns:
        Dict of template variables for the workflow state.
    """
    if status_value == "completed":
        return {"workflow_state": "complete"}

    if status_value == "failed":
        return {
            "workflow_state": "failed",
            "error_message": terminal_outcome or "Unknown error",
        }

    if status_value == "paused":
        if pending_user_input_payload:
            questions = pending_user_input_payload.get("questions", [])
            if questions:
                return {
                    "workflow_state": "paused_pgc",
                    "questions": questions,
                    "pending_user_input_payload": pending_user_input_payload,
                }

        # Paused but no payload/questions - stale execution
        return {
            "workflow_state": "stale_paused",
            "error_message": "Previous workflow session expired. Please try again.",
        }

    # Running state (PENDING or RUNNING or any other)
    return {
        "workflow_state": "running",
        "progress": estimate_progress(current_node_id or ""),
        "status_message": get_status_message(current_node_id or ""),
    }

"""
Pure data transformation functions extracted from intake_workflow_routes.py.

No I/O, no DB, no logging. All functions are deterministic and testable in isolation.

WS-CRAP-006: Testability refactoring for CRAP score reduction.
"""

from typing import Optional


# =============================================================================
# Outcome Display Mapping
# =============================================================================

OUTCOME_DISPLAY = {
    "qualified": {
        "title": "Project Qualified",
        "description": "Your project has been qualified and is ready for PM Discovery.",
        "color": "green",
        "next_action": "View Discovery Document",
    },
    "not_ready": {
        "title": "Not Ready",
        "description": "Additional information is needed before proceeding.",
        "color": "yellow",
        "next_action": "Start Over",
    },
    "out_of_scope": {
        "title": "Out of Scope",
        "description": "This request is outside the scope of The Combine.",
        "color": "gray",
        "next_action": None,
    },
    "redirect": {
        "title": "Redirected",
        "description": "This request has been redirected to a different engagement type.",
        "color": "blue",
        "next_action": None,
    },
    "blocked": {
        "title": "Blocked",
        "description": "The workflow could not complete due to validation issues.",
        "color": "yellow",
        "next_action": "Start Over",
    },
}

DEFAULT_OUTCOME = {
    "title": "Complete",
    "description": "The intake workflow has completed.",
    "color": "gray",
    "next_action": None,
}


def get_outcome_display(outcome: Optional[str]) -> dict:
    """Look up outcome display info by outcome key.

    Returns a dict with keys: title, description, color, next_action.
    Falls back to DEFAULT_OUTCOME for unknown outcomes.
    """
    return OUTCOME_DISPLAY.get(outcome, DEFAULT_OUTCOME)


# =============================================================================
# Completion Outcome Display (project-aware)
# =============================================================================

COMPLETION_OUTCOME_DISPLAY = {
    "qualified": {
        "title_with_project": "Project Created",
        "title_without_project": "Project Qualified",
        "description_with_project": "Project {project_id} is ready for PM Discovery.",
        "description_without_project": "Your project has been qualified and is ready for PM Discovery.",
        "color": "green",
        "next_action_with_project": "View Project",
        "next_action_without_project": "View Discovery Document",
    },
    "not_ready": {
        "title": "Not Ready",
        "description": "Additional information is needed before proceeding.",
        "color": "yellow",
        "next_action": "Start Over",
    },
    "out_of_scope": {
        "title": "Out of Scope",
        "description": "This request is outside the scope of The Combine.",
        "color": "gray",
        "next_action": None,
    },
    "redirect": {
        "title": "Redirected",
        "description": "This request has been redirected to a different engagement type.",
        "color": "blue",
        "next_action": None,
    },
}


def get_completion_outcome_display(
    gate_outcome: Optional[str],
    has_project: bool = False,
    project_id: Optional[str] = None,
) -> dict:
    """Get completion outcome display info, aware of whether a project was created.

    For 'qualified' outcome, the display changes based on whether project creation
    succeeded. For all other outcomes, it's static.

    Returns dict with keys: title, description, color, next_action.
    """
    entry = COMPLETION_OUTCOME_DISPLAY.get(gate_outcome)
    if entry is None:
        return dict(DEFAULT_OUTCOME)

    # Non-qualified outcomes have static fields
    if gate_outcome != "qualified":
        return {
            "title": entry["title"],
            "description": entry["description"],
            "color": entry["color"],
            "next_action": entry["next_action"],
        }

    # Qualified outcome depends on project existence
    if has_project:
        return {
            "title": entry["title_with_project"],
            "description": entry["description_with_project"].format(
                project_id=project_id or "unknown"
            ),
            "color": entry["color"],
            "next_action": entry["next_action_with_project"],
        }
    else:
        return {
            "title": entry["title_without_project"],
            "description": entry["description_without_project"],
            "color": entry["color"],
            "next_action": entry["next_action_without_project"],
        }


# =============================================================================
# Message Extraction from Node History
# =============================================================================

def extract_messages_from_node_history(
    node_history: list,
    pending_user_input_rendered: Optional[str],
) -> list[dict]:
    """Extract conversation messages from workflow node history.

    Each node execution may have user_input and/or response metadata.
    The last response is skipped if the workflow is paused (pending_user_input_rendered
    is truthy), because it's shown separately via the pending prompt UI.

    Args:
        node_history: List of node execution objects with .metadata dict.
        pending_user_input_rendered: Truthy if workflow is paused awaiting user input.

    Returns:
        List of message dicts with 'role' ('user'/'assistant') and 'content'.
    """
    messages = []

    for i, execution in enumerate(node_history):
        metadata = execution.metadata if hasattr(execution, "metadata") else execution.get("metadata", {})
        if metadata.get("user_input"):
            messages.append({
                "role": "user",
                "content": metadata["user_input"],
            })
        response = metadata.get("response") or metadata.get("user_prompt")
        if response:
            is_last = (i == len(node_history) - 1)
            if is_last and pending_user_input_rendered:
                continue
            messages.append({
                "role": "assistant",
                "content": response,
            })

    return messages


def insert_context_state_user_input(
    messages: list[dict],
    user_input: Optional[str],
) -> list[dict]:
    """Insert user_input from context_state if not already present in messages.

    This captures the original user input that may not be in node metadata.
    The input is inserted after any initial assistant messages but before the rest.

    Args:
        messages: Existing messages list (mutated in place AND returned).
        user_input: The user_input string from context_state, or None.

    Returns:
        The messages list (same reference, possibly mutated).
    """
    if not user_input:
        return messages

    # Check if already present
    if any(m.get("content") == user_input for m in messages if m["role"] == "user"):
        return messages

    # Insert after initial assistant messages, before completion
    insert_idx = 0
    for idx, m in enumerate(messages):
        if m["role"] == "assistant":
            insert_idx = idx + 1
        else:
            break

    messages.insert(insert_idx, {
        "role": "user",
        "content": user_input,
    })

    return messages


# =============================================================================
# Problem Statement Cleaning
# =============================================================================

_PREFIXES_TO_STRIP = [
    "The user wants to ",
    "The user wants ",
    "User wants to ",
    "User wants ",
    "The user is requesting ",
    "The user would like to ",
    "The user needs to ",
    "The user needs ",
    "This request is for ",
    "This is a request for ",
    "The request is to ",
]


def clean_problem_statement(text: str) -> str:
    """Mechanically strip 'The user wants to...' style prefixes from summary.description.

    This is a deterministic transformation, not LLM-based.
    After stripping, the first letter is capitalized.
    """
    if not text:
        return ""

    result = text.strip()
    for prefix in _PREFIXES_TO_STRIP:
        if result.lower().startswith(prefix.lower()):
            result = result[len(prefix):]
            if result:
                result = result[0].upper() + result[1:]
            break

    return result


# =============================================================================
# Intake Document Field Extraction
# =============================================================================

def extract_intake_doc_from_context_state(context_state: dict) -> dict:
    """Extract intake document from context_state, trying multiple keys.

    The intake document may be stored under different keys depending on
    the workflow execution path.

    Returns the found document dict, or empty dict if none found.
    """
    if not context_state:
        return {}
    return (
        context_state.get("document_concierge_intake_document")
        or context_state.get("last_produced_document")
        or context_state.get("concierge_intake_document")
        or {}
    )


def extract_constraints_explicit(intake_doc: dict) -> list:
    """Extract explicit constraints from intake document.

    Handles both dict-style constraints (with 'explicit' key) and list-style.
    """
    constraints = intake_doc.get("constraints")
    if isinstance(constraints, dict):
        return constraints.get("explicit", [])
    if isinstance(constraints, list):
        return constraints
    return []


def extract_project_type(intake_doc: dict) -> str:
    """Extract project type category from intake document.

    Handles both dict-style project_type (with 'category' key) and string-style.
    """
    project_type = intake_doc.get("project_type")
    if isinstance(project_type, dict):
        return project_type.get("category", "unknown")
    if isinstance(project_type, str):
        return project_type
    return "unknown"


def extract_problem_statement(intake_doc: dict) -> str:
    """Extract and clean problem statement from intake document summary.

    Pulls description from summary dict, then applies clean_problem_statement.
    """
    summary = intake_doc.get("summary", {})
    raw_description = summary.get("description", "") if isinstance(summary, dict) else ""
    return clean_problem_statement(raw_description)


# =============================================================================
# Completion Context Assembly (pure part)
# =============================================================================

def assemble_completion_data(
    gate_outcome: Optional[str],
    terminal_outcome: Optional[str],
    context_state: dict,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    project_url: Optional[str] = None,
    has_project: bool = False,
    execution_id: Optional[str] = None,
) -> dict:
    """Assemble the pure data portion of completion context.

    This extracts all deterministic data from the workflow state without
    performing any I/O. The caller is responsible for project creation
    and request/template concerns.

    Returns a dict suitable for merging into template context.
    """
    intake_doc = extract_intake_doc_from_context_state(context_state)
    interpretation = context_state.get("interpretation", {}) if context_state else {}

    outcome_info = get_completion_outcome_display(
        gate_outcome=gate_outcome,
        has_project=has_project,
        project_id=project_id,
    )

    return {
        "execution_id": execution_id,
        "gate_outcome": gate_outcome,
        "project_id": project_id,
        "project_name": intake_doc.get("project_name") or project_name,
        "project_url": project_url,
        "terminal_outcome": terminal_outcome,
        "outcome_title": outcome_info["title"],
        "outcome_description": outcome_info["description"],
        "outcome_color": outcome_info["color"],
        "next_action": outcome_info["next_action"],
        "problem_statement": extract_problem_statement(intake_doc),
        "constraints_explicit": extract_constraints_explicit(intake_doc),
        "project_type": extract_project_type(intake_doc),
        "routing_rationale": intake_doc.get("routing_rationale", ""),
        "interpretation": interpretation,
        "is_completed": True,
        "is_paused": False,
        "pending_user_input_rendered": None,
        "pending_choices": None,
        "escalation_active": False,
        "phase": "complete",
    }

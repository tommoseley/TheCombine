"""Pure functions for intake workflow state/message building -- WS-CRAP-002.

Extracted from app/api/v1/routers/intake.py to enable Tier-1 testing.
These functions perform data transformations with no I/O, no DB, no logging.
"""

from typing import Any, Dict, List, Optional


def extract_messages(
    node_history: List[Dict[str, Any]],
    context_state_user_input: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Extract conversation messages from workflow node history.

    Messages are returned in chronological order (oldest first).

    Args:
        node_history: List of node execution metadata dicts.
            Each dict may have "user_input", "response", "user_prompt" keys.
        context_state_user_input: User input from context_state, included
            if not already represented in the message list.

    Returns:
        List of {"role": "user"|"assistant", "content": str} dicts.
    """
    messages: List[Dict[str, str]] = []

    for execution in node_history:
        metadata = execution if isinstance(execution, dict) else getattr(execution, "metadata", execution)
        if isinstance(metadata, dict):
            if metadata.get("user_input"):
                messages.append({"role": "user", "content": metadata["user_input"]})
            response = metadata.get("response") or metadata.get("user_prompt")
            if response:
                messages.append({"role": "assistant", "content": response})

    # Include user_input from context_state if not in messages
    if context_state_user_input and not any(
        m["content"] == context_state_user_input
        for m in messages
        if m["role"] == "user"
    ):
        insert_idx = 0
        for idx, m in enumerate(messages):
            if m["role"] == "assistant":
                insert_idx = idx + 1
            else:
                break
        messages.insert(insert_idx, {"role": "user", "content": context_state_user_input})

    return messages


def build_interpretation(interpretation_raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build typed interpretation dict from raw context_state interpretation.

    Each value is normalized to {value, source, locked} structure.
    """
    interpretation: Dict[str, Dict[str, Any]] = {}
    for key, val in interpretation_raw.items():
        if isinstance(val, dict):
            interpretation[key] = {
                "value": val.get("value", ""),
                "source": val.get("source", "llm"),
                "locked": val.get("locked", False),
            }
        else:
            interpretation[key] = {
                "value": str(val),
                "source": "llm",
                "locked": False,
            }
    return interpretation


def determine_phase(
    context_state_phase: Optional[str],
    is_completed: bool,
) -> str:
    """Determine the current intake phase.

    Returns "complete" if the workflow is completed, otherwise returns
    the phase from context_state (defaulting to "describe").
    """
    if is_completed:
        return "complete"
    return context_state_phase or "describe"


def deduplicate_pending_prompt(
    pending_prompt: Optional[str],
    messages: List[Dict[str, str]],
) -> Optional[str]:
    """Remove pending_prompt if it duplicates the last assistant message.

    Prevents duplication in the UI when the pending prompt is already
    shown as the last assistant message in the conversation.
    """
    if not pending_prompt or not messages:
        return pending_prompt

    # Find the last assistant message
    for m in reversed(messages):
        if m["role"] == "assistant":
            if m["content"] == pending_prompt:
                return None
            break

    return pending_prompt

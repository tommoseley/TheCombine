"""
Work Statement state machine.

Defines the valid states and transitions for Work Statement documents.
Pure module — no dependencies on DB or handlers.
"""

WS_STATES = ["DRAFT", "READY", "IN_PROGRESS", "ACCEPTED", "REJECTED", "BLOCKED"]

WS_VALID_TRANSITIONS = {
    "DRAFT": ["READY"],
    "READY": ["IN_PROGRESS"],
    "IN_PROGRESS": ["ACCEPTED", "REJECTED", "BLOCKED"],
    "BLOCKED": ["IN_PROGRESS"],
    "ACCEPTED": [],  # Terminal state
    "REJECTED": [],  # Terminal state
}


class InvalidWSTransitionError(ValueError):
    """Raised when an invalid Work Statement state transition is attempted."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid WS transition: {current} -> {target}. "
            f"Valid targets from {current}: {WS_VALID_TRANSITIONS.get(current, [])}"
        )


def validate_ws_transition(current: str, target: str) -> bool:
    """
    Validate a Work Statement state transition.

    Args:
        current: Current state
        target: Desired target state

    Returns:
        True if the transition is valid

    Raises:
        InvalidWSTransitionError: If the transition is not allowed
    """
    valid_targets = WS_VALID_TRANSITIONS.get(current, [])
    if target not in valid_targets:
        raise InvalidWSTransitionError(current, target)
    return True

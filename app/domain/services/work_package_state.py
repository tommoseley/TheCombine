"""
Work Package state machine.

Defines the valid states and transitions for Work Package documents.
Pure module — no dependencies on DB or handlers.
"""

WP_STATES = ["PLANNED", "READY", "IN_PROGRESS", "AWAITING_GATE", "DONE"]

WP_VALID_TRANSITIONS = {
    "PLANNED": ["READY"],
    "READY": ["IN_PROGRESS"],
    "IN_PROGRESS": ["AWAITING_GATE"],
    "AWAITING_GATE": ["DONE"],
    "DONE": [],  # Terminal state
}


class InvalidWPTransitionError(ValueError):
    """Raised when an invalid Work Package state transition is attempted."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid WP transition: {current} -> {target}. "
            f"Valid targets from {current}: {WP_VALID_TRANSITIONS.get(current, [])}"
        )


def validate_wp_transition(current: str, target: str) -> bool:
    """
    Validate a Work Package state transition.

    Args:
        current: Current state
        target: Desired target state

    Returns:
        True if the transition is valid

    Raises:
        InvalidWPTransitionError: If the transition is not allowed
    """
    valid_targets = WP_VALID_TRANSITIONS.get(current, [])
    if target not in valid_targets:
        raise InvalidWPTransitionError(current, target)
    return True

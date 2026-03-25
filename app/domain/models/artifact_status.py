"""
Artifact Status Model (ADR-063).

MVP status set for pipeline rewind and regeneration.
Three statuses with deterministic, auditable transitions.
"""

from enum import Enum
from typing import Dict, FrozenSet


class ArtifactStatus(Enum):
    """
    Document artifact status per ADR-063 Section 12.

    current: The active, authoritative artifact used for downstream progression.
    stale: Invalidated due to upstream rewind; no longer eligible for downstream use.
    superseded: Replaced by a regenerated version; retained for lineage and audit.
    """

    CURRENT = "current"
    STALE = "stale"
    SUPERSEDED = "superseded"


# Legal transitions: from_status -> set of allowed to_statuses
LEGAL_TRANSITIONS: Dict[ArtifactStatus, FrozenSet[ArtifactStatus]] = {
    ArtifactStatus.CURRENT: frozenset({ArtifactStatus.STALE, ArtifactStatus.SUPERSEDED}),
    ArtifactStatus.STALE: frozenset({ArtifactStatus.SUPERSEDED}),
    ArtifactStatus.SUPERSEDED: frozenset(),  # terminal — no transitions out
}


def validate_transition(from_status: ArtifactStatus, to_status: ArtifactStatus) -> bool:
    """Check if a status transition is legal. Returns True if allowed."""
    allowed = LEGAL_TRANSITIONS.get(from_status, frozenset())
    return to_status in allowed


class IllegalTransitionError(Exception):
    """Raised when an illegal status transition is attempted."""

    def __init__(self, from_status: ArtifactStatus, to_status: ArtifactStatus):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Illegal status transition: {from_status.value} → {to_status.value}. "
            f"Allowed from {from_status.value}: "
            f"{[s.value for s in LEGAL_TRANSITIONS.get(from_status, frozenset())]}"
        )

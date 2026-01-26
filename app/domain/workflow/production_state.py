"""Production Line state model per ADR-043.

This module defines the canonical vocabulary for document production.
All UI, logs, and APIs MUST use these terms exclusively.

Prohibited terms (conversational language):
- generate, generation -> use assemble, assembly
- retry, retry_count -> use remediation, remediation_count
- failed, failure -> use audit_rejected, halted
- success -> use stabilized
- pending -> use queued, blocked
- paused -> use awaiting_operator
- error -> use halted
"""

from enum import Enum


class ProductionState(str, Enum):
    """Document production states.

    State transitions:
        Queued -> Binding -> Assembling -> Auditing -> Stabilized
                                              |
                                        Remediating <-+ (loop max 2)
                                              |
                                           Halted -> Escalated
    """

    # Pre-production
    QUEUED = "queued"  # Waiting to enter the line
    BLOCKED = "blocked"  # Upstream dependency incomplete

    # Active production
    BINDING = "binding"  # Loading context, constraints, dependencies
    ASSEMBLING = "assembling"  # LLM constructing the artifact
    AUDITING = "auditing"  # QA validation against bound constraints
    REMEDIATING = "remediating"  # Self-correction cycle in progress

    # Operator required
    AWAITING_OPERATOR = "awaiting_operator"  # Line stopped; operator input required

    # Terminal states
    STABILIZED = "stabilized"  # Artifact passed audit, production complete
    HALTED = "halted"  # Circuit breaker tripped; requires review
    ESCALATED = "escalated"  # Operator reviewed halt, accepted without resolution


class Station(str, Enum):
    """Production stations within a track.

    Each station represents a discrete step in document production.
    Used for branch map visualization and telemetry.
    """

    BIND = "bind"  # Loading constraints from intake, PGC, upstream docs
    ASM = "asm"  # LLM assembling the artifact
    AUD = "aud"  # Semantic and structural audit
    REM = "rem"  # Remediation cycle (self-correction)


class InterruptType(str, Enum):
    """Types of operator interrupts that stop the line."""

    CLARIFICATION_REQUIRED = "clarification_required"  # PGC needs operator input
    AUDIT_REVIEW = "audit_review"  # Circuit breaker tripped, needs review
    CONSTRAINT_CONFLICT = "constraint_conflict"  # Bound constraints conflict


# Mapping from legacy terminology to production states
# Used during migration and for backward compatibility
LEGACY_TO_PRODUCTION_STATE = {
    # Old outcome values -> new states
    "pending": ProductionState.QUEUED,
    "paused": ProductionState.AWAITING_OPERATOR,
    "needs_user_input": ProductionState.AWAITING_OPERATOR,
    "success": ProductionState.STABILIZED,
    "complete": ProductionState.STABILIZED,
    "failed": ProductionState.HALTED,
    "error": ProductionState.HALTED,
    "blocked": ProductionState.BLOCKED,
}


def map_node_outcome_to_state(
    node_type: str,
    outcome: str,
    is_terminal: bool = False,
) -> ProductionState:
    """Map workflow node outcomes to production states.

    Args:
        node_type: Type of node (pgc, task, qa, gate)
        outcome: Node execution outcome
        is_terminal: Whether this is the final node in the workflow

    Returns:
        Appropriate ProductionState
    """
    # Node-specific mappings take precedence
    if node_type == "pgc":
        if outcome == "needs_user_input":
            return ProductionState.AWAITING_OPERATOR
        elif outcome == "success":
            return ProductionState.BINDING  # Constraints bound, ready for assembly

    elif node_type == "task":
        if outcome == "success":
            return ProductionState.AUDITING if not is_terminal else ProductionState.STABILIZED

    elif node_type == "qa":
        if outcome == "success":
            return ProductionState.STABILIZED if is_terminal else ProductionState.AUDITING
        elif outcome == "failed":
            return ProductionState.REMEDIATING

    # Legacy mappings for unknown node types or generic outcomes
    if outcome in LEGACY_TO_PRODUCTION_STATE:
        return LEGACY_TO_PRODUCTION_STATE[outcome]

    # Default fallback
    return ProductionState.QUEUED


def map_station_from_node(node_type: str, node_id: str) -> Station:
    """Map workflow node to production station.

    Args:
        node_type: Type of node
        node_id: Node identifier (used for hints like "remediation")

    Returns:
        Appropriate Station
    """
    if node_type == "pgc":
        return Station.BIND
    elif node_type == "task":
        if "remediat" in node_id.lower():
            return Station.REM
        return Station.ASM
    elif node_type == "qa":
        return Station.AUD
    else:
        return Station.BIND  # Default for unknown


# User-facing phrasing for each state
STATE_DISPLAY_TEXT = {
    ProductionState.QUEUED: "Queued",
    ProductionState.BLOCKED: "Blocked",
    ProductionState.BINDING: "Binding...",
    ProductionState.ASSEMBLING: "Assembling...",
    ProductionState.AUDITING: "Auditing...",
    ProductionState.REMEDIATING: "Remediating",
    ProductionState.AWAITING_OPERATOR: "Awaiting operator",
    ProductionState.STABILIZED: "Stabilized",
    ProductionState.HALTED: "Halted",
    ProductionState.ESCALATED: "Escalated",
}


# User-facing phrasing for stations
STATION_DISPLAY_TEXT = {
    Station.BIND: "Binding",
    Station.ASM: "Assembling",
    Station.AUD: "Auditing",
    Station.REM: "Remediating",
}

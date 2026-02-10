"""Production Line state model per ADR-043.

This module defines the canonical vocabulary for document production.
All UI, logs, and APIs MUST use these terms exclusively.

Production States (operator-facing):
- Produced: Final, certified artifact
- In Production: Actively moving through the line
- Ready for Production: All requirements met, can start immediately
- Requirements Not Met: Blocked by missing inputs
- Halted: Explicit stop (error, policy, operator intervention)

Stations (within In Production):
- PGC: Pre-Gen Check (binding constraints)
- ASM: Assembly (LLM constructing artifact)
- QA: Audit (validation)
- REM: Remediation (self-correction)
"""

from enum import Enum


class ProductionState(str, Enum):
    """Document production states.

    State transitions:
        Requirements Not Met -> Ready for Production
        Ready for Production -> In Production
        In Production -> Produced
                      -> Halted (if error/policy/operator)
    """

    # Pre-production
    READY_FOR_PRODUCTION = "ready_for_production"  # All requirements met, can start
    REQUIREMENTS_NOT_MET = "requirements_not_met"  # Blocked by missing inputs

    # Active production (internally at various stations)
    IN_PRODUCTION = "in_production"  # Actively moving through the line

    # Operator required
    AWAITING_OPERATOR = "awaiting_operator"  # Line stopped; operator input required

    # Terminal states
    PRODUCED = "produced"  # Artifact passed audit, production complete
    HALTED = "halted"  # Explicit stop: error, policy, or operator intervention


class Station(str, Enum):
    """Production stations within a track.

    Each station represents a discrete step in document production.
    Used for branch map visualization and telemetry.

    When a document is "In Production", it's at one of these stations.
    Per WS-SUBWAY-MAP-001 Phase 2, there are 6 stations.
    """

    PGC = "pgc"  # Pre-Gen Check: binding constraints from intake, upstream docs
    ASM = "asm"  # Assembly: LLM constructing the artifact
    DRAFT = "draft"  # Draft Available: document content ready for preview while QA runs
    QA = "qa"  # Audit: semantic and structural validation
    REM = "rem"  # Remediation: self-correction cycle
    DONE = "done"  # Finalization: production complete


class InterruptType(str, Enum):
    """Types of operator interrupts that stop the line."""

    CLARIFICATION_REQUIRED = "clarification_required"  # PGC needs operator input
    AUDIT_REVIEW = "audit_review"  # Circuit breaker tripped, needs review
    CONSTRAINT_CONFLICT = "constraint_conflict"  # Bound constraints conflict


# Mapping from legacy terminology to production states
# Used during migration and for backward compatibility
LEGACY_TO_PRODUCTION_STATE = {
    # Old outcome values -> new states
    "pending": ProductionState.READY_FOR_PRODUCTION,
    "queued": ProductionState.READY_FOR_PRODUCTION,
    "blocked": ProductionState.REQUIREMENTS_NOT_MET,
    "binding": ProductionState.IN_PRODUCTION,
    "assembling": ProductionState.IN_PRODUCTION,
    "auditing": ProductionState.IN_PRODUCTION,
    "remediating": ProductionState.IN_PRODUCTION,
    "paused": ProductionState.AWAITING_OPERATOR,
    "needs_user_input": ProductionState.AWAITING_OPERATOR,
    "awaiting_operator": ProductionState.AWAITING_OPERATOR,
    "success": ProductionState.PRODUCED,
    "complete": ProductionState.PRODUCED,
    "stabilized": ProductionState.PRODUCED,
    "ready": ProductionState.PRODUCED,
    "failed": ProductionState.HALTED,
    "error": ProductionState.HALTED,
    "halted": ProductionState.HALTED,
    "escalated": ProductionState.HALTED,
}


def map_node_outcome_to_state(
    node_type: str,
    outcome: str,
    is_terminal: bool = False,
) -> tuple[ProductionState, Station]:
    """Map workflow node outcomes to production states.

    Args:
        node_type: Type of node (pgc, task, qa, gate)
        outcome: Node execution outcome
        is_terminal: Whether this is the final node in the workflow

    Returns:
        Tuple of (ProductionState, Station)
    """
    # Determine station from node type
    if node_type == "pgc":
        station = Station.PGC
    elif node_type == "task":
        station = Station.ASM
    elif node_type == "qa":
        station = Station.QA
    else:
        station = Station.PGC  # Default

    # Determine state from outcome
    if node_type == "pgc":
        if outcome == "needs_user_input":
            return ProductionState.AWAITING_OPERATOR, station
        elif outcome == "success":
            return ProductionState.IN_PRODUCTION, Station.ASM

    elif node_type == "task":
        if outcome == "success":
            if is_terminal:
                return ProductionState.PRODUCED, Station.DONE
            return ProductionState.IN_PRODUCTION, Station.QA

    elif node_type == "qa":
        if outcome == "success":
            return ProductionState.PRODUCED, Station.DONE
        elif outcome == "failed":
            return ProductionState.IN_PRODUCTION, Station.REM

    # Legacy mappings for unknown outcomes
    if outcome in LEGACY_TO_PRODUCTION_STATE:
        return LEGACY_TO_PRODUCTION_STATE[outcome], station

    # Default fallback
    return ProductionState.READY_FOR_PRODUCTION, station


def map_station_from_node(node_type: str, node_id: str) -> Station:
    """Map workflow node to production station.

    Args:
        node_type: Type of node
        node_id: Node identifier (used for hints like "remediation")

    Returns:
        Appropriate Station
    """
    if node_type == "pgc":
        return Station.PGC
    elif node_type == "task":
        if "remediat" in node_id.lower():
            return Station.REM
        return Station.ASM
    elif node_type == "qa":
        return Station.QA
    else:
        return Station.PGC  # Default for unknown


# User-facing phrasing for each state
STATE_DISPLAY_TEXT = {
    ProductionState.READY_FOR_PRODUCTION: "Ready for Production",
    ProductionState.REQUIREMENTS_NOT_MET: "Requirements Not Met",
    ProductionState.IN_PRODUCTION: "In Production",
    ProductionState.AWAITING_OPERATOR: "Awaiting Operator",
    ProductionState.PRODUCED: "Produced",
    ProductionState.HALTED: "Halted",
}


# User-facing phrasing for stations (shown as "In Production at {station}")
STATION_DISPLAY_TEXT = {
    Station.PGC: "Pre-Gen Check",
    Station.ASM: "Assembly",
    Station.DRAFT: "Draft Available",
    Station.QA: "Audit",
    Station.REM: "Remediation",
    Station.DONE: "Complete",
}

"""
Work Binder Audit + Governance Invariants — WS-WB-008.

Provides:
1. Structured audit event builder for all WB mutations.
2. Pure governance invariant validators that enforce hard rules.

Pure module — no DB, no handlers, no external dependencies.
All functions are stateless and side-effect-free for Tier-1 testability.
"""

from datetime import datetime, timezone
from typing import Any


# ===========================================================================
# Supported event types (exhaustive)
# ===========================================================================

SUPPORTED_EVENT_TYPES = {
    "candidate_import",
    "candidate_promotion",
    "wp_created",
    "wp_updated",
    "ws_created",
    "ws_updated",
    "ws_reordered",
    "ws_stabilized",
    "state_transition",
}


# ===========================================================================
# Audit Event Builder
# ===========================================================================


def build_audit_event(
    event_type: str,
    entity_id: str,
    entity_type: str,
    mutation_data: dict[str, Any],
    actor: str = "system",
) -> dict[str, Any]:
    """Build a structured audit event dict for a Work Binder mutation.

    Args:
        event_type: One of SUPPORTED_EVENT_TYPES.
        entity_id: The ID of the mutated entity (wp_id, ws_id, wpc_id, etc.).
        entity_type: The type of entity ('work_package', 'work_statement',
                      'work_package_candidate').
        mutation_data: Dict with before/after data describing the mutation.
                       Structure varies by event_type but should include
                       relevant before/after values where applicable.
        actor: Who performed the mutation (default 'system').

    Returns:
        Structured audit event dict with all required fields.

    Raises:
        ValueError: If event_type is not in SUPPORTED_EVENT_TYPES.
    """
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(
            f"Unsupported event_type '{event_type}'. "
            f"Must be one of: {sorted(SUPPORTED_EVENT_TYPES)}"
        )

    return {
        "event_type": event_type,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "mutation_data": mutation_data,
    }


# ===========================================================================
# Governance Invariant Validators
# ===========================================================================


def validate_can_create_ws(wp_content: dict[str, Any]) -> list[str]:
    """Validate that a WS can be created on this WP.

    Rule: Cannot create WS on a WP with governance_pins.ta_version_id == "pending".
    The TA must have reviewed the WP before work statements can be authored.

    Args:
        wp_content: The Work Package content dict.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []
    governance_pins = wp_content.get("governance_pins", {})
    ta_version_id = governance_pins.get("ta_version_id")
    if ta_version_id == "pending":
        errors.append(
            "Cannot create WS: governance_pins.ta_version_id is 'pending'. "
            "Technical Architect review required before WS authoring."
        )
    return errors


def validate_can_promote(
    transformation: str,
    transformation_notes: str,
) -> list[str]:
    """Validate that a candidate can be promoted.

    Rule: Cannot promote without transformation metadata.
    Both transformation and transformation_notes must be non-empty.

    Args:
        transformation: The transformation type (e.g., 'kept', 'split').
        transformation_notes: Explanation of how the candidate was transformed.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []
    if not transformation or not transformation.strip():
        errors.append(
            "Cannot promote: transformation is required."
        )
    if not transformation_notes or not transformation_notes.strip():
        errors.append(
            "Cannot promote: transformation_notes is required "
            "(explain how the candidate was transformed)."
        )
    return errors


def validate_can_reorder(wp_content: dict[str, Any]) -> list[str]:
    """Validate that WSs can be reordered on this WP.

    Rule: Cannot reorder WSs on a DONE WP.

    Args:
        wp_content: The Work Package content dict.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []
    state = wp_content.get("state", "")
    if state == "DONE":
        errors.append(
            "Cannot reorder work statements: Work Package is in DONE state."
        )
    return errors


def validate_provenance(actor: str) -> list[str]:
    """Validate that a mutation has provenance (non-empty actor).

    Rule: All writes must have provenance — anonymous mutations are forbidden.

    Args:
        actor: The actor performing the mutation.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []
    if not actor or not actor.strip():
        errors.append(
            "Provenance violation: actor must be non-empty for all mutations."
        )
    return errors

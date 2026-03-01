"""
WP Promotion Service -- WS-WB-004.

Promotes a WP candidate (WPC) to a governed Work Package document
with full lineage, audit trail, and transformation metadata.

Pure module -- no DB, no handlers, no external dependencies.
All functions are stateless and side-effect-free for Tier-1 testability.
"""

import re
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TRANSFORMATIONS = {"kept", "split", "merged", "added"}

_WPC_ID_PATTERN = re.compile(r"^WPC-(\d{1,4})$")


# ---------------------------------------------------------------------------
# wp_id derivation
# ---------------------------------------------------------------------------


def derive_wp_id(wpc_id: str) -> str:
    """Derive a snake_case wp_id from a WPC-NNN candidate ID.

    WPC-001 -> wp_wb_001
    WPC-002 -> wp_wb_002
    WPC-1234 -> wp_wb_1234

    The 'wb' prefix indicates Work Binder origin.
    The numeric portion is preserved without zero-padding changes.
    """
    match = _WPC_ID_PATTERN.match(wpc_id)
    if match:
        numeric = match.group(1)
        return f"wp_wb_{numeric}"
    # Fallback: lowercase, replace hyphens with underscores
    return wpc_id.lower().replace("-", "_")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_promotion_request(transformation: str) -> list[str]:
    """Validate the promotion request.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []
    if transformation not in VALID_TRANSFORMATIONS:
        errors.append(
            f"Invalid transformation '{transformation}'. "
            f"Must be one of: {sorted(VALID_TRANSFORMATIONS)}"
        )
    return errors


# ---------------------------------------------------------------------------
# WP document builder
# ---------------------------------------------------------------------------


def build_promoted_wp(
    candidate: dict,
    transformation: str,
    transformation_notes: str,
    title_override: str | None = None,
    rationale_override: str | None = None,
) -> dict:
    """Build a governed WP document from a WPC candidate.

    Returns a dict conforming to work_package v1.1.0 schema:
    - wp_id derived from wpc_id (e.g., WPC-001 -> wp_wb_001)
    - state: PLANNED
    - ws_index: [] (empty)
    - revision: { edition: 1 }
    - source_candidate_ids: [wpc_id]
    - transformation + transformation_notes
    - _lineage: full provenance chain
    - governance_pins: { ta_version_id: "pending" }

    Does not mutate the input candidate dict.
    """
    wpc_id = candidate["wpc_id"]
    wp_id = derive_wp_id(wpc_id)

    title = title_override if title_override is not None else candidate.get("title", "")
    rationale = rationale_override if rationale_override is not None else candidate.get("rationale", "")
    scope_in = list(candidate.get("scope_summary", []))

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "wp_id": wp_id,
        "title": title,
        "rationale": rationale,
        "scope_in": scope_in,
        "scope_out": [],
        "dependencies": [],
        "definition_of_done": ["All work statements executed and verified"],
        "governance_pins": {
            "ta_version_id": "pending",
        },
        "state": "PLANNED",
        "ws_index": [],
        "revision": {
            "edition": 1,
            "updated_at": now_iso,
            "updated_by": "system",
        },
        "source_candidate_ids": [wpc_id],
        "transformation": transformation,
        "transformation_notes": transformation_notes,
        "_lineage": {
            "parent_document_type": "work_package_candidate",
            "parent_execution_id": None,
            "source_candidate_ids": [wpc_id],
            "transformation": transformation,
            "transformation_notes": transformation_notes,
        },
    }


# ---------------------------------------------------------------------------
# Audit event builder
# ---------------------------------------------------------------------------


def build_audit_event(
    wpc_id: str,
    wp_id: str,
    transformation: str,
    promoted_by: str,
) -> dict:
    """Build an audit event dict for a WPC -> WP promotion.

    The event captures who promoted what, when, and how (transformation).
    """
    return {
        "event_type": "wp_promotion",
        "wpc_id": wpc_id,
        "wp_id": wp_id,
        "transformation": transformation,
        "promoted_by": promoted_by,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

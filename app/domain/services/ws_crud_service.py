"""
WS CRUD service — pure functions for Work Statement lifecycle.

Provides deterministic ID generation, lexicographic ordering,
plane separation validation, stabilization checks, and ws_index
manipulation. All functions are pure (dict in, dict out) for
Tier 1 testability.

WS-WB-006.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional


# ===========================================================================
# Structured stabilization findings (WS-PI-2D)
# ===========================================================================

@dataclass(frozen=True)
class StabilizationFinding:
    """A structured failure from a stabilization gate check."""
    rule_id: str
    artifact_id: str
    field_path: Optional[str]
    message: str
    remediation_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ===========================================================================
# Field sets for plane separation
# ===========================================================================

# Fields that MUST NOT appear in a WS update (WP-exclusive fields)
WS_BLOCKED_IN_UPDATE = {
    "ws_index",
    "change_summary",
    "ws_child_refs",
    "ws_total",
    "ws_done",
    "mode_b_count",
    "source_candidate_ids",
    "transformation",
    "transformation_notes",
    "definition_of_done",
    "dependencies",
}

# Fields that MUST NOT appear in a WP update (WS-exclusive fields)
WP_BLOCKED_IN_UPDATE = {
    "parent_wp_id",
    "objective",
    "procedure",
    "verification_criteria",
    "prohibited_actions",
    "allowed_paths",
    "order_key",
}

# WS required fields for stabilization (DRAFT -> READY)
WS_REQUIRED_FOR_STABILIZE = {
    "title",
    "objective",
    "procedure",
    "verification_criteria",
}


# ===========================================================================
# Order key generation
# ===========================================================================

def generate_order_key(existing_keys: list[str]) -> str:
    """
    Generate the next lexicographic order key.

    Starts at 'a0', increments to 'a1', 'a2', ..., 'a9', 'b0', etc.

    Args:
        existing_keys: List of existing order keys

    Returns:
        Next order key in lexicographic sequence
    """
    if not existing_keys:
        return "a0"

    # Find the highest key
    sorted_keys = sorted(existing_keys)
    last_key = sorted_keys[-1]

    if len(last_key) < 2:
        return "a0"

    letter = last_key[0]
    digit = last_key[1]

    if digit == "9":
        # Roll to next letter
        next_letter = chr(ord(letter) + 1)
        return f"{next_letter}0"
    else:
        next_digit = str(int(digit) + 1)
        return f"{letter}{next_digit}"


# ===========================================================================
# Document builders
# ===========================================================================

def build_new_ws(
    wp_id: str,
    ws_id: str,
    order_key: str,
    content: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a new WS document in DRAFT state with revision edition 1.

    Args:
        wp_id: Parent Work Package ID
        ws_id: The generated WS ID
        order_key: Lexicographic order key
        content: User-provided content fields

    Returns:
        Complete WS document dict
    """
    ws = {
        "ws_id": ws_id,
        "parent_wp_id": wp_id,
        "state": "DRAFT",
        "order_key": order_key,
        "revision": {"edition": 1},
        "title": content.get("title", ""),
        "objective": content.get("objective", ""),
        "scope_in": content.get("scope_in", []),
        "scope_out": content.get("scope_out", []),
        "allowed_paths": content.get("allowed_paths", []),
        "procedure": content.get("procedure", []),
        "verification_criteria": content.get("verification_criteria", []),
        "prohibited_actions": content.get("prohibited_actions", []),
        "governance_pins": content.get("governance_pins", {}),
    }
    return ws


# ===========================================================================
# Plane separation validation
# ===========================================================================

def validate_ws_update_fields(update_data: dict[str, Any]) -> list[str]:
    """
    Reject WP-level fields in a WS update.

    Checks update_data keys against the WS_BLOCKED_IN_UPDATE set.

    Args:
        update_data: The update payload dict

    Returns:
        List of error messages. Empty if valid.
    """
    violations = []
    for key in update_data:
        if key in WS_BLOCKED_IN_UPDATE:
            violations.append(
                f"Field '{key}' is a WP-level field and cannot be set via WS update"
            )
    return violations


def validate_wp_update_fields(update_data: dict[str, Any]) -> list[str]:
    """
    Reject WS content fields in a WP update.

    Checks update_data keys against the WP_BLOCKED_IN_UPDATE set.

    Args:
        update_data: The update payload dict

    Returns:
        List of error messages. Empty if valid.
    """
    violations = []
    for key in update_data:
        if key in WP_BLOCKED_IN_UPDATE:
            violations.append(
                f"Field '{key}' is a WS-level field and cannot be set via WP update"
            )
    return violations


# ===========================================================================
# Stabilization validation
# ===========================================================================

def validate_stabilization(ws_content: dict[str, Any]) -> list[str]:
    """
    Validate all required fields present for DRAFT -> READY transition.

    Args:
        ws_content: The WS document content

    Returns:
        List of error messages. Empty if valid.
    """
    errors = []
    for field in sorted(WS_REQUIRED_FOR_STABILIZE):
        value = ws_content.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"Required field '{field}' is missing or empty")
    return errors


# ===========================================================================
# Stabilization certification gate (WS-PI-2A)
# ===========================================================================

def certify_wp_for_stabilization(
    wp_content: dict[str, Any],
    ws_contents: list[dict[str, Any]],
) -> list[StabilizationFinding]:
    """
    Certify a WP artifact set for stabilization.

    Checks:
    1. At least one WS exists
    2. WP governance_pins.policy_refs contains POL-ADR-EXEC-001
    3. Each WS governance_pins.policy_refs contains POL-WS-001

    Args:
        wp_content: The WP document content dict
        ws_contents: List of WS document content dicts

    Returns:
        List of StabilizationFinding objects. Empty means certified.
    """
    findings: list[StabilizationFinding] = []
    wp_id = wp_content.get("wp_id", "unknown")

    # 1. Completeness: at least one WS
    if not ws_contents:
        findings.append(StabilizationFinding(
            rule_id="CERT-001",
            artifact_id=wp_id,
            field_path=None,
            message="WP has no Work Statements — cannot stabilize an empty package",
            remediation_hint="Create at least one Work Statement before stabilizing",
        ))

    # 2. WP governance floor
    wp_pins = wp_content.get("governance_pins") or {}
    wp_policies = wp_pins.get("policy_refs") or []
    if "POL-ADR-EXEC-001" not in wp_policies:
        findings.append(StabilizationFinding(
            rule_id="CERT-002",
            artifact_id=wp_id,
            field_path="governance_pins.policy_refs",
            message="WP missing required governance floor: POL-ADR-EXEC-001",
            remediation_hint="Re-run post-processing or manually add POL-ADR-EXEC-001 to policy_refs",
        ))

    # 3. WS governance floor (per WS)
    for ws in ws_contents:
        ws_id = ws.get("ws_id", "unknown")
        ws_pins = ws.get("governance_pins") or {}
        ws_policies = ws_pins.get("policy_refs") or []
        if "POL-WS-001" not in ws_policies:
            findings.append(StabilizationFinding(
                rule_id="CERT-003",
                artifact_id=ws_id,
                field_path="governance_pins.policy_refs",
                message=f"WS {ws_id} missing required governance floor: POL-WS-001",
                remediation_hint="Re-run post-processing or manually add POL-WS-001 to policy_refs",
            ))

    return findings


# ===========================================================================
# Parent WP invariant (WS-PI-2C)
# ===========================================================================

def check_parent_wp_invariant(
    wp_id: str,
    ws_contents: list[dict[str, Any]],
) -> list[StabilizationFinding]:
    """
    Check that every WS claims the correct parent WP.

    Args:
        wp_id: The WP's wp_id being stabilized
        ws_contents: List of WS document content dicts

    Returns:
        List of StabilizationFinding objects. Empty means all WSs point to the correct parent.
    """
    findings: list[StabilizationFinding] = []
    for ws in ws_contents:
        ws_id = ws.get("ws_id", "unknown")
        parent = ws.get("parent_wp_id")
        if parent is None:
            findings.append(StabilizationFinding(
                rule_id="PARENT-001",
                artifact_id=ws_id,
                field_path="parent_wp_id",
                message=f"WS {ws_id} has no parent_wp_id field",
                remediation_hint=f"Set parent_wp_id to '{wp_id}'",
            ))
        elif parent != wp_id:
            findings.append(StabilizationFinding(
                rule_id="PARENT-002",
                artifact_id=ws_id,
                field_path="parent_wp_id",
                message=f"WS {ws_id} claims parent_wp_id={parent}, expected {wp_id}",
                remediation_hint=f"Update parent_wp_id from '{parent}' to '{wp_id}'",
            ))
    return findings


# ===========================================================================
# Referential integrity gate (WS-PI-2B)
# ===========================================================================

def check_ws_referential_integrity(
    wp_content: dict[str, Any],
    persisted_ws_ids: list[str],
) -> list[StabilizationFinding]:
    """
    Check that every WS referenced in WP ws_index exists as a persisted document.

    Args:
        wp_content: The WP document content dict
        persisted_ws_ids: List of ws_id values from actually persisted WS documents

    Returns:
        List of StabilizationFinding objects. Empty means all references resolve.
    """
    wp_id = wp_content.get("wp_id", "unknown")
    ws_index = wp_content.get("ws_index") or []
    referenced_ids = {entry.get("ws_id") for entry in ws_index if entry.get("ws_id")}
    persisted_set = set(persisted_ws_ids)

    missing = sorted(referenced_ids - persisted_set)
    if missing:
        return [StabilizationFinding(
            rule_id="REF-001",
            artifact_id=wp_id,
            field_path="ws_index",
            message=f"ws_index references {len(missing)} WS(s) that do not exist: {', '.join(missing)}",
            remediation_hint="Remove stale ws_index entries or create the missing WS documents",
        )]
    return []


# ===========================================================================
# ws_index manipulation
# ===========================================================================

def add_ws_to_wp_index(
    wp_content: dict[str, Any],
    ws_id: str,
    order_key: str,
) -> dict[str, Any]:
    """
    Add a WS entry to the WP's ws_index.

    Args:
        wp_content: Work Package content dict (modified in place and returned)
        ws_id: The Work Statement ID
        order_key: The order key for positioning

    Returns:
        Updated WP content with new entry in ws_index
    """
    ws_index = wp_content.get("ws_index", [])

    # Check for duplicate
    for entry in ws_index:
        if entry.get("ws_id") == ws_id:
            return wp_content

    ws_index.append({"ws_id": ws_id, "order_key": order_key})

    # Keep sorted by order_key
    ws_index.sort(key=lambda e: e.get("order_key", ""))

    wp_content["ws_index"] = ws_index
    return wp_content


def reorder_ws_index(
    wp_content: dict[str, Any],
    new_order: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Apply new ordering to ws_index.

    Each entry in new_order must have 'ws_id' and 'order_key'.
    Replaces the existing ws_index entirely.

    Args:
        wp_content: Work Package content dict (modified in place and returned)
        new_order: New ordered list of {ws_id, order_key} dicts

    Returns:
        Updated WP content with reordered ws_index
    """
    # Validate: new_order entries must have required fields
    validated = []
    for entry in new_order:
        validated.append({
            "ws_id": entry["ws_id"],
            "order_key": entry["order_key"],
        })

    # Sort by order_key for consistency
    validated.sort(key=lambda e: e["order_key"])

    wp_content["ws_index"] = validated
    return wp_content

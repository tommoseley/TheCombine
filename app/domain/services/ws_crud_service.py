"""
WS CRUD service — pure functions for Work Statement lifecycle.

Provides deterministic ID generation, lexicographic ordering,
plane separation validation, stabilization checks, and ws_index
manipulation. All functions are pure (dict in, dict out) for
Tier 1 testability.

WS-WB-006.
"""

from typing import Any


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
# ID generation
# ===========================================================================

def generate_ws_id(wp_id: str, sequence_num: int) -> str:
    """
    Generate deterministic WS ID from WP ID and sequence number.

    Extracts the prefix from wp_id and builds a WS ID.
    E.g., wp_id='wp_wb_001', seq=1 -> 'WS-WB-001'
    E.g., wp_id='wp_wb_001', seq=2 -> 'WS-WB-002'
    E.g., wp_id='wp_pipeline_003', seq=5 -> 'WS-PIPELINE-005'

    Args:
        wp_id: Work Package ID (e.g., 'wp_wb_001')
        sequence_num: 1-based sequence number

    Returns:
        Deterministic WS ID string
    """
    # Parse wp_id: strip 'wp_' prefix, split on last '_' to get prefix and WP number
    # But we use the WP prefix for the WS ID, not the WP number
    stripped = wp_id
    if stripped.lower().startswith("wp_"):
        stripped = stripped[3:]

    # Split into parts — the last part is the WP numeric suffix
    parts = stripped.split("_")

    # Extract prefix (everything except trailing numeric part)
    prefix_parts = []
    for part in parts:
        if part.isdigit() and not prefix_parts:
            # Numeric at start — keep it as prefix
            prefix_parts.append(part)
        elif part.isdigit() and prefix_parts:
            # Trailing numeric — this is the WP number, skip it
            break
        else:
            prefix_parts.append(part)

    prefix = "-".join(p.upper() for p in prefix_parts)

    return f"WS-{prefix}-{sequence_num:03d}"


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
        "revision": 1,
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

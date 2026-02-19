"""
Work Statement registration service — pure functions on dicts.

Cross-document operations for Work Statement ↔ Work Package interaction.
All functions are pure (dict in, dict out) for Tier 1 testability.
"""

from typing import Dict, Any, Optional


class ParentNotFoundError(ValueError):
    """Raised when a Work Statement's parent Work Package does not exist."""

    def __init__(self):
        super().__init__("Parent Work Package not found")


def validate_parent_exists(parent_wp: Optional[Dict[str, Any]]) -> None:
    """
    Validate that the parent Work Package exists.

    Args:
        parent_wp: The parent WP dict, or None if not found

    Raises:
        ParentNotFoundError: If parent_wp is None
    """
    if parent_wp is None:
        raise ParentNotFoundError()


def inherit_governance_pins(
    ws_data: Dict[str, Any], wp_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Copy governance pins from parent WP into WS.

    Args:
        ws_data: Work Statement dict (modified in place and returned)
        wp_data: Parent Work Package dict

    Returns:
        Modified ws_data with governance_pins from WP
    """
    ws_data["governance_pins"] = wp_data.get("governance_pins", {})
    return ws_data


def register_ws_on_wp(wp_data: Dict[str, Any], ws_id: str) -> Dict[str, Any]:
    """
    Register a Work Statement on its parent Work Package.

    Increments ws_total and appends ws_id to ws_child_refs.
    Idempotent — duplicate ws_id is ignored.

    Args:
        wp_data: Work Package dict (modified in place and returned)
        ws_id: The Work Statement ID to register

    Returns:
        Modified wp_data with updated rollup fields
    """
    child_refs = wp_data.get("ws_child_refs", [])
    if ws_id not in child_refs:
        child_refs.append(ws_id)
        wp_data["ws_child_refs"] = child_refs
        wp_data["ws_total"] = len(child_refs)
    return wp_data


def apply_ws_accepted_to_wp(wp_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Increment ws_done on a WP when a child WS is accepted.

    Clamps ws_done to ws_total.

    Args:
        wp_data: Work Package dict (modified in place and returned)

    Returns:
        Modified wp_data with incremented ws_done (clamped)
    """
    ws_total = wp_data.get("ws_total", 0)
    ws_done = wp_data.get("ws_done", 0)
    if ws_done < ws_total:
        wp_data["ws_done"] = ws_done + 1
    return wp_data

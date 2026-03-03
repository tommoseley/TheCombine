"""WS Proposal Service — pure functions for the PROPOSE STATEMENTS station.

WS-WB-025: Provides gate validation, WS document construction,
and ws_index entry building for the propose-ws endpoint.

All functions are pure (no DB, no LLM, no side effects) for Tier-1 testability.
The router orchestrates DB access, LLM calls, and audit events.
"""

from typing import Any, Optional

from app.domain.services.document_readiness import is_doc_ready_for_downstream
from app.domain.services.ws_crud_service import generate_order_key


def validate_proposal_gates(
    wp_content: dict[str, Any],
    ta_doc: Optional[Any],
) -> list[str]:
    """Validate all preconditions for WS proposal.

    Gates (in order):
    1. TA must be ready for downstream consumption
    2. WP ws_index must be empty (no existing WSs)

    Args:
        wp_content: The Work Package content dict.
        ta_doc: The Technical Architecture document (or None if missing).

    Returns:
        List of error messages. Empty means all gates pass.
    """
    errors: list[str] = []

    # Gate 1: TA readiness
    if not is_doc_ready_for_downstream(ta_doc):
        errors.append(
            "HARD_STOP: Cannot propose work statements until "
            "Technical Architecture is stabilized for this project."
        )

    # Gate 2: ws_index must be empty
    ws_index = wp_content.get("ws_index", [])
    if ws_index:
        errors.append(
            "HARD_STOP: Work Package already has Work Statements. "
            "Delete drafts (or resolve ws_index) before proposing again."
        )

    return errors


def build_ws_documents(
    ws_items: list[dict[str, Any]],
    wp_id: str,
) -> list[dict[str, Any]]:
    """Build WS document content dicts from LLM proposal output.

    Ensures each WS has:
    - state = "DRAFT"
    - parent_wp_id = wp_id
    - revision = 1
    - order_key assigned sequentially

    Args:
        ws_items: List of WS dicts from the LLM (already schema-validated).
        wp_id: Parent Work Package ID.

    Returns:
        List of WS content dicts ready for Document persistence.
    """
    existing_keys: list[str] = []
    docs: list[dict[str, Any]] = []

    for ws_item in ws_items:
        order_key = generate_order_key(existing_keys)
        existing_keys.append(order_key)

        ws_doc = {
            **ws_item,
            "parent_wp_id": wp_id,
            "state": "DRAFT",
            "revision": {"edition": 1},
            "order_key": order_key,
        }
        docs.append(ws_doc)

    return docs


def build_ws_index_entries(
    ws_items: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build ws_index entries from WS items.

    Args:
        ws_items: List of WS dicts (must have ws_id).

    Returns:
        Ordered list of {ws_id, order_key} dicts for WP ws_index.
    """
    existing_keys: list[str] = []
    entries: list[dict[str, str]] = []

    for ws_item in ws_items:
        order_key = generate_order_key(existing_keys)
        existing_keys.append(order_key)
        entries.append({
            "ws_id": ws_item["ws_id"],
            "order_key": order_key,
        })

    return entries

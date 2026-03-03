"""Pure helper functions extracted from PlanExecutor._spawn_child_documents.

WS-CRAP-009: Testability Refactoring -- _spawn_child_documents decomposition.

These functions handle:
1. Raw LLM envelope unwrapping
2. Execution ID lineage injection
3. SSE event payload construction
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def unwrap_raw_envelope(doc_content: Any) -> Any:
    """Unwrap raw LLM output envelope if present.

    LLM output is sometimes stored as:
        {"raw": true, "content": "```json\\n{...}\\n```"}
    This function strips the envelope and parses the inner JSON.

    Returns the original value if no raw envelope is detected.
    """
    if not isinstance(doc_content, dict):
        return doc_content
    if not doc_content.get("raw") or "content" not in doc_content:
        return doc_content

    raw_str = doc_content["content"]
    if not isinstance(raw_str, str):
        return doc_content

    cleaned = raw_str.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
        logger.debug("Unwrapped raw envelope for child document extraction")
        return parsed
    except json.JSONDecodeError:
        logger.warning("Failed to unwrap raw content for child extraction")
        return doc_content


def inject_execution_id_into_lineage(
    child_specs: list[dict],
    execution_id: Optional[str],
) -> None:
    """Inject execution_id into _lineage metadata of each child spec.

    Mutates child_specs in place. No-op if execution_id is None.
    """
    if not execution_id:
        return
    for spec in child_specs:
        lineage = spec.get("content", {}).get("_lineage")
        if lineage:
            lineage["parent_execution_id"] = execution_id


def build_children_event_payload(
    child_specs: list[dict],
    existing_ids: set[str],
    spawned_ids: set[str],
) -> dict:
    """Build the created/updated/superseded ID lists for SSE event.

    Args:
        child_specs: List of child document specs (each has "identifier")
        existing_ids: Set of instance_ids from pre-existing children
        spawned_ids: Set of instance_ids from current spec

    Returns:
        Dict with keys: created, updated, superseded
    """
    created = [
        s.get("identifier", "")
        for s in child_specs
        if s.get("identifier", "") not in existing_ids
    ]
    updated = [
        s.get("identifier", "")
        for s in child_specs
        if s.get("identifier", "") in existing_ids
    ]
    superseded = [cid for cid in existing_ids if cid not in spawned_ids]
    return {"created": created, "updated": updated, "superseded": superseded}

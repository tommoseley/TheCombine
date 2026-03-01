"""Pure data transformation functions for admin_workbench_service.py.

Extracted per WS-CRAP-003 to enable Tier-1 testing of fragment assembly,
workflow summary building, and orchestration enrichment without filesystem
or PackageLoader dependencies.
"""

from typing import Any, Dict, List, Optional


def build_fragment_dict(
    fragment_id: str,
    kind: str,
    version: str,
    name: str,
    intent: Optional[str],
    tags: List[str],
    content: str,
    source_doc_type: Optional[str],
    preview_length: int = 200,
) -> Dict[str, Any]:
    """Build a prompt fragment summary dict.

    Pure transformation: assembles a fragment summary with content preview.

    Args:
        fragment_id: Fragment identifier
        kind: Fragment kind value (role, task, qa, pgc, reflection)
        version: Version string
        name: Display name
        intent: Intent description (may be None)
        tags: List of tags
        content: Full content text
        source_doc_type: Source document type ID (None for role fragments)
        preview_length: Max characters for content_preview

    Returns:
        Fragment summary dict
    """
    preview = (
        content[:preview_length] + "..." if len(content) > preview_length else content
    )
    return {
        "fragment_id": fragment_id,
        "kind": kind,
        "version": version,
        "name": name,
        "intent": intent,
        "tags": tags,
        "content_preview": preview,
        "source_doc_type": source_doc_type,
    }


def build_workflow_summary(
    workflow_id: str,
    raw: Dict[str, Any],
    active_version: str,
) -> Optional[Dict[str, Any]]:
    """Build a graph-based workflow summary from raw definition JSON.

    Returns None if the definition is not a graph-based workflow
    (must have 'nodes' and 'edges' keys).

    Args:
        workflow_id: Workflow identifier
        raw: Raw workflow definition dict from JSON
        active_version: Active version string

    Returns:
        Workflow summary dict, or None if not graph-based
    """
    if "nodes" not in raw or "edges" not in raw:
        return None

    return {
        "workflow_id": workflow_id,
        "name": raw.get("name", workflow_id),
        "active_version": active_version,
        "description": raw.get("description"),
        "node_count": len(raw.get("nodes", [])),
        "edge_count": len(raw.get("edges", [])),
    }


def build_orchestration_summary(
    workflow_id: str,
    raw: Dict[str, Any],
    active_version: str,
) -> Optional[Dict[str, Any]]:
    """Build an orchestration workflow summary from raw definition JSON.

    Returns None if the definition IS a graph-based workflow
    (has both 'nodes' and 'edges' keys).

    Args:
        workflow_id: Workflow identifier
        raw: Raw workflow definition dict from JSON
        active_version: Active version string

    Returns:
        Orchestration workflow summary dict, or None if graph-based
    """
    if "nodes" in raw and "edges" in raw:
        return None

    derived_from = raw.get("derived_from")
    derived_from_label = None
    if derived_from and isinstance(derived_from, dict):
        derived_from_label = (
            f"{derived_from.get('workflow_id', '')} v{derived_from.get('version', '')}"
        )

    return {
        "workflow_id": workflow_id,
        "name": raw.get("name", workflow_id.replace("_", " ").title()),
        "active_version": active_version,
        "description": raw.get("description"),
        "step_count": len(raw.get("steps", [])),
        "schema_version": raw.get("schema_version", "workflow.v1"),
        "pow_class": raw.get("pow_class", "reference"),
        "derived_from": derived_from,
        "derived_from_label": derived_from_label,
        "source_version": raw.get("source_version"),
        "tags": raw.get("tags", []),
    }

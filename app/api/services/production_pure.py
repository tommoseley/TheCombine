"""Pure data transformation functions for production_service.py.

Extracted per WS-CRAP-003 to enable Tier-1 testing of track-building
and station-sequencing logic without DB or filesystem dependencies.
"""

from typing import Any, Dict, List, Optional


def build_station_sequence(
    workflow_stations: List[Dict[str, Any]],
    current_node_station_id: Optional[str],
    status: str,
    terminal_outcome: Optional[str],
    pending_user_input: bool,
) -> List[Dict[str, Any]]:
    """Build station sequence from workflow-defined stations.

    Pure transformation: takes station metadata and execution state,
    returns list of station dicts with computed state fields.

    Args:
        workflow_stations: Station list from WorkflowPlan.get_stations()
        current_node_station_id: Station ID for current node
        status: Execution status (running, paused, completed, failed)
        terminal_outcome: Terminal outcome if completed (stabilized, blocked)
        pending_user_input: Whether waiting for user input

    Returns:
        List of station dicts with station, label, state, and optionally needs_input
    """
    if not workflow_stations:
        return []

    station_order = [s["id"] for s in workflow_stations]
    current_idx = (
        station_order.index(current_node_station_id)
        if current_node_station_id in station_order
        else -1
    )

    # Handle completed/stabilized state
    if terminal_outcome == "stabilized" or status == "completed":
        return [
            {"station": s["id"], "label": s["label"], "state": "complete"}
            for s in workflow_stations
        ]

    # Handle failed/blocked state
    if terminal_outcome == "blocked" or status == "failed":
        stations = []
        for i, s in enumerate(workflow_stations):
            if i < current_idx:
                state = "complete"
            elif i == current_idx:
                state = "failed"
            else:
                state = "pending"
            stations.append({"station": s["id"], "label": s["label"], "state": state})
        return stations

    # Build stations based on current position
    stations = []
    for i, s in enumerate(workflow_stations):
        if i < current_idx:
            state = "complete"
        elif i == current_idx:
            state = "active"
            if pending_user_input:
                stations.append({
                    "station": s["id"],
                    "label": s["label"],
                    "state": "active",
                    "needs_input": True,
                })
                continue
        else:
            state = "pending"

        stations.append({"station": s["id"], "label": s["label"], "state": state})

    return stations


def classify_track_state(
    doc_type_id: str,
    documents: Dict[str, Any],
    stabilized_types: set,
    requires: List[str],
) -> tuple:
    """Classify the production state for a document type track.

    Pure transformation: given document existence and dependency info,
    returns (state, blocked_by, is_stabilized).

    Args:
        doc_type_id: Document type identifier
        documents: Dict mapping doc_type_id -> document objects (must have .status)
        stabilized_types: Set of already-stabilized document type IDs
        requires: List of required document type IDs

    Returns:
        Tuple of (state_str, blocked_by_list, is_stabilized)
    """
    from app.domain.workflow.production_state import ProductionState

    if doc_type_id in documents:
        doc = documents[doc_type_id]
        status = doc.status if hasattr(doc, "status") else doc.get("status", "")
        if status not in ("failed", "error", "cancelled"):
            return ProductionState.PRODUCED.value, [], True
        else:
            return ProductionState.READY_FOR_PRODUCTION.value, [], False
    elif requires:
        missing = [r for r in requires if r not in stabilized_types]
        if missing:
            return ProductionState.REQUIREMENTS_NOT_MET.value, missing, False

    return ProductionState.READY_FOR_PRODUCTION.value, [], False


def classify_execution_state(
    exec_status: str,
) -> Optional[str]:
    """Map execution status to production state.

    Args:
        exec_status: Execution status string (running, in_progress, paused)

    Returns:
        Production state value string, or None if no mapping applies
    """
    from app.domain.workflow.production_state import ProductionState

    if exec_status == "paused":
        return ProductionState.AWAITING_OPERATOR.value
    elif exec_status in ("running", "in_progress"):
        return ProductionState.IN_PRODUCTION.value
    return None


def build_production_summary(tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary counts from a list of production tracks.

    Pure aggregation: counts tracks in each production state.

    Args:
        tracks: List of track dicts, each with a 'state' key

    Returns:
        Dict with total, produced, in_production, requirements_not_met,
        ready_for_production, awaiting_operator counts
    """
    from app.domain.workflow.production_state import ProductionState

    summary = {
        "total": len(tracks),
        "produced": 0,
        "in_production": 0,
        "requirements_not_met": 0,
        "ready_for_production": 0,
        "awaiting_operator": 0,
    }

    for track in tracks:
        state = track["state"]
        if state == ProductionState.PRODUCED.value:
            summary["produced"] += 1
        elif state == ProductionState.IN_PRODUCTION.value:
            summary["in_production"] += 1
        elif state == ProductionState.REQUIREMENTS_NOT_MET.value:
            summary["requirements_not_met"] += 1
        elif state == ProductionState.READY_FOR_PRODUCTION.value:
            summary["ready_for_production"] += 1
        elif state == ProductionState.AWAITING_OPERATOR.value:
            summary["awaiting_operator"] += 1

    return summary


def determine_line_state(summary: Dict[str, Any]) -> str:
    """Determine the overall production line state from summary counts.

    Args:
        summary: Dict with in_production, awaiting_operator, produced, total counts

    Returns:
        Line state string: 'active', 'stopped', 'complete', or 'idle'
    """
    if summary["in_production"] > 0:
        return "active"
    elif summary["awaiting_operator"] > 0:
        return "stopped"
    elif summary["produced"] == summary["total"]:
        return "complete"
    else:
        return "idle"


def build_interrupts(tracks: List[Dict[str, Any]], project_id: str) -> List[Dict[str, str]]:
    """Build interrupts list from tracks that need operator attention.

    Args:
        tracks: List of track dicts
        project_id: Project identifier for URL building

    Returns:
        List of interrupt dicts with document_type and resolve_url
    """
    from app.domain.workflow.production_state import ProductionState

    interrupts = []
    for track in tracks:
        if track["state"] == ProductionState.AWAITING_OPERATOR.value:
            interrupts.append({
                "document_type": track["document_type"],
                "resolve_url": f"/projects/{project_id}/workflows/{track['document_type']}/build",
            })
    return interrupts


def build_child_track(
    doc_type_id: str,
    title: Optional[str],
    content: Dict[str, Any],
    instance_id: Optional[str],
) -> Dict[str, Any]:
    """Build a child track dict from a child document's data.

    Args:
        doc_type_id: Document type ID of the child
        title: Document title (may be None)
        content: Document content dict
        instance_id: Document instance_id

    Returns:
        Child track dict
    """
    from app.domain.workflow.production_state import ProductionState

    child_name = title or content.get("name", doc_type_id)
    return {
        "document_type": doc_type_id,
        "document_name": child_name,
        "description": content.get("intent", ""),
        "scope": doc_type_id,
        "state": ProductionState.PRODUCED.value,
        "stations": [],
        "elapsed_ms": None,
        "blocked_by": [],
        "identifier": content.get("epic_id", ""),
        "sequence": content.get("sequence"),
        "instance_id": instance_id,
    }

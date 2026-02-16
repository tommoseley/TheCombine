"""Production Line service (ADR-043).

Provides production status calculation for the Production Line UI.
Used by both the API and web routes.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.document_type import DocumentType
from app.api.models.project import Project
from app.api.models.workflow_execution import WorkflowExecution
from app.domain.workflow.production_state import ProductionState
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.plan_loader import PlanLoader

logger = logging.getLogger(__name__)


# Cache for workflow plans (avoid repeated file I/O)
_workflow_plan_cache: Dict[str, Any] = {}


def _get_workflow_plan(document_type: str):
    """Load workflow plan for a document type.
    
    Uses combine-config versioned structure.
    Returns WorkflowPlan or None if not found.
    """
    from pathlib import Path
    
    if document_type in _workflow_plan_cache:
        return _workflow_plan_cache[document_type]
    
    # Try to load from combine-config
    active_releases_path = Path("combine-config/_active/active_releases.json")
    if active_releases_path.exists():
        try:
            with open(active_releases_path) as f:
                active = json.load(f)
            version = active.get("workflows", {}).get(document_type)
            if version:
                plan_path = Path(f"combine-config/workflows/{document_type}/releases/{version}/definition.json")
                if plan_path.exists():
                    loader = PlanLoader()
                    plan = loader.load(plan_path)
                    _workflow_plan_cache[document_type] = plan
                    return plan
        except Exception as e:
            logger.warning(f"Failed to load workflow plan for {document_type}: {e}")
    
    _workflow_plan_cache[document_type] = None
    return None


def _build_station_sequence_from_workflow(
    workflow_stations: List[Dict[str, Any]],
    current_node: str,
    current_node_station_id: Optional[str],
    status: str,
    terminal_outcome: Optional[str],
    pending_user_input: bool,
) -> List[Dict[str, str]]:
    """Build station sequence from workflow-defined stations.

    Per WS-STATION-DATA-001: Stations are derived from DCW node metadata,
    not hardcoded. Multiple nodes may map to the same station.

    Args:
        workflow_stations: Station list from WorkflowPlan.get_stations()
        current_node: Current workflow node ID
        current_node_station_id: Station ID for current node (from node metadata)
        status: Execution status (running, paused, completed, failed)
        terminal_outcome: Terminal outcome if completed (stabilized, blocked)
        pending_user_input: Whether waiting for user input

    Returns:
        List of station dicts with station, label, state, needs_input
    """
    if not workflow_stations:
        # Fallback for workflows without station metadata
        return []

    stations = []
    station_order = [s["id"] for s in workflow_stations]
    current_idx = station_order.index(current_node_station_id) if current_node_station_id in station_order else -1

    # Handle completed/stabilized state
    if terminal_outcome == "stabilized" or status == "completed":
        for s in workflow_stations:
            stations.append({
                "station": s["id"],
                "label": s["label"],
                "state": "complete",
            })
        return stations

    # Handle failed/blocked state
    if terminal_outcome == "blocked" or status == "failed":
        for i, s in enumerate(workflow_stations):
            if i < current_idx:
                state = "complete"
            elif i == current_idx:
                state = "failed"
            else:
                state = "pending"
            stations.append({
                "station": s["id"],
                "label": s["label"],
                "state": state,
            })
        return stations

    # Build stations based on current position
    for i, s in enumerate(workflow_stations):
        if i < current_idx:
            state = "complete"
        elif i == current_idx:
            state = "active"
            # If pending user input at current station, mark as needs_input
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

        stations.append({
            "station": s["id"],
            "label": s["label"],
            "state": state,
        })

    return stations


def get_document_type_dependencies() -> List[Dict[str, Any]]:
    """Get document type dependencies for the production line.

    Reads from the master workflow definition (software_product_development.v1.json)
    to get all document types and their dependencies in the correct order.

    Returns list of dicts with:
    - id: document type identifier
    - name: human-readable name
    - requires: list of required document type IDs
    - scope: document scope (project, epic, feature)
    - may_own: list of entity types this document can own (for parent-child relationships)
    - collection_field: field name containing child entities (if may_own is set)
    """
    # Try to load from master workflow definition first (combine-config versioned structure)
    master_workflow_path = Path("combine-config/workflows/software_product_development/releases/1.0.0/definition.json")
    if master_workflow_path.exists():
        try:
            with open(master_workflow_path) as f:
                master = json.load(f)

            doc_types_def = master.get("document_types", {})
            entity_types_def = master.get("entity_types", {})
            steps = master.get("steps", [])

            # Build document types in step order (respecting dependencies)
            document_types = []
            seen = set()

            def extract_from_steps(step_list: List[Dict], parent_docs: List[str] = None):
                """Recursively extract document types from steps."""
                if parent_docs is None:
                    parent_docs = []

                for step in step_list:
                    # Handle nested steps (iterate_over)
                    if "steps" in step:
                        # Get inputs from this level
                        inputs = [inp.get("doc_type") for inp in step.get("inputs", []) if inp.get("doc_type")]
                        extract_from_steps(step["steps"], parent_docs + inputs)
                        continue

                    produces = step.get("produces")
                    if produces and produces not in seen:
                        seen.add(produces)
                        doc_def = doc_types_def.get(produces, {})

                        # Build requires list from step inputs
                        requires = []
                        for inp in step.get("inputs", []):
                            doc_type = inp.get("doc_type")
                            if doc_type:
                                requires.append(doc_type)

                        # Get parent-child relationship info
                        may_own = doc_def.get("may_own", [])
                        collection_field = doc_def.get("collection_field")

                        # Determine child_doc_type from entity_types
                        child_doc_type = None
                        if may_own:
                            for entity_type in may_own:
                                entity_def = entity_types_def.get(entity_type, {})
                                # The child documents have the entity type as their doc_type_id
                                child_doc_type = entity_type
                                break

                        document_types.append({
                            "id": produces,
                            "name": doc_def.get("name", produces),
                            "requires": requires,
                            "scope": doc_def.get("scope", "project"),
                            "may_own": may_own,
                            "collection_field": collection_field,
                            "child_doc_type": child_doc_type,
                        })

            extract_from_steps(steps)
            return document_types

        except Exception as e:
            logger.warning(f"Failed to load master workflow: {e}, falling back to plan registry")

    # Fallback to DIW plan registry
    registry = get_plan_registry()
    plans = registry.list_plans()

    document_types = []
    for plan in plans:
        if plan.document_type:
            document_types.append({
                "id": plan.document_type,
                "name": plan.name,
                "requires": plan.requires_inputs or [],
                "scope": "project",
            })

    # Sort by dependency depth (documents with fewer deps first)
    def dep_count(dt: Dict[str, Any]) -> int:
        return len(dt["requires"])

    document_types.sort(key=dep_count)

    return document_types


async def get_project(db: AsyncSession, project_id: str) -> Optional[Project]:
    """Load project by ID (UUID or project_id)."""
    from uuid import UUID

    try:
        project_uuid = UUID(project_id)
        result = await db.execute(select(Project).where(Project.id == project_uuid))
    except ValueError:
        result = await db.execute(select(Project).where(Project.project_id == project_id))

    return result.scalar_one_or_none()


async def get_production_tracks(db: AsyncSession, project_id: str) -> List[Dict[str, Any]]:
    """Build production tracks for a project.

    Returns list of track dicts with:
    - document_type
    - state (ProductionState value)
    - stations (list of station states)
    - elapsed_ms
    - blocked_by (if blocked)
    """
    from uuid import UUID

    # Get existing documents for this project
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        # project_id is not a UUID, need to look up the project first
        project = await get_project(db, project_id)
        if not project:
            return []
        project_uuid = project.id

    result = await db.execute(
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == project_uuid)
        .where(Document.is_latest == True)
    )
    documents = {doc.doc_type_id: doc for doc in result.scalars().all()}

    # Get active workflow executions
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.project_id == project_uuid)
        .where(WorkflowExecution.status.in_(["running", "in_progress", "paused"]))
    )
    active_executions = {ex.document_type: ex for ex in result.scalars().all()}

    tracks = []
    stabilized_types = set()

    # Add concierge_intake as the first track (it's the input source, not produced by workflow)
    concierge_track = {
        "document_type": "concierge_intake",
        "document_name": "Concierge Intake",
        "state": ProductionState.READY_FOR_PRODUCTION.value,
        "stations": [],
        "elapsed_ms": None,
        "blocked_by": [],
    }
    if "concierge_intake" in documents:
        doc = documents["concierge_intake"]
        # Document exists - consider it produced unless explicitly incomplete
        if doc.status not in ["failed", "error", "cancelled"]:
            concierge_track["state"] = ProductionState.PRODUCED.value
            stabilized_types.add("concierge_intake")
            # Show all stations as complete for produced documents
            # Load workflow plan to get station metadata
            concierge_plan = _get_workflow_plan("concierge_intake")
            if concierge_plan:
                workflow_stations = concierge_plan.get_stations()
                concierge_track["stations"] = _build_station_sequence_from_workflow(
                    workflow_stations=workflow_stations,
                    current_node="end_stabilized",
                    current_node_station_id="done",
                    status="completed",
                    terminal_outcome="stabilized",
                    pending_user_input=False,
                )
    tracks.append(concierge_track)

    # Get document types from master workflow definition
    document_types = get_document_type_dependencies()

    # Fetch document type descriptions from database
    doc_type_ids = [dt["id"] for dt in document_types] + ["concierge_intake"]
    result = await db.execute(
        select(DocumentType).where(DocumentType.doc_type_id.in_(doc_type_ids))
    )
    doc_type_descriptions = {
        dt.doc_type_id: dt.description 
        for dt in result.scalars().all()
    }

    # Update concierge_intake track with description
    if tracks and tracks[0]["document_type"] == "concierge_intake":
        tracks[0]["description"] = doc_type_descriptions.get("concierge_intake", "")

    for doc_type in document_types:
        type_id = doc_type["id"]
        requires = doc_type["requires"]
        scope = doc_type.get("scope", "project")

        # For now, only show project-scoped documents in the production line
        # Epic and story documents require entity context
        if scope != "project":
            continue

        track = {
            "document_type": type_id,
            "document_name": doc_type.get("name", type_id),
            "description": doc_type_descriptions.get(type_id, ""),
            "scope": scope,
            "state": ProductionState.READY_FOR_PRODUCTION.value,
            "station": None,
            "stations": [],
            "elapsed_ms": None,
            "blocked_by": [],
            # Parent-child relationship info from workflow definition
            "may_own": doc_type.get("may_own", []),
            "child_doc_type": doc_type.get("child_doc_type"),
            "collection_field": doc_type.get("collection_field"),
        }

        # Check if produced (document exists and not failed/cancelled)
        if type_id in documents:
            doc = documents[type_id]
            # Document exists - consider it produced unless explicitly failed
            if doc.status not in ["failed", "error", "cancelled"]:
                track["state"] = ProductionState.PRODUCED.value
                stabilized_types.add(type_id)
                # Show all stations as complete for produced documents
                workflow_plan = _get_workflow_plan(type_id)
                if workflow_plan:
                    workflow_stations = workflow_plan.get_stations()
                    track["stations"] = _build_station_sequence_from_workflow(
                        workflow_stations=workflow_stations,
                        current_node="end_stabilized",
                        current_node_station_id="done",
                        status="completed",
                        terminal_outcome="stabilized",
                        pending_user_input=False,
                    )
            else:
                track["state"] = ProductionState.READY_FOR_PRODUCTION.value

        # Check if blocked by dependencies
        elif requires:
            missing = [r for r in requires if r not in stabilized_types]
            if missing:
                track["state"] = ProductionState.REQUIREMENTS_NOT_MET.value
                track["blocked_by"] = missing

        # Check if actively running
        if type_id in active_executions:
            ex = active_executions[type_id]
            current_node = ex.current_node_id or ""

            # Map execution state to production state + station
            if ex.status == "paused":
                track["state"] = ProductionState.AWAITING_OPERATOR.value
            elif ex.status in ["running", "in_progress"]:
                track["state"] = ProductionState.IN_PRODUCTION.value


            # Build station sequence from workflow definition
            workflow_plan = _get_workflow_plan(type_id)
            if workflow_plan:
                workflow_stations = workflow_plan.get_stations()
                # Get station ID for current node
                current_station_id = None
                node_station = workflow_plan.get_node_station(current_node)
                if node_station:
                    current_station_id = node_station.id
                
                stations = _build_station_sequence_from_workflow(
                    workflow_stations=workflow_stations,
                    current_node=current_node,
                    current_node_station_id=current_station_id,
                    status=ex.status,
                    terminal_outcome=ex.terminal_outcome,
                    pending_user_input=ex.pending_user_input,
                )
                track["stations"] = stations
                track["active_station_id"] = current_station_id

        tracks.append(track)

    # Query spawned child documents for tracks with child_doc_type
    # These are data snapshots (e.g., epics spawned from implementation_plan)
    # that appear as L2 children on the production floor
    for track in tracks:
        child_doc_type = track.get("child_doc_type")
        if not child_doc_type:
            continue

        parent_doc = documents.get(track["document_type"])
        if not parent_doc:
            continue

        child_result = await db.execute(
            select(Document).where(
                Document.parent_document_id == parent_doc.id,
                Document.doc_type_id == child_doc_type,
                Document.is_latest == True,
            )
        )
        child_docs = child_result.scalars().all()

        for child_doc in child_docs:
            child_name = child_doc.title or child_doc.content.get("name", child_doc.doc_type_id)
            child_track = {
                "document_type": child_doc.doc_type_id,
                "document_name": child_name,
                "description": child_doc.content.get("intent", ""),
                "scope": child_doc.doc_type_id,  # Non-"project" so transformer groups as child
                "state": ProductionState.PRODUCED.value,
                "stations": [],
                "elapsed_ms": None,
                "blocked_by": [],
                "identifier": child_doc.content.get("epic_id", ""),
                "sequence": child_doc.content.get("sequence"),
            }
            tracks.append(child_track)

    return tracks


async def get_production_status(
    db: AsyncSession,
    project_id: str,
) -> Dict[str, Any]:
    """Get full production status for a project.

    Returns:
        Dict with project_id, line_state, tracks, interrupts, and summary.
    """
    project = await get_project(db, project_id)
    if not project:
        return {
            "project_id": project_id,
            "project_name": None,
            "line_state": "idle",
            "tracks": [],
            "interrupts": [],
            "summary": {
                "total": 0,
                "produced": 0,
                "in_production": 0,
                "requirements_not_met": 0,
                "ready_for_production": 0,
                "awaiting_operator": 0,
            },
        }

    tracks = await get_production_tracks(db, str(project.id))

    # Calculate summary
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

    # Determine line state
    if summary["in_production"] > 0:
        line_state = "active"
    elif summary["awaiting_operator"] > 0:
        line_state = "stopped"
    elif summary["produced"] == summary["total"]:
        line_state = "complete"
    else:
        line_state = "idle"

    # Build interrupts list
    interrupts = []
    for track in tracks:
        if track["state"] == ProductionState.AWAITING_OPERATOR.value:
            interrupts.append({
                "document_type": track["document_type"],
                "resolve_url": f"/projects/{project_id}/workflows/{track['document_type']}/build",
            })

    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "line_state": line_state,
        "tracks": tracks,
        "interrupts": interrupts,
        "summary": summary,
    }

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

    Delegates to production_pure.build_station_sequence for testability.
    """
    from app.api.services.production_pure import build_station_sequence

    return build_station_sequence(
        workflow_stations=workflow_stations,
        current_node_station_id=current_node_station_id,
        status=status,
        terminal_outcome=terminal_outcome,
        pending_user_input=pending_user_input,
    )


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
    from app.api.services.production_pure import (
        apply_active_execution,
        build_child_track,
        build_concierge_track,
        build_document_type_track,
    )

    # Resolve project UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        project = await get_project(db, project_id)
        if not project:
            return []
        project_uuid = project.id

    # Fetch documents and active executions
    result = await db.execute(
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == project_uuid)
        .where(Document.is_latest == True)
    )
    documents = {doc.doc_type_id: doc for doc in result.scalars().all()}

    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.project_id == project_uuid)
        .where(WorkflowExecution.status.in_(["running", "in_progress", "paused"]))
    )
    active_executions = {ex.document_type: ex for ex in result.scalars().all()}

    # Station lookup helper (wraps _get_workflow_plan)
    def _get_stations(doc_type_id: str):
        plan = _get_workflow_plan(doc_type_id)
        return plan.get_stations() if plan else None

    def _get_node_station(doc_type_id: str, node_id: str):
        plan = _get_workflow_plan(doc_type_id)
        return plan.get_node_station(node_id) if plan else None

    stabilized_types: set = set()

    # Build concierge track
    concierge_track = build_concierge_track(documents, stabilized_types, _get_stations)
    tracks = [concierge_track]

    # Get document types and descriptions
    document_types = get_document_type_dependencies()
    doc_type_ids = [dt["id"] for dt in document_types] + ["concierge_intake"]
    result = await db.execute(
        select(DocumentType).where(DocumentType.doc_type_id.in_(doc_type_ids))
    )
    doc_type_descriptions = {
        dt.doc_type_id: dt.description
        for dt in result.scalars().all()
    }

    # Update concierge track with description
    concierge_track["description"] = doc_type_descriptions.get("concierge_intake", "")

    # Build tracks for each document type
    for doc_type in document_types:
        track = build_document_type_track(
            doc_type, documents, stabilized_types, doc_type_descriptions, _get_stations,
        )
        if track is None:
            continue

        type_id = doc_type["id"]
        if type_id in active_executions:
            apply_active_execution(
                track, active_executions[type_id], _get_stations, _get_node_station,
            )

        tracks.append(track)

    # Query spawned child documents
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
        for child_doc in child_result.scalars().all():
            tracks.append(build_child_track(
                doc_type_id=child_doc.doc_type_id,
                title=child_doc.title,
                content=child_doc.content,
                display_id=child_doc.display_id,
            ))

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

    from app.api.services.production_pure import (
        build_interrupts,
        build_production_summary,
        determine_line_state,
    )

    tracks = await get_production_tracks(db, str(project.id))

    summary = build_production_summary(tracks)
    line_state = determine_line_state(summary)
    interrupts = build_interrupts(tracks, project_id)

    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "line_state": line_state,
        "tracks": tracks,
        "interrupts": interrupts,
        "summary": summary,
    }

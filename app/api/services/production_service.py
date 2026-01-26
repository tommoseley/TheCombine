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
from app.api.models.project import Project
from app.api.models.workflow_execution import WorkflowExecution
from app.domain.workflow.production_state import ProductionState
from app.domain.workflow.plan_registry import get_plan_registry

logger = logging.getLogger(__name__)


def get_document_type_dependencies() -> List[Dict[str, Any]]:
    """Get document type dependencies for the production line.

    Reads from the master workflow definition (software_product_development.v1.json)
    to get all document types and their dependencies in the correct order.

    Returns list of dicts with:
    - id: document type identifier
    - name: human-readable name
    - requires: list of required document type IDs
    - scope: document scope (project, epic, story)
    """
    # Try to load from master workflow definition first
    master_workflow_path = Path("seed/workflows/software_product_development.v1.json")
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

                        document_types.append({
                            "id": produces,
                            "name": doc_def.get("name", produces),
                            "requires": requires,
                            "scope": doc_def.get("scope", "project"),
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

    # Get document types from master workflow definition
    document_types = get_document_type_dependencies()

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
            "state": ProductionState.QUEUED.value,
            "stations": [],
            "elapsed_ms": None,
            "blocked_by": [],
        }

        # Check if stabilized (document exists)
        if type_id in documents:
            doc = documents[type_id]
            if doc.status in ["stabilized", "complete", "success", "active"]:
                track["state"] = ProductionState.STABILIZED.value
                stabilized_types.add(type_id)
            else:
                track["state"] = ProductionState.QUEUED.value

        # Check if blocked by dependencies
        elif requires:
            missing = [r for r in requires if r not in stabilized_types]
            if missing:
                track["state"] = ProductionState.BLOCKED.value
                track["blocked_by"] = missing

        # Check if actively running
        if type_id in active_executions:
            ex = active_executions[type_id]
            current_node = ex.current_node_id or ""

            # Map execution state to production state
            if ex.status == "paused":
                track["state"] = ProductionState.AWAITING_OPERATOR.value
            elif ex.status in ["running", "in_progress"]:
                if "qa" in current_node.lower():
                    track["state"] = ProductionState.AUDITING.value
                elif "remediat" in current_node.lower():
                    track["state"] = ProductionState.REMEDIATING.value
                elif "pgc" in current_node.lower():
                    track["state"] = ProductionState.BINDING.value
                else:
                    track["state"] = ProductionState.ASSEMBLING.value

            # Build station sequence from execution_log
            execution_log = ex.execution_log or []
            stations = []
            for node_exec in execution_log[-6:]:  # Last 6 nodes
                node_id = node_exec.get("node_id", "")
                outcome = node_exec.get("outcome", "")

                station = {"station": "asm", "state": "pending"}
                if "pgc" in node_id.lower():
                    station["station"] = "bind"
                elif "qa" in node_id.lower():
                    station["station"] = "aud"
                elif "remediat" in node_id.lower():
                    station["station"] = "rem"

                if outcome == "success":
                    station["state"] = "complete"
                elif outcome == "failed":
                    station["state"] = "failed"
                elif node_id == current_node:
                    station["state"] = "active"

                stations.append(station)

            track["stations"] = stations

        tracks.append(track)

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
                "stabilized": 0,
                "active": 0,
                "blocked": 0,
                "queued": 0,
                "awaiting_operator": 0,
            },
        }

    tracks = await get_production_tracks(db, str(project.id))

    # Calculate summary
    summary = {
        "total": len(tracks),
        "stabilized": 0,
        "active": 0,
        "blocked": 0,
        "queued": 0,
        "awaiting_operator": 0,
    }

    for track in tracks:
        state = track["state"]
        if state == ProductionState.STABILIZED.value:
            summary["stabilized"] += 1
        elif state in [
            ProductionState.ASSEMBLING.value,
            ProductionState.AUDITING.value,
            ProductionState.BINDING.value,
            ProductionState.REMEDIATING.value,
        ]:
            summary["active"] += 1
        elif state == ProductionState.BLOCKED.value:
            summary["blocked"] += 1
        elif state == ProductionState.QUEUED.value:
            summary["queued"] += 1
        elif state == ProductionState.AWAITING_OPERATOR.value:
            summary["awaiting_operator"] += 1

    # Determine line state
    if summary["active"] > 0:
        line_state = "active"
    elif summary["awaiting_operator"] > 0:
        line_state = "stopped"
    elif summary["stabilized"] == summary["total"]:
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

"""SSE event emission for workflow execution.

Extracted from PlanExecutor (WS-CRAP decomposition).
Decouples station/phase event publishing from core orchestration.
"""

import logging
from typing import Dict, List, Optional

from app.domain.workflow.document_workflow_state import DocumentWorkflowState
from app.domain.workflow.plan_models import Node, WorkflowPlan

# Domain event bus — no API layer import
from app.domain.events import publish_event

logger = logging.getLogger(__name__)


async def emit_stations_declared(
    plan: WorkflowPlan,
    state: DocumentWorkflowState,
) -> None:
    """Emit stations_declared event on workflow start.

    Broadcasts the full station list for this workflow so UI can
    render station dots immediately, including phases (sub-steps) per station.

    Args:
        plan: The workflow plan (contains station metadata)
        state: The workflow state (for project_id, execution_id)
    """
    try:
        stations = plan.get_stations()
        if not stations:
            logger.debug(f"No stations defined in plan {plan.workflow_id}")
            return

        # Collect phases (internals) per station
        phases_by_station: Dict[str, List[str]] = {}
        for node in plan.nodes:
            if node.station and node.internals:
                station_id = node.station.id
                if station_id not in phases_by_station:
                    phases_by_station[station_id] = []
                # Add internal keys as phases (preserves dict order from Python 3.7+)
                for phase_key in node.internals.keys():
                    if phase_key not in phases_by_station[station_id]:
                        phases_by_station[station_id].append(phase_key)

        # All stations start as pending, include phases if any
        station_data = [
            {
                "id": s["id"],
                "label": s["label"],
                "order": s["order"],
                "state": "pending",
                "phases": phases_by_station.get(s["id"], []),
            }
            for s in stations
        ]

        await publish_event(
            state.project_id,
            "stations_declared",
            {
                "document_type": state.document_type,
                "execution_id": state.execution_id,
                "stations": station_data,
            },
        )
        logger.debug(
            f"Emitted stations_declared for {state.document_type}: "
            f"{[s['id'] for s in station_data]}"
        )
    except Exception as e:
        logger.warning(f"Failed to emit stations_declared: {e}")


async def emit_station_changed(
    plan: WorkflowPlan,
    state: DocumentWorkflowState,
    node_id: str,
    station_state: str,
    phase: Optional[str] = None,
) -> None:
    """Emit station_changed event when station state changes.

    Args:
        plan: The workflow plan
        state: The workflow state
        node_id: The node causing the change
        station_state: New station state (pending, active, complete, blocked)
        phase: Optional sub-phase (pass_a, entry, merge, etc.)
    """
    try:
        station = plan.get_node_station(node_id)
        if not station:
            logger.debug(f"No station for node {node_id}")
            return

        data = {
            "document_type": state.document_type,
            "execution_id": state.execution_id,
            "station_id": station.id,
            "state": station_state,
        }
        if phase:
            data["phase"] = phase

        await publish_event(state.project_id, "station_changed", data)
        logger.debug(
            f"Emitted station_changed: {station.id} -> {station_state}"
            f"{f' (phase: {phase})' if phase else ''}"
        )
    except Exception as e:
        logger.warning(f"Failed to emit station_changed: {e}")


async def emit_internal_step(
    plan: WorkflowPlan,
    state: DocumentWorkflowState,
    node: Node,
    phase_key: str,
) -> None:
    """Emit internal_step event when entering an internal phase.

    Broadcasts detailed step information for UI display:
    - Station context
    - Internal step details (key, name, type)
    - Progress (step number, total steps)

    Args:
        plan: The workflow plan
        state: The workflow state
        node: The node being executed
        phase_key: The internal phase key (e.g., 'pass_a', 'entry', 'merge')
    """
    try:
        station = plan.get_node_station(node.node_id)
        if not station or not node.internals:
            return

        # Get internal details
        internal = node.internals.get(phase_key, {})
        internal_name = internal.get("name", phase_key)
        internal_type = internal.get("internal_type", "UNKNOWN")

        # Calculate step position
        internal_keys = list(node.internals.keys())
        step_number = internal_keys.index(phase_key) + 1 if phase_key in internal_keys else 1
        total_steps = len(internal_keys)

        data = {
            "document_type": state.document_type,
            "execution_id": state.execution_id,
            "station_id": station.id,
            "node_id": node.node_id,
            "step": {
                "key": phase_key,
                "name": internal_name,
                "type": internal_type,
                "number": step_number,
                "total": total_steps,
            },
        }

        await publish_event(state.project_id, "internal_step", data)
        logger.debug(
            f"Emitted internal_step: {station.id}.{phase_key} "
            f"({step_number}/{total_steps}: {internal_name})"
        )
    except Exception as e:
        logger.warning(f"Failed to emit internal_step: {e}")

"""
Spawner Handler - creates new POW executions with lineage tracking.

Per ADR-048, the spawner creates a new POW execution and returns a
spawn_receipt documenting the lineage relationship.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.api.services.mech_handlers.base import (
    MechHandler,
    MechResult,
    ExecutionContext,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def build_lineage(
    lineage_config: dict,
    parent_execution_id: str,
    spawning_operation_id: str,
) -> dict:
    """Build lineage dict from config and parent context.

    Pure function — no I/O, no side effects.

    Args:
        lineage_config: Lineage configuration dict
        parent_execution_id: Parent execution ID
        spawning_operation_id: Spawning operation ID

    Returns:
        Lineage dict for spawn receipt
    """
    return {
        "spawned_from_execution_id": parent_execution_id
        if lineage_config.get("set_spawned_from_execution_id", True)
        else None,
        "spawned_by_operation_id": spawning_operation_id
        if lineage_config.get("set_spawned_by_operation_id", True)
        else None,
        "spawned_by_step_name": "Spawn Follow-on POW",
    }


def collect_seed_inputs(
    seed_inputs_config: list,
    available_input_keys: set,
) -> list:
    """Collect seed inputs from config, filtering by available inputs.

    Pure function — no I/O, no side effects.

    Args:
        seed_inputs_config: List of seed input config dicts
        available_input_keys: Set of available input reference keys

    Returns:
        List of seed input dicts with name and artifact_id
    """
    seed_inputs = []
    for seed_input in seed_inputs_config:
        artifact_id = seed_input.get("from_artifact_id")
        name = seed_input.get("name", artifact_id)

        if artifact_id and artifact_id in available_input_keys:
            seed_inputs.append({
                "name": name,
                "artifact_id": artifact_id,
            })
    return seed_inputs


def assemble_spawn_receipt(
    next_pow_ref: str,
    child_execution_id: str,
    lineage: dict,
    seed_inputs: list,
    project_id: str = None,
    write_project_event: bool = False,
    spawned_at: str = None,
) -> dict:
    """Assemble a spawn receipt dict.

    Pure function — no I/O, no side effects.

    Args:
        next_pow_ref: POW reference to spawn
        child_execution_id: Generated child execution ID
        lineage: Lineage dict from build_lineage()
        seed_inputs: Seed inputs list from collect_seed_inputs()
        project_id: Optional project ID
        write_project_event: Whether project event was written
        spawned_at: ISO timestamp (generated if not provided)

    Returns:
        Spawn receipt dict
    """
    return {
        "schema_version": "spawn_receipt.v1",
        "spawned_at": spawned_at or datetime.now(timezone.utc).isoformat(),
        "child_execution_id": child_execution_id,
        "child_pow_ref": next_pow_ref,
        "lineage": lineage,
        "seed_inputs": seed_inputs,
        "project_id": project_id,
        "project_event_written": write_project_event,
    }


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------

@register_handler
class SpawnerHandler(MechHandler):
    """Handler for spawner operations.

    Creates a new POW execution based on routing_decision and seeds it
    with artifacts from the parent execution. Returns a spawn_receipt
    with lineage pointers.
    """

    operation_type = "spawner"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute the spawn operation."""
        try:
            routing_decision = None
            if context.has_input("routing_decision"):
                routing_decision = context.get_input("routing_decision")

            if not routing_decision:
                return MechResult.fail(
                    error="No routing_decision in context",
                    error_code="input_missing",
                )

            if not isinstance(routing_decision, dict):
                return MechResult.fail(
                    error=f"routing_decision must be dict, got {type(routing_decision).__name__}",
                    error_code="invalid_input_type",
                )

            decision = routing_decision.get("decision", {})
            next_pow_ref = decision.get("next_pow_ref")

            if not next_pow_ref:
                return MechResult.fail(
                    error="routing_decision.decision.next_pow_ref is required",
                    error_code="missing_pow_ref",
                )

            child_execution_id = f"exec_{uuid.uuid4().hex[:12]}"
            parent_execution_id = context.workflow_id or "unknown"
            spawning_operation_id = context.node_id or "spawn_pow"

            # Collect available input keys for seed_inputs filtering
            available_keys = set(context.inputs.keys()) | set(context.node_outputs.keys())
            seed_inputs = collect_seed_inputs(
                config.get("seed_inputs", []),
                available_keys,
            )

            lineage = build_lineage(
                config.get("lineage", {}),
                parent_execution_id,
                spawning_operation_id,
            )

            project_id = None
            if context.has_input("project_id"):
                project_id = context.get_input("project_id")

            spawn_receipt = assemble_spawn_receipt(
                next_pow_ref=next_pow_ref,
                child_execution_id=child_execution_id,
                lineage=lineage,
                seed_inputs=seed_inputs,
                project_id=project_id,
                write_project_event=config.get("write_project_event", False),
            )

            logger.info(
                f"Spawner: created spawn_receipt for {next_pow_ref} "
                f"(child={child_execution_id}, parent={parent_execution_id})"
            )

            return MechResult.ok(output=spawn_receipt)

        except Exception as e:
            logger.exception(f"Spawner failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="spawn_error",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate spawner configuration."""
        errors = []

        seed_inputs = config.get("seed_inputs")
        if seed_inputs and not isinstance(seed_inputs, list):
            errors.append("seed_inputs must be a list")

        lineage = config.get("lineage")
        if lineage and not isinstance(lineage, dict):
            errors.append("lineage must be an object")

        return errors

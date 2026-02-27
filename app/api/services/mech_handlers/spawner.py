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


@register_handler
class SpawnerHandler(MechHandler):
    """
    Handler for spawner operations.

    Creates a new POW execution based on routing_decision and seeds it
    with artifacts from the parent execution. Returns a spawn_receipt
    with lineage pointers.

    Config:
        seed_inputs: List of artifacts to pass to spawned POW
        write_project_event: Whether to write a project event
        return_child_execution_id: Whether to include child ID in receipt
        lineage: Lineage configuration
            set_spawned_from_execution_id: Store parent execution ID
            set_spawned_by_operation_id: Store spawning operation ID

    Example config:
        seed_inputs:
          - name: intake_record
            from_artifact_id: intake_record
        lineage:
          set_spawned_from_execution_id: true
          set_spawned_by_operation_id: true
    """

    operation_type = "spawner"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """
        Execute the spawn operation.

        Args:
            config: Spawner configuration
            context: Execution context with routing_decision and artifacts

        Returns:
            MechResult with spawn_receipt
        """
        try:
            # Get routing decision to determine which POW to spawn
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

            # Extract the POW to spawn
            decision = routing_decision.get("decision", {})
            next_pow_ref = decision.get("next_pow_ref")

            if not next_pow_ref:
                return MechResult.fail(
                    error="routing_decision.decision.next_pow_ref is required",
                    error_code="missing_pow_ref",
                )

            # Generate child execution ID
            child_execution_id = f"exec_{uuid.uuid4().hex[:12]}"

            # Get parent execution context
            parent_execution_id = context.workflow_id or "unknown"
            spawning_operation_id = context.node_id or "spawn_pow"

            # Collect seed inputs
            seed_inputs_config = config.get("seed_inputs", [])
            seed_inputs = []

            for seed_input in seed_inputs_config:
                artifact_id = seed_input.get("from_artifact_id")
                name = seed_input.get("name", artifact_id)

                if artifact_id and context.has_input(artifact_id):
                    seed_inputs.append({
                        "name": name,
                        "artifact_id": artifact_id,
                    })

            # Build lineage
            lineage_config = config.get("lineage", {})
            lineage = {
                "spawned_from_execution_id": parent_execution_id
                if lineage_config.get("set_spawned_from_execution_id", True)
                else None,
                "spawned_by_operation_id": spawning_operation_id
                if lineage_config.get("set_spawned_by_operation_id", True)
                else None,
                "spawned_by_step_name": "Spawn Follow-on POW",
            }

            # Get project ID if available
            project_id = None
            if context.has_input("project_id"):
                project_id = context.get_input("project_id")

            # Build spawn receipt
            spawn_receipt = {
                "schema_version": "spawn_receipt.v1",
                "spawned_at": datetime.now(timezone.utc).isoformat(),
                "child_execution_id": child_execution_id,
                "child_pow_ref": next_pow_ref,
                "lineage": lineage,
                "seed_inputs": seed_inputs,
                "project_id": project_id,
                "project_event_written": config.get("write_project_event", False),
            }

            logger.info(
                f"Spawner: created spawn_receipt for {next_pow_ref} "
                f"(child={child_execution_id}, parent={parent_execution_id})"
            )

            # Note: Actual POW execution creation is delegated to the workflow
            # engine layer. This handler produces the spawn_receipt which
            # documents the intent. The engine will use this to create the
            # child execution with proper lineage.

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

"""
Mechanical Operation Executor.

Provides the unified entry point for executing mechanical operations.
This is the glue between operation definitions (YAML) and handlers (Python).
"""

import logging
from typing import Any, Dict, Optional

from app.api.services.mech_handlers.base import (
    ExecutionContext,
    MechResult,
)
from app.api.services.mech_handlers.registry import get_handler

logger = logging.getLogger(__name__)


async def execute_operation(
    operation: Dict[str, Any],
    inputs: Dict[str, Any],
    workflow_id: Optional[str] = None,
    node_id: Optional[str] = None,
) -> MechResult:
    """
    Execute a mechanical operation.

    This is the main entry point for running mechanical operations.
    It looks up the appropriate handler based on operation type and
    dispatches execution.

    Args:
        operation: The operation definition (loaded from YAML)
            Must contain 'type' and 'config' keys
        inputs: Input data keyed by reference name
            e.g., {"source_document": {...}, "qa_result": {...}}
        workflow_id: Optional workflow ID for context
        node_id: Optional node ID for context

    Returns:
        MechResult with output or error

    Example:
        >>> operation = {
        ...     "id": "intake_context_extractor",
        ...     "type": "extractor",
        ...     "config": {
        ...         "field_paths": [
        ...             {"path": "$.summary", "as": "summary"}
        ...         ]
        ...     }
        ... }
        >>> inputs = {"source_document": {"summary": "Build a widget"}}
        >>> result = await execute_operation(operation, inputs)
        >>> result.output
        {"summary": "Build a widget"}
    """
    op_type = operation.get("type")
    op_id = operation.get("id", "unknown")
    config = operation.get("config", {})

    if not op_type:
        return MechResult.fail(
            error=f"Operation {op_id} has no type",
            error_code="config_error",
        )

    # Get the handler for this operation type
    handler = get_handler(op_type)
    if not handler:
        return MechResult.fail(
            error=f"No handler registered for type '{op_type}'",
            error_code="handler_not_found",
        )

    # Build execution context
    context = ExecutionContext(
        inputs=inputs,
        workflow_id=workflow_id,
        node_id=node_id,
    )

    # Add op_id to config so handlers can access it
    config_with_id = {**config, "op_id": op_id}

    logger.info(f"Executing operation {op_id} (type={op_type})")

    try:
        result = await handler.execute(config_with_id, context)
        logger.info(f"Operation {op_id} completed: success={result.success}, outcome={result.outcome}")
        return result
    except Exception as e:
        logger.exception(f"Operation {op_id} failed with exception: {e}")
        return MechResult.fail(
            error=str(e),
            error_code="execution_error",
        )


async def execute_operation_by_ref(
    op_ref: str,
    inputs: Dict[str, Any],
    ops_service: Any,  # MechanicalOpsService
    workflow_id: Optional[str] = None,
    node_id: Optional[str] = None,
) -> MechResult:
    """
    Execute a mechanical operation by reference string.

    Parses the op_ref, loads the operation from the service,
    and executes it.

    Args:
        op_ref: Operation reference in format "mech:{type}:{op_id}:{version}"
        inputs: Input data keyed by reference name
        ops_service: MechanicalOpsService instance for loading operations
        workflow_id: Optional workflow ID for context
        node_id: Optional node ID for context

    Returns:
        MechResult with output or error

    Example:
        >>> result = await execute_operation_by_ref(
        ...     "mech:extractor:intake_context_extractor:1.0.0",
        ...     {"source_document": intake_doc},
        ...     ops_service
        ... )
    """
    # Parse op_ref: mech:{type}:{op_id}:{version}
    parts = op_ref.split(":")
    if len(parts) < 4 or parts[0] != "mech":
        return MechResult.fail(
            error=f"Invalid op_ref format: {op_ref}",
            error_code="config_error",
        )

    op_type, op_id, version = parts[1], parts[2], parts[3]

    # Load operation from service
    try:
        operation = await ops_service.get_operation(op_id, version)
        if not operation:
            return MechResult.fail(
                error=f"Operation not found: {op_id}@{version}",
                error_code="not_found",
            )
    except Exception as e:
        return MechResult.fail(
            error=f"Failed to load operation {op_id}: {e}",
            error_code="load_error",
        )

    # Execute
    return await execute_operation(
        operation=operation,
        inputs=inputs,
        workflow_id=workflow_id,
        node_id=node_id,
    )

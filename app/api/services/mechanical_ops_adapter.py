"""
Adapters that bridge API-layer mechanical operations to domain-level protocols.

These adapters satisfy the protocols defined in app.domain.workflow.operations,
allowing domain code to use mechanical operations without importing API-layer code.

Created by WS-CLEANUP-003 to fix domain/API boundary leakage.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.api.services.mechanical_ops_service import MechanicalOpsService
from app.api.services.mech_handlers import execute_operation as _execute_operation
from app.api.services.mech_handlers.base import MechResult
from app.api.services.mech_handlers.exclusion_filter import (
    apply_exclusion_filter as _apply_exclusion_filter,
)
from app.domain.workflow.operations import OperationResult


class MechanicalOpsProviderAdapter:
    """Adapts MechanicalOpsService to the OperationProvider protocol."""

    def __init__(self, service: Optional[MechanicalOpsService] = None):
        self._service = service or MechanicalOpsService()

    def get_operation(
        self,
        op_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a mechanical operation instance by ID."""
        return self._service.get_operation(op_id, version)

    def get_operation_by_ref(
        self,
        op_ref: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a mechanical operation by reference string.

        Parses op_ref format 'mech:{type}:{op_id}:{version}' and loads via service.
        """
        parts = op_ref.split(":")
        if len(parts) < 4 or parts[0] != "mech":
            return None

        op_id, version = parts[2], parts[3]
        try:
            return self._service.get_operation(op_id, version)
        except Exception:
            return None


class MechanicalOpsExecutorAdapter:
    """Adapts execute_operation to the OperationExecutor protocol."""

    async def execute(
        self,
        operation: Dict[str, Any],
        inputs: Dict[str, Any],
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> OperationResult:
        """Execute a mechanical operation, returning a domain OperationResult."""
        mech_result: MechResult = await _execute_operation(
            operation=operation,
            inputs=inputs,
            workflow_id=workflow_id,
            node_id=node_id,
        )
        return OperationResult(
            success=mech_result.success,
            output=mech_result.output,
            error=mech_result.error,
            outcome=mech_result.outcome,
            error_code=mech_result.error_code,
            entry_config=mech_result.entry_config,
        )


class ExclusionFilterAdapter:
    """Adapts apply_exclusion_filter to the ExclusionFilter protocol."""

    def apply(
        self,
        document: Dict[str, Any],
        invariants: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], int]:
        """Apply exclusion filtering to a document."""
        return _apply_exclusion_filter(document, invariants)


def create_default_operation_provider() -> MechanicalOpsProviderAdapter:
    """Create the default OperationProvider adapter."""
    return MechanicalOpsProviderAdapter()


def create_default_operation_executor() -> MechanicalOpsExecutorAdapter:
    """Create the default OperationExecutor adapter."""
    return MechanicalOpsExecutorAdapter()


def create_default_exclusion_filter() -> ExclusionFilterAdapter:
    """Create the default ExclusionFilter adapter."""
    return ExclusionFilterAdapter()

"""
Domain-level protocols for mechanical operations.

These protocols define the interface that domain workflow code uses to interact
with mechanical operations, without depending on the API layer implementation.
The API layer provides adapter implementations that satisfy these protocols.

Created by WS-CLEANUP-003 to fix domain/API boundary leakage.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple


@dataclass
class OperationResult:
    """Result of a mechanical operation execution.

    Domain-owned result type that mirrors the essential fields from MechResult
    without creating a dependency on the API layer.
    """
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    outcome: str = "success"
    error_code: Optional[str] = None
    entry_config: Optional[Dict[str, Any]] = None


class OperationProvider(Protocol):
    """Protocol for fetching mechanical operation definitions.

    Implementations load operation YAML configs from combine-config/
    and return them as dicts suitable for execution.
    """

    def get_operation(
        self,
        op_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a mechanical operation instance by ID.

        Args:
            op_id: Operation identifier (e.g. 'pgc_clarification_processor')
            version: Specific version or None for active version

        Returns:
            Full operation definition dict with type, config, etc.

        Raises:
            Exception if operation not found.
        """
        ...

    def get_operation_by_ref(
        self,
        op_ref: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a mechanical operation by reference string.

        Args:
            op_ref: Reference in format 'mech:{type}:{op_id}:{version}'

        Returns:
            Operation definition dict, or None if not found.
        """
        ...


class OperationExecutor(Protocol):
    """Protocol for executing mechanical operations.

    Implementations dispatch to the appropriate handler based on
    operation type and return results.
    """

    async def execute(
        self,
        operation: Dict[str, Any],
        inputs: Dict[str, Any],
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> OperationResult:
        """Execute a mechanical operation.

        Args:
            operation: Operation definition dict (from OperationProvider)
            inputs: Input data keyed by reference name
            workflow_id: Optional workflow ID for context
            node_id: Optional node ID for context

        Returns:
            OperationResult with output or error
        """
        ...


class ExclusionFilter(Protocol):
    """Protocol for filtering excluded topics from documents.

    Pure function interface — no I/O, no side effects.
    """

    def apply(
        self,
        document: Dict[str, Any],
        invariants: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], int]:
        """Filter excluded topics from a document.

        Args:
            document: Document dict to filter
            invariants: List of invariant dicts

        Returns:
            Tuple of (filtered_document, removed_count)
        """
        ...


# ---------------------------------------------------------------------------
# Default factory registry
#
# The API layer registers factory functions at startup via
# register_default_factories(). Domain code calls get_default_*()
# to obtain implementations without importing the API layer.
# ---------------------------------------------------------------------------

import logging as _logging

_log = _logging.getLogger(__name__)

_default_provider_factory: Optional["Callable[[], OperationProvider]"] = None
_default_executor_factory: Optional["Callable[[], OperationExecutor]"] = None
_default_filter_factory: Optional["Callable[[], ExclusionFilter]"] = None


def register_default_factories(
    provider_factory: "Callable[[], OperationProvider]",
    executor_factory: "Callable[[], OperationExecutor]",
    filter_factory: "Callable[[], ExclusionFilter]",
) -> None:
    """Register default factory functions (called by API layer at startup)."""
    global _default_provider_factory, _default_executor_factory, _default_filter_factory
    _default_provider_factory = provider_factory
    _default_executor_factory = executor_factory
    _default_filter_factory = filter_factory
    _log.info("Operation default factories registered")


def get_default_provider() -> Optional["OperationProvider"]:
    """Get the default OperationProvider, or None if not registered."""
    return _default_provider_factory() if _default_provider_factory else None


def get_default_executor() -> Optional["OperationExecutor"]:
    """Get the default OperationExecutor, or None if not registered."""
    return _default_executor_factory() if _default_executor_factory else None


def get_default_filter() -> Optional["ExclusionFilter"]:
    """Get the default ExclusionFilter, or None if not registered."""
    return _default_filter_factory() if _default_filter_factory else None

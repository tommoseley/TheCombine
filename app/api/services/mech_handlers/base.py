"""
Base classes for Mechanical Operation handlers.

Per ADR-047, mechanical operations are deterministic data transformations
that execute without LLM invocation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class MechHandlerError(Exception):
    """Base exception for mechanical handler errors."""
    pass


class InputMissingError(MechHandlerError):
    """Required input not available in context."""
    pass


class SchemaViolationError(MechHandlerError):
    """Output doesn't match declared schema."""
    pass


class TransformError(MechHandlerError):
    """Transformation logic failed."""
    pass


class RoutingUnmatchedError(MechHandlerError):
    """Selector found no matching route and no default."""
    pass


@dataclass
class ExecutionContext:
    """
    Context for mechanical operation execution.

    Provides access to inputs, prior outputs, and workflow state.
    """
    # Input documents/data keyed by reference name
    inputs: Dict[str, Any] = field(default_factory=dict)

    # Prior node outputs keyed by node_id
    node_outputs: Dict[str, Any] = field(default_factory=dict)

    # Workflow-level metadata
    workflow_id: Optional[str] = None
    node_id: Optional[str] = None

    def get_input(self, ref: str) -> Any:
        """
        Get an input by reference.

        Args:
            ref: Input reference name

        Returns:
            Input value

        Raises:
            InputMissingError: If input not found
        """
        if ref in self.inputs:
            return self.inputs[ref]
        if ref in self.node_outputs:
            return self.node_outputs[ref]
        raise InputMissingError(f"Input not found: {ref}")

    def has_input(self, ref: str) -> bool:
        """Check if an input exists."""
        return ref in self.inputs or ref in self.node_outputs


@dataclass
class MechResult:
    """
    Result of a mechanical operation execution.

    Attributes:
        success: Whether the operation succeeded
        output: The output data (if successful)
        error: Error message (if failed)
        outcome: Outcome name for edge routing
        error_code: Machine-readable error code
        entry_config: Configuration for Entry operations (UI must handle)
    """
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    outcome: str = "success"
    error_code: Optional[str] = None
    entry_config: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls, output: Dict[str, Any], outcome: str = "success") -> "MechResult":
        """Create a successful result."""
        return cls(success=True, output=output, outcome=outcome)

    @classmethod
    def fail(
        cls,
        error: str,
        outcome: str = "failed",
        error_code: Optional[str] = None,
    ) -> "MechResult":
        """Create a failed result."""
        return cls(
            success=False,
            error=error,
            outcome=outcome,
            error_code=error_code,
        )

    @classmethod
    def pending_entry(
        cls,
        op_id: str,
        renders: Any,
        captures_schema: str,
        entry_prompt: Optional[str] = None,
        layout: str = "form",
        ui_hints: Optional[Dict[str, Any]] = None,
        merge_strategy: Optional[Dict[str, Any]] = None,
        renders_schema: Optional[str] = None,
    ) -> "MechResult":
        """
        Create a pending entry result for Entry operations.

        Entry operations don't execute server-side; they return this
        result to indicate the UI must capture operator input.

        Args:
            op_id: Operation identifier
            renders: Data to render to the operator
            captures_schema: Schema ref for operator input
            entry_prompt: Prompt text for the operator
            layout: UI layout (form, wizard, review)
            ui_hints: Additional hints for frontend rendering
            merge_strategy: How to merge captured data into existing artifacts
            renders_schema: Schema ref for the rendered data
        """
        entry_config = {
            "op_id": op_id,
            "renders": renders,
            "captures_schema": captures_schema,
            "entry_prompt": entry_prompt,
            "layout": layout,
        }
        if renders_schema:
            entry_config["renders_schema"] = renders_schema
        if ui_hints:
            entry_config["ui_hints"] = ui_hints
        if merge_strategy:
            entry_config["merge_strategy"] = merge_strategy

        return cls(
            success=True,
            output=None,
            outcome="pending_entry",
            entry_config=entry_config,
        )


class MechHandler(ABC):
    """
    Abstract base class for mechanical operation handlers.

    Each operation type (extractor, merger, validator, etc.) has a
    corresponding handler that implements the execute method.
    """

    # Operation type this handler handles
    operation_type: str = "unknown"

    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """
        Execute the mechanical operation.

        Args:
            config: Operation configuration from operation.yaml
            context: Execution context with inputs and state

        Returns:
            MechResult with output or error
        """
        pass

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate operation configuration.

        Override in subclasses to add validation.

        Args:
            config: Operation configuration

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

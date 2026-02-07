"""
Entry operation handler.

Per ADR-047 Addendum A, Entry operations capture structured operator input
via UI components. They don't execute server-side; instead, they return
a 'pending_entry' result indicating the frontend must handle the input.
"""

from typing import Any, Dict, List

from app.api.services.mech_handlers.base import (
    ExecutionContext,
    MechHandler,
    MechResult,
)
from app.api.services.mech_handlers.registry import register_handler


@register_handler
class EntryHandler(MechHandler):
    """
    Handler for Entry operations.

    Entry operations are unique: they don't perform server-side work.
    Instead, they signal to the workflow executor that operator input
    is required, and provide the configuration for the UI to render.

    The workflow execution pauses until the operator submits a response,
    which is then validated and used to resume the workflow.
    """

    operation_type = "entry"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """
        'Execute' an Entry operation.

        This doesn't perform actual work - it returns a pending_entry
        result that tells the frontend to render an Entry component.

        Args:
            config: Operation configuration with renders, captures, etc.
            context: Execution context (may contain data for renders)

        Returns:
            MechResult with pending_entry outcome and entry_config
        """
        # Extract Entry-specific config
        renders_schema = config.get("renders", "")
        captures_schema = config.get("captures", "")
        entry_prompt = config.get("entry_prompt", "")
        layout = config.get("layout", "form")

        # Get the context data to render (if available)
        # The 'context' input is what gets displayed to the operator
        renders_data = None
        if context.has_input("context"):
            renders_data = context.get_input("context")

        return MechResult.pending_entry(
            op_id=config.get("op_id", "unknown"),
            renders=renders_data,
            captures_schema=captures_schema,
            entry_prompt=entry_prompt,
            layout=layout,
        )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate Entry operation configuration.

        Args:
            config: Operation configuration

        Returns:
            List of validation error messages
        """
        errors = []

        if not config.get("renders"):
            errors.append("Entry operation requires 'renders' config")

        if not config.get("captures"):
            errors.append("Entry operation requires 'captures' config")

        layout = config.get("layout", "form")
        if layout not in ("form", "wizard", "review"):
            errors.append(f"Invalid layout '{layout}'; must be form, wizard, or review")

        return errors

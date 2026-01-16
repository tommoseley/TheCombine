"""End node executor for Document Interaction Workflow Plans (ADR-039).

End nodes record terminal outcomes and close the workflow.
"""

import logging
from typing import Any, Dict

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)

logger = logging.getLogger(__name__)


class EndNodeExecutor(NodeExecutor):
    """Executor for end nodes.

    End nodes:
    - Record the terminal outcome (stabilized, blocked, abandoned)
    - Finalize the workflow execution
    - Do not produce documents or require user input

    BOUNDARY CONSTRAINTS:
    - Returns the terminal_outcome configured on the node
    - Does NOT make decisions - simply reports the configured outcome
    """

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "end"

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute an end node.

        Args:
            node_id: The end node ID
            node_config: Node configuration with terminal_outcome, gate_outcome
            context: Workflow context (final state)
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with the terminal outcome
        """
        terminal_outcome = node_config.get("terminal_outcome")
        gate_outcome = node_config.get("gate_outcome")

        if not terminal_outcome:
            logger.error(f"End node {node_id} missing terminal_outcome")
            return NodeResult.failed(
                reason=f"End node {node_id} missing terminal_outcome configuration"
            )

        logger.info(
            f"End node {node_id} reached: terminal={terminal_outcome}, "
            f"gate={gate_outcome}"
        )

        # Build final metadata
        metadata = {
            "node_id": node_id,
            "terminal_outcome": terminal_outcome,
            "is_terminal": True,
        }

        if gate_outcome:
            metadata["gate_outcome"] = gate_outcome

        # Include summary of workflow execution
        metadata["conversation_turns"] = len(context.conversation_history)
        metadata["documents_produced"] = list(context.document_content.keys())

        return NodeResult(
            outcome=terminal_outcome,
            produced_document=context.document_content.get(context.document_type),
            metadata=metadata,
        )

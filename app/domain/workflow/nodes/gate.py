"""Gate node executor for Document Interaction Workflow Plans (ADR-039).

Gate nodes are decision points that determine workflow routing.
"""

import logging
from typing import Any, Dict, List, Optional

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)

logger = logging.getLogger(__name__)


class GateNodeExecutor(NodeExecutor):
    """Executor for gate nodes.

    Gate nodes:
    - Present choices to user (if requires_consent or gate_outcomes defined)
    - Collect user decision
    - Return the selected outcome

    BOUNDARY CONSTRAINTS:
    - Returns outcome based on user selection or evaluation
    - Does NOT inspect edges or make routing decisions
    - Does NOT decide which path to take - only reports the selected outcome
    """

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "gate"

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a gate node.

        Args:
            node_id: The gate node ID
            node_config: Node configuration with gate_outcomes, requires_consent
            context: Workflow context with user responses
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with outcome based on user selection
        """
        requires_consent = node_config.get("requires_consent", False)
        gate_outcomes = node_config.get("gate_outcomes", [])

        # Check if we already have a user response for this gate
        response_key = f"gate_{node_id}_outcome"
        existing_response = context.get_user_response(response_key)

        if existing_response:
            # User already made a selection
            logger.info(f"Gate {node_id} using existing response: {existing_response}")
            return NodeResult(
                outcome=existing_response,
                metadata={"gate_id": node_id, "from_cache": True},
            )

        # Handle consent gate
        if requires_consent:
            return self._handle_consent_gate(node_id, context)

        # Handle outcome gate (multiple choices)
        if gate_outcomes:
            return self._handle_outcome_gate(node_id, gate_outcomes, context)

        # Default: simple pass-through gate
        logger.info(f"Gate {node_id} passed (no conditions)")
        return NodeResult.success(metadata={"gate_id": node_id})

    def _handle_consent_gate(
        self,
        node_id: str,
        context: DocumentWorkflowContext,
    ) -> NodeResult:
        """Handle a consent gate that requires explicit user consent.

        Args:
            node_id: The gate node ID
            context: Workflow context

        Returns:
            NodeResult requiring user input or with consent outcome
        """
        response_key = f"gate_{node_id}_consent"
        consent = context.get_user_response(response_key)

        if consent is None:
            # Need to ask for consent
            logger.info(f"Gate {node_id} requesting consent")
            return NodeResult.needs_user_input(
                prompt="Do you want to proceed with document generation?",
                choices=["proceed", "not_ready"],
                gate_id=node_id,
                consent_required=True,
            )

        # User has responded
        if consent in ("proceed", "yes", "true", True):
            logger.info(f"Gate {node_id} consent granted")
            return NodeResult(
                outcome="success",
                metadata={"gate_id": node_id, "consent": True},
            )
        else:
            logger.info(f"Gate {node_id} consent denied")
            return NodeResult(
                outcome="blocked",
                metadata={"gate_id": node_id, "consent": False},
            )

    def _handle_outcome_gate(
        self,
        node_id: str,
        gate_outcomes: List[str],
        context: DocumentWorkflowContext,
    ) -> NodeResult:
        """Handle a gate with multiple outcome choices.

        Args:
            node_id: The gate node ID
            gate_outcomes: List of possible outcomes
            context: Workflow context

        Returns:
            NodeResult requiring user input or with selected outcome
        """
        response_key = f"gate_{node_id}_outcome"
        selected = context.get_user_response(response_key)

        if selected is None:
            # Need user to select outcome
            logger.info(f"Gate {node_id} requesting outcome selection from {gate_outcomes}")
            return NodeResult.needs_user_input(
                prompt=f"Select the appropriate outcome for this gate",
                choices=gate_outcomes,
                gate_id=node_id,
                outcome_selection=True,
            )

        # Validate selection
        if selected not in gate_outcomes:
            logger.warning(
                f"Gate {node_id} received invalid outcome: {selected}. "
                f"Valid: {gate_outcomes}"
            )
            # Return as-is; let EdgeRouter handle invalid outcomes
            return NodeResult(
                outcome=selected,
                metadata={
                    "gate_id": node_id,
                    "warning": f"Outcome '{selected}' not in defined gate_outcomes",
                },
            )

        logger.info(f"Gate {node_id} outcome selected: {selected}")
        return NodeResult(
            outcome=selected,
            metadata={"gate_id": node_id},
        )

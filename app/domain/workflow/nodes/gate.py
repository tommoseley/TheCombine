"""Gate node executor for Document Interaction Workflow Plans (ADR-039).

Gate nodes are decision points that determine workflow routing.

Supports two modes:
1. Simple gates: consent gates and outcome selection gates
2. Gate Profiles (ADR-047): gates with internals (LLM/MECH/UI passes)
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)

if TYPE_CHECKING:
    from app.api.services.mechanical_ops_service import MechanicalOpsService

logger = logging.getLogger(__name__)


class GateNodeExecutor(NodeExecutor):
    """Executor for gate nodes.

    Gate nodes:
    - Present choices to user (if requires_consent or gate_outcomes defined)
    - Collect user decision
    - Return the selected outcome

    Gate Profile nodes (ADR-047):
    - Have internals configuration with LLM/MECH/UI passes
    - Delegate to IntakeGateProfileExecutor for execution

    BOUNDARY CONSTRAINTS:
    - Returns outcome based on user selection or evaluation
    - Does NOT inspect edges or make routing decisions
    - Does NOT decide which path to take - only reports the selected outcome
    """

    def __init__(
        self,
        llm_service=None,
        prompt_loader=None,
        ops_service: Optional["MechanicalOpsService"] = None,
    ):
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader
        self._ops_service = ops_service
        self._profile_executor = None  # Lazy initialization

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
            node_config: Node configuration with gate_outcomes, requires_consent, or internals
            context: Workflow context with user responses
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with outcome based on user selection
        """
        # Check for Gate Profile (ADR-047) - has internals
        internals = node_config.get("internals")
        if internals:
            return await self._execute_gate_profile(node_id, node_config, context, state_snapshot)

        requires_consent = node_config.get("requires_consent", False)
        gate_outcomes = node_config.get("gate_outcomes", [])

        # Get user's selected option (ADR-037 compliant)
        # Per ADR-037: Option selection arrives via context.extra["selected_option_id"]
        selected_option_id = context.extra.get("selected_option_id")

        # Handle consent gate
        if requires_consent:
            return self._handle_consent_gate(node_id, selected_option_id)

        # Handle outcome gate (multiple choices)
        if gate_outcomes:
            return self._handle_outcome_gate(node_id, gate_outcomes, selected_option_id)

        # Default: simple pass-through gate
        logger.info(f"Gate {node_id} passed (no conditions)")
        return NodeResult.success(metadata={"gate_id": node_id})

    def _handle_consent_gate(
        self,
        node_id: str,
        selected_option_id: Optional[str],
    ) -> NodeResult:
        """Handle a consent gate that requires explicit user consent.

        Args:
            node_id: The gate node ID
            selected_option_id: User's selected option (ADR-037 compliant)

        Returns:
            NodeResult requiring user input or with consent outcome
        """
        # ADR-037: Only explicit option selection can advance
        # Valid consent options: "proceed", "not_ready"
        consent_proceed_options = {"proceed", "yes", "consent_proceed"}
        consent_decline_options = {"not_ready", "no", "consent_decline"}

        if selected_option_id is None:
            # Need to ask for consent
            logger.info(f"Gate {node_id} requesting consent")
            return NodeResult.needs_user_input(
                prompt="Do you want to proceed with document generation?",
                choices=["proceed", "not_ready"],
                gate_id=node_id,
                consent_required=True,
            )

        # User has selected an option
        if selected_option_id in consent_proceed_options:
            logger.info(f"Gate {node_id} consent granted via '{selected_option_id}'")
            return NodeResult(
                outcome="success",
                metadata={
                    "gate_id": node_id,
                    "consent": True,
                    "selected_option_id": selected_option_id,
                },
            )
        elif selected_option_id in consent_decline_options:
            logger.info(f"Gate {node_id} consent denied via '{selected_option_id}'")
            return NodeResult(
                outcome="blocked",
                metadata={
                    "gate_id": node_id,
                    "consent": False,
                    "selected_option_id": selected_option_id,
                },
            )
        else:
            # Invalid option - log and reject
            logger.warning(
                f"Gate {node_id} received invalid consent option: '{selected_option_id}'"
            )
            return NodeResult.needs_user_input(
                prompt="Please select a valid option: proceed or not_ready",
                choices=["proceed", "not_ready"],
                gate_id=node_id,
                consent_required=True,
                invalid_selection=selected_option_id,
            )

    def _handle_outcome_gate(
        self,
        node_id: str,
        gate_outcomes: List[str],
        selected_option_id: Optional[str],
    ) -> NodeResult:
        """Handle a gate with multiple outcome choices.

        Args:
            node_id: The gate node ID
            gate_outcomes: List of possible outcomes (available_options per ADR-037)
            selected_option_id: User's selected option (must be in gate_outcomes)

        Returns:
            NodeResult requiring user input or with selected outcome
        """
        if selected_option_id is None:
            # Need user to select outcome
            logger.info(f"Gate {node_id} requesting outcome selection from {gate_outcomes}")
            return NodeResult.needs_user_input(
                prompt="Select the appropriate outcome for this gate",
                choices=gate_outcomes,
                gate_id=node_id,
                outcome_selection=True,
            )

        # ADR-037: Validate selection is in available_options
        if selected_option_id not in gate_outcomes:
            logger.warning(
                f"Gate {node_id} received invalid option: '{selected_option_id}'. "
                f"Valid options: {gate_outcomes}"
            )
            # Re-prompt with valid options - do NOT advance with invalid selection
            return NodeResult.needs_user_input(
                prompt=f"Invalid selection. Please choose from: {', '.join(gate_outcomes)}",
                choices=gate_outcomes,
                gate_id=node_id,
                outcome_selection=True,
                invalid_selection=selected_option_id,
            )

        logger.info(f"Gate {node_id} outcome selected: {selected_option_id}")
        return NodeResult(
            outcome=selected_option_id,
            metadata={
                "gate_id": node_id,
                "gate_outcome": selected_option_id,
                "selected_option_id": selected_option_id,
            },
        )

    async def _execute_gate_profile(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a Gate Profile node with internals (ADR-047).

        Delegates to IntakeGateProfileExecutor for actual execution.
        """
        # Lazy import to avoid circular dependency
        if self._profile_executor is None:
            from app.domain.workflow.nodes.intake_gate_profile import IntakeGateProfileExecutor
            self._profile_executor = IntakeGateProfileExecutor(
                llm_service=self.llm_service,
                prompt_loader=self.prompt_loader,
                ops_service=self._ops_service,
            )

        logger.info(f"Gate {node_id}: Delegating to Gate Profile executor")
        return await self._profile_executor.execute(
            node_id=node_id,
            node_config=node_config,
            context=context,
            state_snapshot=state_snapshot,
        )

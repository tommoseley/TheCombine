"""Intake Gate Profile Executor (ADR-047, WS-ADR-047-005).

Implements the Gate Profile pattern for Concierge Intake:
- pass_a (LLM): Classification using intake_gate task prompt
- extract (MECH): Extract fields from classification
- entry (UI): Operator confirms/corrects classification
- pin (MECH): Pin confirmed fields as binding constraints

This replaces the mechanical regex-based IntakeGateExecutor with a proper
Gate Profile that uses LLM classification + operator confirmation.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)

if TYPE_CHECKING:
    from app.api.services.mechanical_ops_service import MechanicalOpsService

logger = logging.getLogger(__name__)


class IntakeGateProfileExecutor(NodeExecutor):
    """Executor for intake gate with Gate Profile pattern.

    Execution flow:
    1. First execution (no prior state):
       - Execute pass_a (LLM classification)
       - Execute extract (MECH extraction)
       - Return pending_entry for operator confirmation

    2. Resume (with operator confirmation):
       - Execute pin (MECH invariant pinning)
       - Return qualified/rejected outcome

    State tracking via context_state["intake_gate_phase"]:
    - "initial": Ready for pass_a
    - "awaiting_confirmation": Entry returned, waiting for operator
    - "confirmed": Operator confirmed, ready for pinning
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

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "gate"  # Handles gate type with internals

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute intake gate with Gate Profile pattern."""

        # Check if this is a gate with internals (Gate Profile)
        internals = node_config.get("internals")
        if not internals:
            # Not a Gate Profile - delegate to regular gate handling
            logger.warning(f"Gate {node_id} has no internals, cannot execute as Gate Profile")
            return NodeResult.failed("Gate has no internals configuration")

        # Get current phase from context_state
        context_state = state_snapshot.get("context_state", {})
        phase = context_state.get("intake_gate_phase", "initial")

        logger.info(f"Intake gate {node_id}: phase={phase}")

        if phase == "initial":
            return await self._execute_initial_phase(node_id, internals, context, state_snapshot)
        elif phase == "awaiting_confirmation":
            return await self._execute_confirmation_phase(node_id, internals, context, state_snapshot)
        else:
            logger.warning(f"Unknown phase '{phase}' for gate {node_id}")
            return NodeResult.failed(f"Unknown gate phase: {phase}")

    async def _execute_initial_phase(
        self,
        node_id: str,
        internals: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute pass_a (LLM) and extract (MECH), then pause for entry."""

        user_input = context.extra.get("user_input", "")
        if not user_input or not user_input.strip():
            logger.info(f"Gate {node_id}: No input, requesting initial description")
            return NodeResult.needs_user_input(
                prompt="Please describe what you'd like to build or accomplish.",
                node_id=node_id,
            )

        # --- Pass A: LLM Classification ---
        pass_a = internals.get("pass_a", {})
        if pass_a.get("internal_type") == "LLM":
            classification = await self._execute_llm_classification(
                node_id, pass_a, user_input, context, state_snapshot
            )
            if classification is None:
                return NodeResult.failed("LLM classification failed")
        else:
            # Fallback: use simple extraction (like old mechanical executor)
            classification = self._extract_classification_fallback(user_input)

        logger.info(f"Gate {node_id}: Classification complete - {classification.get('classification')}")

        # Check if classification needs more info
        if classification.get("classification") == "needs_clarification":
            missing = classification.get("missing_information", [])
            prompt = missing[0] if missing else "Please provide more details about your project."
            return NodeResult.needs_user_input(
                prompt=prompt,
                node_id=node_id,
                intake_classification=classification,
            )

        # Check if out of scope
        if classification.get("classification") == "out_of_scope":
            return NodeResult(
                outcome="out_of_scope",
                metadata={
                    "node_id": node_id,
                    "classification": classification,
                    "reason": classification.get("classification_rationale", "Out of scope"),
                },
            )

        # --- Extract: MECH Extraction ---
        extract = internals.get("extract", {})
        if extract.get("internal_type") == "MECH":
            extracted = await self._execute_extraction(node_id, extract, classification)
        else:
            extracted = classification  # Pass through if no extraction configured

        # --- Entry: Pause for operator confirmation ---
        entry = internals.get("entry", {})
        entry_prompt = "Review the intake classification. Confirm or correct as needed."

        # Return pending entry - execution pauses here
        return NodeResult(
            outcome="needs_user_input",
            requires_user_input=True,
            user_prompt=entry_prompt,
            user_input_payload=classification,  # What to render
            user_input_schema_ref="schema:intake_confirmation:1.0.0",
            metadata={
                "node_id": node_id,
                "intake_gate_phase": "awaiting_confirmation",
                "intake_classification": classification,
                "extracted": extracted,
                "entry_op_ref": entry.get("op_ref"),
                "user_input": user_input,
            },
        )

    async def _execute_confirmation_phase(
        self,
        node_id: str,
        internals: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Process operator confirmation and execute pin (MECH)."""

        # Get operator confirmation from user input
        user_input = context.extra.get("user_input", {})
        if isinstance(user_input, str):
            # Try to parse as JSON
            import json
            try:
                confirmation = json.loads(user_input)
            except json.JSONDecodeError:
                confirmation = {"confirmed": True}  # Default to confirmed
        else:
            confirmation = user_input or {"confirmed": True}

        # Get classification from previous execution
        context_state = state_snapshot.get("context_state", {})
        classification = context_state.get("intake_classification", {})

        logger.info(f"Gate {node_id}: Operator confirmation received - confirmed={confirmation.get('confirmed')}")

        # --- Pin: MECH Invariant Pinning ---
        pin = internals.get("pin", {})
        if pin.get("internal_type") == "MECH" and confirmation.get("confirmed"):
            await self._execute_pinning(node_id, pin, confirmation, state_snapshot)

        # Merge confirmation with classification for final output
        final_classification = {**classification}
        if confirmation.get("project_type"):
            final_classification["project_type"] = confirmation["project_type"]
        if confirmation.get("artifact_type"):
            final_classification["artifact_type"] = confirmation["artifact_type"]
        if confirmation.get("audience"):
            final_classification["audience"] = confirmation["audience"]

        # Build interpretation for downstream
        interpretation = {
            "project_name": {"value": final_classification.get("intake_summary", "")[:50], "source": "llm", "locked": False},
            "problem_statement": {"value": final_classification.get("intake_summary", ""), "source": "llm", "locked": False},
            "project_type": {"value": final_classification.get("project_type", "greenfield"), "source": "operator", "locked": True},
        }

        return NodeResult(
            outcome="qualified",
            metadata={
                "node_id": node_id,
                "classification": "qualified",
                "intake_classification": final_classification,
                "intake_confirmation": confirmation,
                "intake_summary": final_classification.get("intake_summary", ""),
                "project_type": final_classification.get("project_type", "greenfield"),
                "artifact_type": final_classification.get("artifact_type"),
                "audience": final_classification.get("audience"),
                "source": "gate_profile",
                "interpretation": interpretation,
                "phase": "review",
                "intake_gate_phase": "complete",
            },
        )

    async def _execute_llm_classification(
        self,
        node_id: str,
        pass_a_config: Dict[str, Any],
        user_input: str,
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Execute LLM classification using intake_gate task prompt."""

        if not self.llm_service or not self.prompt_loader:
            logger.warning(f"Gate {node_id}: No LLM service, using fallback classification")
            return self._extract_classification_fallback(user_input)

        try:
            # Load task prompt
            task_ref = pass_a_config.get("task_ref", "prompt:task:intake_gate:1.0.0")
            task_prompt = self.prompt_loader.load_task_prompt(task_ref)

            # Build messages for LLM
            user_message = f"## User Input\n{user_input}"
            messages = [{"role": "user", "content": user_message}]

            # Execute LLM with task prompt as system prompt
            response = await self.llm_service.complete(
                messages=messages,
                system_prompt=task_prompt,
                task_ref=f"{node_id}_pass_a",
                node_id=node_id,
            )

            # Parse JSON response
            import json
            import re

            # Try to extract JSON from response
            content = response.content if hasattr(response, 'content') else str(response)

            # Look for JSON in code blocks or raw
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON object
                json_match = re.search(r'\{[^{}]*"classification"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content

            classification = json.loads(json_str)
            return classification

        except Exception as e:
            logger.error(f"Gate {node_id}: LLM classification failed: {e}")
            return self._extract_classification_fallback(user_input)

    def _extract_classification_fallback(self, user_input: str) -> Dict[str, Any]:
        """Fallback classification using simple pattern matching."""
        import re

        text_lower = user_input.lower()

        # Extract artifact type
        artifact_type = None
        patterns = [
            (r"\bweb\s*app", "web_application"),
            (r"\bmobile\s*app", "mobile_application"),
            (r"\bapi\b", "api"),
            (r"\bapp\b", "application"),
        ]
        for pattern, atype in patterns:
            if re.search(pattern, text_lower):
                artifact_type = atype
                break

        # Extract audience
        audience = None
        audience_patterns = [
            (r"\bkids?\b|\bchildren\b", "children"),
            (r"\bcustomers?\b", "customers"),
            (r"\busers?\b", "users"),
            (r"\bteam\b", "internal_team"),
        ]
        for pattern, aud in audience_patterns:
            if re.search(pattern, text_lower):
                audience = aud
                break

        # Determine classification
        if artifact_type and audience:
            classification = "qualified"
            missing = []
        else:
            classification = "needs_clarification"
            missing = []
            if not artifact_type:
                missing.append("What type of software do you want to build?")
            if not audience:
                missing.append("Who will use this?")

        return {
            "classification": classification,
            "project_type": "greenfield",
            "artifact_type": artifact_type,
            "audience": audience,
            "intake_summary": user_input[:500],
            "confidence": 0.7 if classification == "qualified" else 0.5,
            "missing_information": missing,
            "classification_rationale": "Pattern-based fallback classification",
        }

    async def _execute_extraction(
        self,
        node_id: str,
        extract_config: Dict[str, Any],
        classification: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute extraction operation."""

        op_ref = extract_config.get("op_ref")
        if not op_ref or not self._ops_service:
            return classification

        try:
            from app.api.services.mech_handlers import execute_operation

            op = self._ops_service.get_operation_by_ref(op_ref)
            if op:
                result = await execute_operation(
                    operation=op,
                    inputs={"source_document": classification},
                )
                if result.success:
                    return result.output
        except Exception as e:
            logger.warning(f"Gate {node_id}: Extraction failed: {e}")

        return classification

    async def _execute_pinning(
        self,
        node_id: str,
        pin_config: Dict[str, Any],
        confirmation: Dict[str, Any],
        state_snapshot: Dict[str, Any],
    ) -> None:
        """Execute invariant pinning operation."""

        op_ref = pin_config.get("op_ref")
        if not op_ref or not self._ops_service:
            return

        try:
            from app.api.services.mech_handlers import execute_operation

            op = self._ops_service.get_operation_by_ref(op_ref)
            if op:
                await execute_operation(
                    operation=op,
                    inputs={
                        "confirmation": confirmation,
                        "context_state": state_snapshot.get("context_state", {}),
                    },
                )
        except Exception as e:
            logger.warning(f"Gate {node_id}: Pinning failed: {e}")

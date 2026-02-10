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
        """Execute a Gate Profile node with internals (ADR-047/ADR-049).

        Routes to appropriate executor based on gate_kind or internals structure:
        - QA gates (gate_kind=qa or has evaluate internal) → QANodeExecutor
        - Intake gates (has pass_a internal) → IntakeGateProfileExecutor
        """
        internals = node_config.get("internals", {})
        gate_kind = node_config.get("gate_kind")

        logger.info(f"Gate {node_id}: gate_kind={gate_kind}, internals_keys={list(internals.keys())}")

        # Route QA gates to QANodeExecutor
        if gate_kind == "qa" or "evaluate" in internals:
            logger.info(f"Gate {node_id}: Routing to QA executor (gate_kind={gate_kind})")
            return await self._execute_qa_gate(node_id, node_config, context, state_snapshot)

        # Route PGC gates to PGC executor
        # Check gate_kind first, then fall back to node_id pattern matching
        if gate_kind == "pgc" or (gate_kind is None and "pgc" in node_id.lower()):
            logger.info(f"Gate {node_id}: Routing to PGC executor (gate_kind={gate_kind})")
            return await self._execute_pgc_gate(node_id, node_config, context, state_snapshot)

        # Route intake-style gates to IntakeGateProfileExecutor
        if self._profile_executor is None:
            from app.domain.workflow.nodes.intake_gate_profile import IntakeGateProfileExecutor
            self._profile_executor = IntakeGateProfileExecutor(
                llm_service=self.llm_service,
                prompt_loader=self.prompt_loader,
                ops_service=self._ops_service,
            )

        logger.info(f"Gate {node_id}: Delegating to Intake Gate Profile executor")
        return await self._profile_executor.execute(
            node_id=node_id,
            node_config=node_config,
            context=context,
            state_snapshot=state_snapshot,
        )

    async def _execute_qa_gate(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a QA gate with evaluate internal.

        Uses QANodeExecutor to run the QA evaluation.
        """
        from app.domain.workflow.nodes.qa import QANodeExecutor

        # Extract QA config from internals.evaluate
        internals = node_config.get("internals", {})
        evaluate_config = internals.get("evaluate", {})

        # Build QA node config from evaluate internal
        qa_node_config = {
            "task_ref": evaluate_config.get("task_ref"),
            "schema_ref": evaluate_config.get("schema_ref"),
            "qa_mode": evaluate_config.get("qa_mode", "semantic"),
            "requires_qa": True,
            # Pass through any includes for prompt resolution
            "includes": evaluate_config.get("includes", {}),
        }

        # Create QA executor
        qa_executor = QANodeExecutor(
            llm_service=self.llm_service,
            prompt_loader=self.prompt_loader,
        )

        logger.info(f"QA Gate {node_id}: Executing QA evaluation with task_ref={qa_node_config.get('task_ref')}")

        # Execute QA
        result = await qa_executor.execute(
            node_id=node_id,
            node_config=qa_node_config,
            context=context,
            state_snapshot=state_snapshot,
        )

        # Map QA result to gate outcomes
        # QA pass -> "pass" edge, QA fail -> "fail" edge (triggers remediation)
        if result.outcome == "success":
            return NodeResult(
                outcome="pass",
                metadata={
                    **result.metadata,
                    "gate_id": node_id,
                    "gate_kind": "qa",
                },
            )
        else:
            return NodeResult(
                outcome="fail",
                metadata={
                    **result.metadata,
                    "gate_id": node_id,
                    "gate_kind": "qa",
                },
            )

    def _resolve_urn(self, urn: str) -> str:
        """Resolve URN-style reference to file path.

        URN formats:
        - prompt:{type}:{name}:{version} -> Maps to prompt file paths
        - schema:{name}:{version} -> Maps to schema file paths
        """
        if not urn:
            return urn

        # Schema URNs (schema:name:version) - map to actual schema files
        if urn.startswith("schema:"):
            parts = urn.split(":")
            if len(parts) >= 3:
                _, name, version = parts[:3]
                # Map schema names to actual files
                # v2 workflow uses clarification_questions but actual schema is clarification_question_set
                if name == "clarification_questions":
                    return "seed/schemas/clarification_question_set.v2.json"
                # Default: pass through for assembler to handle
                return urn
            return urn

        # Handle prompt URNs
        if not urn.startswith("prompt:"):
            return urn

        parts = urn.split(":")
        if len(parts) < 4:
            return urn

        _, prompt_type, name, version = parts[:4]

        # Map prompt types to file paths
        if prompt_type == "pgc":
            # pgc contexts: prompt:pgc:project_discovery.v1:1.0.0 -> seed/prompts/pgc-contexts/project_discovery.v1.txt
            return f"seed/prompts/pgc-contexts/{name}.txt"
        elif prompt_type == "role":
            # roles: prompt:role:technical_architect:1.0.0 -> seed/prompts/roles/Technical Architect 1.0.txt
            name_formatted = name.replace("_", " ").title()
            return f"seed/prompts/roles/{name_formatted} {version.replace('.0.0', '.0')}.txt"
        elif prompt_type == "task":
            # tasks: prompt:task:project_discovery:1.4.0 -> seed/prompts/tasks/Project Discovery v1.4.txt
            name_formatted = name.replace("_", " ").title()
            version_short = version.rsplit(".", 1)[0] if version.count(".") > 1 else version
            return f"seed/prompts/tasks/{name_formatted} v{version_short}.txt"
        elif prompt_type == "template":
            # templates: prompt:template:pgc_clarifier:1.0.0 -> tasks/Clarification Questions Generator v1.1
            if "pgc_clarifier" in name:
                return "tasks/Clarification Questions Generator v1.1"
            elif "document_generator" in name:
                return "templates/Document Generator v1.0"
            return f"templates/{name}"
        else:
            return urn

    async def _execute_pgc_gate(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a PGC (Pre-Gen Clarification) gate.

        PGC gates have 3 phases:
        1. pass_a: Generate questions (LLM)
        2. entry: Collect user answers (UI pause)
        3. merge: Combine questions + answers into clarifications

        State tracking:
        - context.context_state["pgc_questions"] = questions from pass_a
        - context.context_state["pgc_answers"] = answers from entry phase
        """
        from app.domain.workflow.nodes.task import TaskNodeExecutor

        internals = node_config.get("internals", {})
        pass_a = internals.get("pass_a", {})
        produces = node_config.get("produces", "pgc_clarifications")

        # Check current phase based on what's in context
        pgc_questions = context.context_state.get("pgc_questions")
        pgc_answers = context.context_state.get("pgc_answers")

        # Debug: log all keys in context_state to diagnose state propagation
        context_keys = list(context.context_state.keys())
        logger.info(
            f"PGC Gate {node_id}: questions={pgc_questions is not None}, "
            f"answers={pgc_answers is not None}, context_keys={context_keys}"
        )

        # Phase 3: merge - we have both questions and answers
        if pgc_questions and pgc_answers:
            logger.info(f"PGC Gate {node_id}: Phase 3 (merge) - combining questions and answers")

            # Merge questions with answers
            merged_clarifications = []
            questions_list = pgc_questions.get("questions", [])

            for q in questions_list:
                q_id = q.get("id", "")
                answer = pgc_answers.get(q_id, "")
                merged_clarifications.append({
                    "id": q_id,
                    "question": q.get("text", q.get("question", "")),
                    "answer": answer,
                    "priority": q.get("priority", "should"),
                    "why_it_matters": q.get("why_it_matters", ""),
                })

            # Store merged clarifications in context for document generation
            clarifications_doc = {
                "schema_version": "pgc_clarifications.v1",
                "clarifications": merged_clarifications,
                "question_count": len(questions_list),
                "answered_count": len([c for c in merged_clarifications if c.get("answer")]),
            }

            context.document_content[produces] = clarifications_doc

            logger.info(f"PGC Gate {node_id}: Merge complete, {len(merged_clarifications)} clarifications")

            # Return "qualified" outcome to match v2 workflow edge (pgc_gate -> generation)
            return NodeResult(
                outcome="qualified",
                produced_document=clarifications_doc,
                metadata={
                    "gate_id": node_id,
                    "gate_kind": "pgc",
                    "phase": "merge",
                    "produces": produces,
                },
            )

        # Phase 2: entry - we have questions but no answers, need user input
        # This shouldn't normally happen here since the pause happens in phase 1
        # But handle it for robustness
        if pgc_questions and not pgc_answers:
            logger.info(f"PGC Gate {node_id}: Phase 2 (entry) - waiting for user answers")
            return NodeResult.needs_user_input(
                prompt="Please answer the clarification questions",
                choices=None,
                gate_id=node_id,
                user_input_payload=pgc_questions,
            )

        # Phase 1: pass_a - generate questions
        logger.info(f"PGC Gate {node_id}: Phase 1 (pass_a) - generating questions")

        # Resolve URN-style references to file paths
        task_ref = self._resolve_urn(pass_a.get("template_ref", ""))
        includes = {}
        for key, value in pass_a.get("includes", {}).items():
            includes[key] = self._resolve_urn(value)

        # Add OUTPUT_SCHEMA from output_schema_ref if present (v2 workflow format)
        if pass_a.get("output_schema_ref"):
            includes["OUTPUT_SCHEMA"] = self._resolve_urn(pass_a.get("output_schema_ref"))

        # Build task node config from pass_a internal
        task_node_config = {
            "type": "pgc",  # Triggers PGC behavior in TaskNodeExecutor
            "task_ref": task_ref,
            "includes": includes,
            "produces": produces,
        }

        # Create task executor for PGC
        task_executor = TaskNodeExecutor(
            llm_service=self.llm_service,
            prompt_loader=self.prompt_loader,
        )

        logger.info(f"PGC Gate {node_id}: Executing pass_a with task_ref={task_ref}")

        # Execute PGC via task executor
        result = await task_executor.execute(
            node_id=node_id,
            node_config=task_node_config,
            context=context,
            state_snapshot=state_snapshot,
        )

        # If pass_a succeeded and returned questions, store them in context for phase tracking
        logger.info(f"PGC Gate {node_id}: result.outcome={result.outcome}, has_produced_doc={result.produced_document is not None}")
        if result.outcome == "needs_user_input" and result.produced_document:
            # Store questions in context_state for phase tracking
            # This will be persisted by the plan executor
            context.context_state["pgc_questions"] = result.produced_document
            logger.info(f"PGC Gate {node_id}: Stored {len(result.produced_document.get('questions', []))} questions in context_state")

        # Add gate metadata to result
        if result.metadata is None:
            result.metadata = {}
        result.metadata["gate_id"] = node_id
        result.metadata["gate_kind"] = "pgc"
        result.metadata["phase"] = "pass_a"

        return result

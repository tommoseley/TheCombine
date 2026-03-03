"""QA node executor for Document Interaction Workflow Plans (ADR-039).

QA nodes validate generated documents against quality criteria.

Validation order (per ADR-042, WS-PGC-VALIDATION-001, and WS-SEMANTIC-QA-001):
1. Constraint drift validation (ADR-042 Layer 1) - mechanical checks, fails fast
2. Promotion validation (WS-PGC-VALIDATION-001) - catches promotion and contradiction issues
3. Schema validation
4. LLM-based semantic QA (WS-SEMANTIC-QA-001 Layer 2) - semantic constraint compliance
"""

import json
import logging
import os
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Protocol

import jsonschema

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    LLMService,
    NodeExecutor,
    NodeResult,
    PromptLoader,
)
from app.domain.workflow.validation import (
    PromotionValidator,
    PromotionValidationInput,
    PromotionValidationResult,
    ConstraintDriftValidator,
    DriftValidationResult,
)

logger = logging.getLogger(__name__)


class SchemaValidator(Protocol):
    """Protocol for schema validation."""

    def validate(self, document: Dict[str, Any], schema_ref: str) -> tuple[bool, List[str]]:
        """Validate document against schema.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        ...


class QANodeExecutor(NodeExecutor):
    """Executor for QA nodes.

    QA nodes:
    - Validate documents against schemas
    - Run LLM-based quality checks
    - Return pass/fail outcomes with feedback

    BOUNDARY CONSTRAINTS:
    - Returns outcome "success" (passed) or "failed"
    - Does NOT increment retry counters (that's EdgeRouter/PlanExecutor's job)
    - Does NOT decide whether to retry or trip circuit breaker
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        schema_validator: Optional[SchemaValidator] = None,
    ):
        """Initialize with dependencies.

        Args:
            llm_service: Optional LLM service for quality assessment
            prompt_loader: Optional prompt loader for QA prompts
            schema_validator: Optional schema validator
        """
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader
        self.schema_validator = schema_validator

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "qa"

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a QA node.

        Runs a sequential validation pipeline:
        drift -> code-based -> schema -> semantic -> LLM.
        Each check may return an early failure or collect warnings/errors.

        Args:
            node_id: The QA node ID
            node_config: Node configuration with task_ref, schema_ref
            context: Workflow context with document to validate
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with outcome "success" or "failed"
        """
        requires_qa = node_config.get("requires_qa", True)
        if not requires_qa:
            logger.info(f"QA node {node_id} skipped (requires_qa=false)")
            return NodeResult.success(qa_skipped=True)

        document = self._get_document_to_validate(context)
        if not document:
            logger.warning(f"QA node {node_id}: No document to validate")
            return NodeResult.failed(
                reason="No document available for QA validation",
                node_id=node_id,
            )

        errors: List[str] = []
        feedback: Dict[str, Any] = {}

        # 1. Drift validation (ADR-042) - fails fast
        fail_result, drift_warnings = self._check_drift_validation(
            document, context, node_id,
        )
        if fail_result:
            return fail_result

        # 2. Code-based validation (WS-PGC-VALIDATION-001) - fails fast
        fail_result, code_validation_warnings = self._check_code_validation(
            document, context, node_id,
        )
        if fail_result:
            return fail_result

        # 3. Schema validation
        self._check_schema_validation(
            document, node_config.get("schema_ref"), errors, feedback,
        )

        # 4. Semantic QA (WS-SEMANTIC-QA-001 Layer 2)
        fail_result, semantic_warnings, semantic_qa_report = await self._check_semantic_qa(
            node_id, document, context, errors,
        )
        if fail_result:
            return fail_result

        # 5. LLM QA
        await self._check_llm_qa(
            node_id, node_config, document, context, errors, feedback,
        )

        # 6. Final outcome
        if errors:
            logger.info(f"QA node {node_id} failed with {len(errors)} issues")
            return NodeResult(
                outcome="failed",
                metadata={
                    "node_id": node_id,
                    "errors": errors,
                    "feedback": feedback,
                    "error_count": len(errors),
                },
            )

        logger.info(f"QA node {node_id} passed")
        from app.domain.workflow.nodes.qa_parsing import build_qa_success_metadata

        success_metadata = build_qa_success_metadata(
            node_id=node_id,
            drift_warnings=drift_warnings,
            code_validation_warnings=code_validation_warnings,
            semantic_warnings=semantic_warnings,
            semantic_qa_report=semantic_qa_report,
        )
        return NodeResult.success(**success_metadata)

    # ------------------------------------------------------------------
    # Validation check methods (WS-CRAP-010 extractions)
    # ------------------------------------------------------------------

    def _check_drift_validation(
        self,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
        node_id: str,
    ) -> tuple[Optional[NodeResult], List[Dict[str, Any]]]:
        """Run drift validation. Returns (early_fail_result, warnings)."""
        drift_result = self._run_drift_validation(document=document, context=context)

        if drift_result is None:
            return None, []

        if not drift_result.passed:
            logger.warning(
                f"QA node {node_id} failed drift validation with "
                f"{len(drift_result.errors)} errors, "
                f"{len(drift_result.warnings)} warnings"
            )
            return NodeResult(
                outcome="failed",
                metadata={
                    "node_id": node_id,
                    "drift_errors": [v.to_dict() for v in drift_result.errors],
                    "drift_warnings": [v.to_dict() for v in drift_result.warnings],
                    "validation_source": "constraint_drift",
                },
            ), []

        return None, [v.to_dict() for v in drift_result.warnings]

    def _check_code_validation(
        self,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
        node_id: str,
    ) -> tuple[Optional[NodeResult], List[Dict[str, Any]]]:
        """Run code-based validation. Returns (early_fail_result, warnings)."""
        result = self._run_code_based_validation(document=document, context=context)

        if result is None:
            return None, []

        if not result.passed:
            return NodeResult(
                outcome="failed",
                metadata={
                    "node_id": node_id,
                    "validation_errors": [asdict(e) for e in result.errors],
                    "validation_warnings": [asdict(w) for w in result.warnings],
                    "validation_source": "code_based",
                },
            ), []

        return None, [asdict(w) for w in result.warnings]

    def _check_schema_validation(
        self,
        document: Dict[str, Any],
        schema_ref: Optional[str],
        errors: List[str],
        feedback: Dict[str, Any],
    ) -> None:
        """Run schema validation, appending errors in place."""
        if not schema_ref or not self.schema_validator:
            return

        schema_valid, schema_errors = self.schema_validator.validate(
            document, schema_ref
        )
        if not schema_valid:
            errors.extend(schema_errors)
            feedback["schema_errors"] = schema_errors

    async def _check_semantic_qa(
        self,
        node_id: str,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
        errors: List[str],
    ) -> tuple[Optional[NodeResult], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Run semantic QA. Returns (early_fail_result, warnings, report)."""
        try:
            semantic_qa_report = await self._run_semantic_qa(node_id, document, context)
        except ValueError as e:
            logger.error(f"Semantic QA validation error: {e}")
            errors.append(f"Semantic QA validation error: {str(e)}")
            return None, [], None

        if not semantic_qa_report:
            return None, [], None

        if semantic_qa_report.get("gate") == "fail":
            error_messages = self._extract_semantic_error_messages(semantic_qa_report)
            return NodeResult(
                outcome="failed",
                metadata={
                    "node_id": node_id,
                    "semantic_qa_report": semantic_qa_report,
                    "errors": error_messages,
                    "validation_source": "semantic_qa",
                },
            ), [], semantic_qa_report

        warnings = self._collect_semantic_warnings(semantic_qa_report)
        return None, warnings, semantic_qa_report

    async def _check_llm_qa(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
        errors: List[str],
        feedback: Dict[str, Any],
    ) -> None:
        """Run LLM QA if configured, appending errors in place."""
        task_ref = node_config.get("task_ref")
        qa_mode = node_config.get("qa_mode", "structural")

        if not (task_ref and self.llm_service and self.prompt_loader):
            return

        llm_result = await self._run_llm_qa(
            node_id, task_ref, document, context, qa_mode,
        )
        if not llm_result["passed"]:
            issues = llm_result.get("issues", [])
            if issues:
                errors.extend(issues)
            else:
                errors.append("QA check failed")
            feedback["llm_feedback"] = llm_result.get("feedback", "")

    def _extract_semantic_error_messages(
        self, report: Dict[str, Any],
    ) -> List[str]:
        """Extract error-level messages from a semantic QA report."""
        feedback = self._convert_semantic_findings_to_feedback(report)
        return [f["message"] for f in feedback if f.get("severity") == "error"]

    def _collect_semantic_warnings(
        self, report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Collect warning/info findings from a semantic QA report."""
        return [
            f for f in report.get("findings", [])
            if f.get("severity") in ("warning", "info")
        ]

    def _get_document_to_validate(
        self,
        context: DocumentWorkflowContext,
    ) -> Optional[Dict[str, Any]]:
        """Get the document to validate from context.

        Args:
            context: Workflow context

        Returns:
            Document dict or None
        """
        # Try document_content first (most recently produced)
        if context.document_content:
            # Get the most recent document
            for key in reversed(list(context.document_content.keys())):
                return context.document_content[key]

        # Fall back to input documents
        if context.input_documents:
            for key in context.input_documents:
                return context.input_documents[key]

        return None

    def _run_code_based_validation(
        self,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
    ) -> Optional[PromotionValidationResult]:
        """Run code-based validation before LLM QA.

        Checks for:
        - Promotion violations (should/could answers becoming constraints)
        - Internal contradictions (same concept in constraints and assumptions)
        - Policy conformance (prohibited terms in unknowns)
        - Grounding issues (guardrails not traceable to input)

        Per WS-PGC-VALIDATION-001 Phase 1.

        Args:
            document: The document to validate
            context: Workflow context with PGC data

        Returns:
            PromotionValidationResult or None if no PGC data available
        """
        # Get PGC data from context
        # These may come from context_state or be loaded separately
        pgc_questions = []
        pgc_answers = {}
        intake = None

        # Try to get from context_state if available
        if hasattr(context, "context_state") and context.context_state:
            # pgc_questions may be the full PGC document (dict with 'questions' key)
            # or just the list of questions - handle both cases
            raw_pgc_questions = context.context_state.get("pgc_questions", [])
            if isinstance(raw_pgc_questions, dict):
                pgc_questions = raw_pgc_questions.get("questions", [])
            else:
                pgc_questions = raw_pgc_questions
            pgc_answers = context.context_state.get("pgc_answers", {})
            intake = context.context_state.get("concierge_intake")

        # Also check direct context attributes
        if hasattr(context, "pgc_questions") and context.pgc_questions:
            pgc_questions = context.pgc_questions
        if hasattr(context, "pgc_answers") and context.pgc_answers:
            pgc_answers = context.pgc_answers
        if hasattr(context, "intake") and context.intake:
            intake = context.intake

        # If no PGC data available, skip validation
        if not pgc_questions and not pgc_answers:
            logger.debug("No PGC data available, skipping code-based validation")
            return None

        logger.info(
            f"Running code-based validation with {len(pgc_questions)} questions, "
            f"{len(pgc_answers)} answers"
        )

        validator = PromotionValidator()
        validation_input = PromotionValidationInput(
            pgc_questions=pgc_questions,
            pgc_answers=pgc_answers,
            generated_document=document,
            intake=intake,
        )

        return validator.validate(validation_input)

    def _run_drift_validation(
        self,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
    ) -> Optional[DriftValidationResult]:
        """Run constraint drift validation (ADR-042).

        Validates artifact against bound constraints (pgc_invariants) to detect:
        - QA-PGC-001: Contradictions of bound constraints (ERROR)
        - QA-PGC-002: Reopened decisions (ERROR)
        - QA-PGC-003: Silent omissions of constraints (WARNING)
        - QA-PGC-004: Missing traceability (WARNING)

        This runs FIRST, before promotion validation.

        Args:
            document: The document to validate
            context: Workflow context with pgc_invariants

        Returns:
            DriftValidationResult or None if no invariants available
        """
        # Get invariants from context_state
        invariants = []
        if hasattr(context, "context_state") and context.context_state:
            invariants = context.context_state.get("pgc_invariants", [])

        if not invariants:
            logger.debug("ADR-042: No invariants available, skipping drift validation")
            return None

        logger.info(f"ADR-042: Running drift validation against {len(invariants)} binding invariants")

        validator = ConstraintDriftValidator()
        return validator.validate(
            artifact=document,
            invariants=invariants,
        )

    async def _run_semantic_qa(
        self,
        node_id: str,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
    ) -> Optional[Dict[str, Any]]:
        """Run Layer 2 semantic QA validation (WS-SEMANTIC-QA-001).

        Delegates pure logic to semantic_qa_pure module for testability.
        """
        from app.domain.workflow.nodes.semantic_qa_pure import (
            extract_semantic_qa_inputs,
            build_semantic_qa_prompt,
            build_error_report,
        )

        # Check if semantic QA is enabled
        if not os.environ.get("SEMANTIC_QA_ENABLED", "true").lower() == "true":
            logger.info("Semantic QA disabled via SEMANTIC_QA_ENABLED=false")
            return None

        if not self.llm_service:
            logger.debug("No LLM service, skipping semantic QA")
            return None

        # Pure: extract inputs from context_state
        has_ctx = hasattr(context, "context_state") and context.context_state
        ctx_state = context.context_state if has_ctx else {}
        invariants, pgc_questions, pgc_answers = extract_semantic_qa_inputs(ctx_state)

        if not invariants:
            logger.debug("No invariants available, skipping semantic QA")
            return None

        logger.info(
            f"WS-SEMANTIC-QA-001: Running semantic QA against {len(invariants)} "
            f"binding invariants"
        )

        correlation_id = ""
        if hasattr(context, "extra") and context.extra:
            correlation_id = context.extra.get("execution_id", "")

        # Load policy prompt (I/O)
        try:
            from app.config.package_loader import get_package_loader
            task = get_package_loader().get_task("qa_semantic_compliance", "1.1.0")
            policy_prompt = task.content
        except Exception:
            logger.error("Semantic QA policy prompt not found via PackageLoader")
            policy_prompt = "# Semantic QA Policy\nEvaluate constraints for compliance."

        # Pure: build prompt
        message_content = build_semantic_qa_prompt(
            pgc_questions=pgc_questions,
            pgc_answers=pgc_answers,
            invariants=invariants,
            document=document,
            correlation_id=correlation_id,
            policy_prompt=policy_prompt,
        )

        try:
            execution_id = context.extra.get("execution_id") if hasattr(context, "extra") else None
            response = await self.llm_service.complete(
                messages=[{"role": "user", "content": message_content}],
                workflow_execution_id=execution_id,
                role="Semantic Compliance Auditor",
                task_ref="qa_semantic_compliance_v1.1",
                artifact_type=context.document_type,
                node_id=node_id,
                project_id=context.project_id,
            )

            report = self._parse_semantic_qa_response(
                response=response,
                expected_constraint_count=len(invariants),
                provided_constraint_ids=[inv.get("id", "") for inv in invariants],
            )

            return report

        except Exception as e:
            logger.exception(f"Semantic QA failed: {e}")
            return build_error_report(correlation_id, len(invariants), e)

    def _parse_semantic_qa_response(
        self,
        response: str,
        expected_constraint_count: int,
        provided_constraint_ids: List[str],
    ) -> Dict[str, Any]:
        """Parse and validate LLM response against schema.

        Args:
            response: Raw LLM response
            expected_constraint_count: Number of constraints provided
            provided_constraint_ids: List of valid constraint IDs

        Returns:
            Parsed and validated report dict

        Raises:
            ValueError: If response is invalid
        """
        # Extract JSON from response
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        try:
            report = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Semantic QA response is not valid JSON: {e}")
            raise ValueError(f"Invalid JSON response: {e}")

        # Load and validate against schema via PackageLoader (combine-config)
        try:
            from app.config.package_loader import get_package_loader
            schema_obj = get_package_loader().get_schema(
                "qa_semantic_compliance_output", "1.0.0"
            )
            jsonschema.validate(instance=report, schema=schema_obj.content)
        except jsonschema.ValidationError as e:
            logger.error(f"Semantic QA response failed schema validation: {e.message}")
            raise ValueError(f"Schema validation failed: {e.message}")
        except Exception as e:
            logger.warning(f"Schema not found via PackageLoader, skipping validation: {e}")

        # Validate contract rules
        self._validate_semantic_qa_contract(
            report=report,
            expected_constraint_count=expected_constraint_count,
            provided_constraint_ids=provided_constraint_ids,
        )

        return report

    def _validate_semantic_qa_contract(
        self,
        report: Dict[str, Any],
        expected_constraint_count: int,
        provided_constraint_ids: List[str],
    ) -> None:
        """Validate semantic QA contract rules.

        Delegates to qa_parsing.validate_semantic_qa_contract pure function.

        Args:
            report: Parsed report
            expected_constraint_count: Expected number of constraints
            provided_constraint_ids: Valid constraint IDs
        """
        from app.domain.workflow.nodes.qa_parsing import validate_semantic_qa_contract

        warnings = validate_semantic_qa_contract(
            report, expected_constraint_count, provided_constraint_ids
        )
        for warning in warnings:
            logger.warning(warning)

    def _convert_semantic_findings_to_feedback(
        self,
        report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Convert semantic QA findings to feedback format.

        Delegates to qa_parsing.convert_semantic_findings_to_feedback pure function.

        Args:
            report: Semantic QA report

        Returns:
            List of feedback issues compatible with remediation
        """
        from app.domain.workflow.nodes.qa_parsing import convert_semantic_findings_to_feedback

        return convert_semantic_findings_to_feedback(report)

    async def _run_llm_qa(
        self,
        node_id: str,
        task_ref: str,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
        qa_mode: str = "structural",
    ) -> Dict[str, Any]:
        """Run LLM-based quality assessment.

        Args:
            node_id: The QA node ID
            task_ref: Reference to QA prompt
            document: Document to validate
            context: Workflow context
            qa_mode: "structural" or "structural+intent"

        Returns:
            Dict with keys: passed, issues, feedback
        """
        try:
            # Load QA prompt
            qa_prompt = self.prompt_loader.load_task_prompt(task_ref)

            # Build the content based on qa_mode
            import json
            content_parts = [qa_prompt]

            # Include intent capsule for structural+intent mode
            if qa_mode == "structural+intent" and context.intent_capsule:
                content_parts.append(
                    f"\n\n## User Intent (for alignment validation)\n{context.intent_capsule}"
                )
                logger.info(f"QA mode: {qa_mode} - including intent capsule")
            else:
                logger.info(f"QA mode: {qa_mode} - structural validation only")

            content_parts.append(
                f"\n\nDocument to review:\n```json\n{json.dumps(document, indent=2)}\n```"
            )

            messages = [
                {
                    "role": "user",
                    "content": "".join(content_parts),
                }
            ]

            # Get LLM assessment with execution tracking
            execution_id = context.extra.get("execution_id")
            response = await self.llm_service.complete(
                messages,
                workflow_execution_id=execution_id,
                role="QA Validator",
                task_ref=task_ref,
                artifact_type=context.document_type,
                node_id=node_id,
                project_id=context.project_id,
            )

            # Log the raw response for debugging
            logger.info(f"QA LLM response (first 1500 chars): {response[:1500]}")

            # Parse response
            return self._parse_qa_response(response)

        except Exception as e:
            logger.exception(f"LLM QA for {node_id} failed: {e}")
            return {
                "passed": False,
                "issues": [f"LLM QA error: {str(e)}"],
                "feedback": "",
            }

    def _parse_qa_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM QA response.

        Delegates to qa_parsing.parse_qa_response pure function.

        Args:
            response: Raw LLM response

        Returns:
            Dict with passed, issues, feedback
        """
        from app.domain.workflow.nodes.qa_parsing import parse_qa_response

        result = parse_qa_response(response)
        logger.info(f"QA response parsed - passed: {result['passed']}")
        return result

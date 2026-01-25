"""QA node executor for Document Interaction Workflow Plans (ADR-039).

QA nodes validate generated documents against quality criteria.

Validation order (per ADR-042 and WS-PGC-VALIDATION-001):
1. Constraint drift validation (ADR-042) - fails fast on bound constraint violations
2. Promotion validation (WS-PGC-VALIDATION-001) - catches promotion and contradiction issues
3. Schema validation
4. LLM-based semantic QA
"""

import logging
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Protocol

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

        Args:
            node_id: The QA node ID
            node_config: Node configuration with task_ref, schema_ref
            context: Workflow context with document to validate
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with outcome "success" or "failed"
        """
        task_ref = node_config.get("task_ref")
        schema_ref = node_config.get("schema_ref")
        requires_qa = node_config.get("requires_qa", True)

        if not requires_qa:
            # QA not required, auto-pass
            logger.info(f"QA node {node_id} skipped (requires_qa=false)")
            return NodeResult.success(qa_skipped=True)

        # Get the document to validate
        document = self._get_document_to_validate(context)
        if not document:
            logger.warning(f"QA node {node_id}: No document to validate")
            return NodeResult.failed(
                reason="No document available for QA validation",
                node_id=node_id,
            )

        errors: List[str] = []
        feedback: Dict[str, Any] = {}
        code_validation_warnings: List[Dict[str, Any]] = []
        drift_warnings: List[Dict[str, Any]] = []

        # 1. Run constraint drift validation FIRST (ADR-042)
        # Fails fast if bound constraints are violated
        drift_result = self._run_drift_validation(
            document=document,
            context=context,
        )

        if drift_result is not None:
            if not drift_result.passed:
                # Log full error details for debugging
                for err in drift_result.errors:
                    logger.warning(
                        f"ADR-042 drift ERROR: {err.check_id} - {err.clarification_id}: {err.message}"
                    )
                for warn in drift_result.warnings:
                    logger.info(
                        f"ADR-042 drift WARNING: {warn.check_id} - {warn.clarification_id}: {warn.message}"
                    )
                logger.warning(
                    f"QA node {node_id} failed drift validation with "
                    f"{len(drift_result.errors)} errors"
                )
                return NodeResult(
                    outcome="failed",
                    metadata={
                        "node_id": node_id,
                        "drift_errors": [v.to_dict() for v in drift_result.errors],
                        "drift_warnings": [v.to_dict() for v in drift_result.warnings],
                        "validation_source": "constraint_drift",
                    },
                )

            # Collect drift warnings
            if drift_result.warnings:
                drift_warnings = [v.to_dict() for v in drift_result.warnings]
                logger.info(
                    f"QA node {node_id}: {len(drift_warnings)} drift validation warnings"
                )

        # 2. Run promotion validation (WS-PGC-VALIDATION-001)
        code_validation_result = self._run_code_based_validation(
            document=document,
            context=context,
        )

        if code_validation_result is not None:
            # Fail immediately on validation errors
            if not code_validation_result.passed:
                logger.warning(
                    f"QA node {node_id} failed code-based validation with "
                    f"{len(code_validation_result.errors)} errors"
                )
                return NodeResult(
                    outcome="failed",
                    metadata={
                        "node_id": node_id,
                        "validation_errors": [asdict(e) for e in code_validation_result.errors],
                        "validation_warnings": [asdict(w) for w in code_validation_result.warnings],
                        "validation_source": "code_based",
                    },
                )

            # Collect warnings for inclusion in final result
            if code_validation_result.warnings:
                code_validation_warnings = [asdict(w) for w in code_validation_result.warnings]
                logger.info(
                    f"QA node {node_id}: {len(code_validation_warnings)} code validation warnings"
                )

        # Run schema validation if configured
        if schema_ref and self.schema_validator:
            schema_valid, schema_errors = self.schema_validator.validate(
                document, schema_ref
            )
            if not schema_valid:
                errors.extend(schema_errors)
                feedback["schema_errors"] = schema_errors

        # Run LLM-based QA if configured
        # qa_mode: "structural" (default) or "structural+intent"
        qa_mode = node_config.get("qa_mode", "structural")

        if task_ref and self.llm_service and self.prompt_loader:
            llm_result = await self._run_llm_qa(
                node_id, task_ref, document, context, qa_mode
            )
            if not llm_result["passed"]:
                issues = llm_result.get("issues", [])
                if issues:
                    errors.extend(issues)
                else:
                    # Failed but no specific issues extracted
                    errors.append("QA check failed")
                feedback["llm_feedback"] = llm_result.get("feedback", "")

        # Determine outcome
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
        success_metadata = {
            "node_id": node_id,
            "qa_passed": True,
        }

        # Include drift warnings in success result (ADR-042)
        if drift_warnings:
            success_metadata["drift_warnings"] = drift_warnings

        # Include code validation warnings in success result
        if code_validation_warnings:
            success_metadata["code_validation_warnings"] = code_validation_warnings

        return NodeResult.success(**success_metadata)

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
            pgc_questions = context.context_state.get("pgc_questions", [])
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

        Args:
            response: Raw LLM response

        Returns:
            Dict with passed, issues, feedback
        """
        import json
        
        # First, try to parse as JSON (many QA prompts return structured JSON)
        try:
            # Strip markdown code fences if present
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "passed" in parsed:
                passed = bool(parsed["passed"])
                issues = parsed.get("issues", [])
                # Normalize issues to list of strings
                if issues and isinstance(issues[0], dict):
                    issues = [issue.get("message", str(issue)) for issue in issues]
                summary = parsed.get("summary", "")
                logger.info(f"QA response parsed as JSON - passed: {passed}")
                return {
                    "passed": passed,
                    "issues": issues,
                    "feedback": summary or response,
                }
        except (json.JSONDecodeError, TypeError, KeyError):
            pass  # Not valid JSON, fall through to text parsing
        
        response_lower = response.lower()

        # Look for explicit Result: PASS/FAIL from the QA prompt format
        # The prompt outputs: **Result:** PASS or **Result:** FAIL
        passed = False
        issues = []

        # Check for explicit Result line (matches prompt output format)
        result_match = re.search(r'\*?\*?result\*?\*?:?\s*(pass|fail)', response_lower)
        if result_match:
            passed = result_match.group(1) == "pass"
            logger.info(f"QA response parsed - Result: {'PASS' if passed else 'FAIL'}")
        # Fallback to keyword heuristics
        elif any(indicator in response_lower for indicator in [
            "passes all",
            "meets requirements",
            "approved",
            "no issues found",
            "quality: pass",
        ]):
            passed = True
            logger.info("QA response parsed via keyword heuristic - PASS")
        elif any(indicator in response_lower for indicator in [
            "fails",
            "issues found",
            "rejected",
            "needs revision",
            "quality: fail",
        ]):
            passed = False
            logger.info("QA response parsed via keyword heuristic - FAIL")
        else:
            # Ambiguous - default to pass with warning
            passed = True
            logger.warning("QA response ambiguous, defaulting to PASS")

        # Extract issues if failed
        if not passed:
            if "issues found" in response_lower or "### issues" in response_lower:
                # Find the issues section
                issues_start = response_lower.find("### issues")
                if issues_start == -1:
                    issues_start = response_lower.find("issues found")
                if issues_start != -1:
                    issues_section = response[issues_start:]
                    # Extract bullet points
                    for line in issues_section.split("\n")[1:10]:
                        line = line.strip()
                        if line and line.startswith(("-", "*", "Ã¢â‚¬Â¢", "[")):
                            # Clean up the line
                            cleaned = re.sub(r'^[-*Ã¢â‚¬Â¢\[\]]+\s*', '', line)
                            if cleaned and len(cleaned) > 5:
                                issues.append(cleaned)

        return {
            "passed": passed,
            "issues": issues,
            "feedback": response,
        }

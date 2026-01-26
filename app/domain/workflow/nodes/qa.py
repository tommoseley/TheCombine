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
import re
from dataclasses import asdict
from pathlib import Path
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

        # 3. Run semantic QA (Layer 2) - only if mechanical checks passed
        # This detects constraint violations requiring semantic understanding
        # (e.g., distinguishing follow-up questions from reopening decisions)
        semantic_qa_report = None
        semantic_warnings: List[Dict[str, Any]] = []

        try:
            semantic_qa_report = await self._run_semantic_qa(node_id, document, context)
        except ValueError as e:
            # Schema/contract validation failed - treat as error
            logger.error(f"Semantic QA validation error: {e}")
            errors.append(f"Semantic QA validation error: {str(e)}")

        if semantic_qa_report:
            if semantic_qa_report.get("gate") == "fail":
                # Convert findings to feedback format
                semantic_feedback = self._convert_semantic_findings_to_feedback(
                    semantic_qa_report
                )
                error_findings = [
                    f for f in semantic_feedback if f.get("severity") == "error"
                ]
                warning_findings = [
                    f for f in semantic_feedback if f.get("severity") == "warning"
                ]

                logger.warning(
                    f"QA node {node_id} failed semantic QA with "
                    f"{len(error_findings)} errors, {len(warning_findings)} warnings"
                )

                return NodeResult(
                    outcome="failed",
                    metadata={
                        "node_id": node_id,
                        "semantic_qa_report": semantic_qa_report,
                        "errors": [f["message"] for f in error_findings],
                        "validation_source": "semantic_qa",
                    },
                )

            # Collect semantic QA warnings for success result
            for finding in semantic_qa_report.get("findings", []):
                if finding.get("severity") in ["warning", "info"]:
                    semantic_warnings.append(finding)

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

        # Include semantic QA warnings in success result (WS-SEMANTIC-QA-001)
        if semantic_warnings:
            success_metadata["semantic_qa_warnings"] = semantic_warnings

        # Include full semantic QA report if available
        if semantic_qa_report:
            success_metadata["semantic_qa_report"] = semantic_qa_report

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

    async def _run_semantic_qa(
        self,
        node_id: str,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
    ) -> Optional[Dict[str, Any]]:
        """Run Layer 2 semantic QA validation (WS-SEMANTIC-QA-001).

        Uses LLM to evaluate bound constraints for semantic compliance that
        mechanical checks cannot detect (e.g., follow-up vs reopening questions).

        Args:
            node_id: QA node identifier
            document: Generated document to validate
            context: Workflow context with PGC data

        Returns:
            Parsed semantic QA report or None if skipped/disabled
        """
        # Check if semantic QA is enabled
        if not os.environ.get("SEMANTIC_QA_ENABLED", "true").lower() == "true":
            logger.info("Semantic QA disabled via SEMANTIC_QA_ENABLED=false")
            return None

        # Check if we have LLM service
        if not self.llm_service:
            logger.debug("No LLM service, skipping semantic QA")
            return None

        # Get invariants from context_state
        invariants = []
        if hasattr(context, "context_state") and context.context_state:
            invariants = context.context_state.get("pgc_invariants", [])

        if not invariants:
            logger.debug("No invariants available, skipping semantic QA")
            return None

        # Get PGC questions and answers
        pgc_questions = []
        pgc_answers = {}
        if hasattr(context, "context_state") and context.context_state:
            pgc_questions = context.context_state.get("pgc_questions", [])
            pgc_answers = context.context_state.get("pgc_answers", {})

        logger.info(
            f"WS-SEMANTIC-QA-001: Running semantic QA against {len(invariants)} "
            f"binding invariants"
        )

        # Get correlation ID for traceability
        correlation_id = ""
        if hasattr(context, "extra") and context.extra:
            correlation_id = context.extra.get("execution_id", "")

        # Build semantic QA context
        message_content = self._build_semantic_qa_context(
            pgc_questions=pgc_questions,
            pgc_answers=pgc_answers,
            invariants=invariants,
            document=document,
            correlation_id=correlation_id,
        )

        try:
            # Call LLM with semantic QA policy
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

            # Parse and validate response
            report = self._parse_semantic_qa_response(
                response=response,
                expected_constraint_count=len(invariants),
                provided_constraint_ids=[inv.get("id", "") for inv in invariants],
            )

            return report

        except Exception as e:
            logger.exception(f"Semantic QA failed: {e}")
            # Return a failing report on error
            return {
                "schema_version": "qa_semantic_compliance_output.v1",
                "correlation_id": correlation_id,
                "gate": "fail",
                "summary": {
                    "errors": 1,
                    "warnings": 0,
                    "infos": 0,
                    "expected_constraints": len(invariants),
                    "evaluated_constraints": 0,
                    "blocked_reasons": [f"Semantic QA error: {str(e)}"],
                },
                "coverage": {
                    "expected_count": len(invariants),
                    "evaluated_count": 0,
                    "items": [],
                },
                "findings": [
                    {
                        "severity": "error",
                        "code": "OTHER",
                        "constraint_id": "SYSTEM",
                        "message": f"Semantic QA execution failed: {str(e)}",
                        "evidence_pointers": [],
                    }
                ],
            }

    def _build_semantic_qa_context(
        self,
        pgc_questions: List[Dict[str, Any]],
        pgc_answers: Dict[str, Any],
        invariants: List[Dict[str, Any]],
        document: Dict[str, Any],
        correlation_id: str,
    ) -> str:
        """Assemble the inputs for semantic QA.

        Args:
            pgc_questions: PGC question definitions
            pgc_answers: User answers keyed by question ID
            invariants: Bound constraints to evaluate
            document: Generated document to audit
            correlation_id: Workflow correlation ID

        Returns:
            Formatted message content for LLM
        """
        # Load policy prompt
        policy_path = Path(__file__).parent.parent.parent.parent.parent / "seed" / "prompts" / "tasks" / "qa_semantic_compliance_v1.1.txt"
        try:
            policy_prompt = policy_path.read_text()
        except FileNotFoundError:
            logger.error(f"Semantic QA policy prompt not found at {policy_path}")
            policy_prompt = "# Semantic QA Policy\nEvaluate constraints for compliance."

        parts = [policy_prompt]

        # PGC Questions with answers
        parts.append("\n\n---\n\n## PGC Questions and Answers\n")
        for q in pgc_questions:
            qid = q.get("id", "UNKNOWN")
            answer = pgc_answers.get(qid)
            priority = q.get("priority", "could")
            answer_label = ""
            if isinstance(answer, dict):
                answer_label = answer.get("label", str(answer))
            elif answer is not None:
                answer_label = str(answer)
            parts.append(f"- {qid} (priority={priority}): {answer_label}\n")

        # Bound constraints
        parts.append("\n## Bound Constraints (MUST evaluate each)\n")
        for inv in invariants:
            cid = inv.get("id", "UNKNOWN")
            kind = inv.get("invariant_kind", "requirement")
            text = inv.get("normalized_text") or inv.get("user_answer_label") or str(inv.get("user_answer", ""))
            parts.append(f"- {cid} [{kind}]: {text}\n")

        # Document
        parts.append("\n## Generated Document\n```json\n")
        parts.append(json.dumps(document, indent=2))
        parts.append("\n```\n")

        # Correlation ID and output instructions
        parts.append(f"\ncorrelation_id for output: {correlation_id}\n")
        parts.append("\nOutput ONLY valid JSON matching qa_semantic_compliance_output.v1 schema. No prose.\n")

        return "".join(parts)

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

        # Load and validate against schema
        schema_path = Path(__file__).parent.parent.parent.parent.parent / "seed" / "schemas" / "qa_semantic_compliance_output.v1.json"
        try:
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(instance=report, schema=schema)
        except FileNotFoundError:
            logger.warning(f"Schema not found at {schema_path}, skipping validation")
        except jsonschema.ValidationError as e:
            logger.error(f"Semantic QA response failed schema validation: {e.message}")
            raise ValueError(f"Schema validation failed: {e.message}")

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

        Args:
            report: Parsed report
            expected_constraint_count: Expected number of constraints
            provided_constraint_ids: Valid constraint IDs

        Raises:
            ValueError: If contract rules are violated
        """
        coverage = report.get("coverage", {})
        findings = report.get("findings", [])
        summary = report.get("summary", {})
        gate = report.get("gate")

        # Rule 1: Coverage count must match
        if coverage.get("expected_count") != expected_constraint_count:
            logger.warning(
                f"Coverage expected_count mismatch: got {coverage.get('expected_count')}, "
                f"expected {expected_constraint_count}"
            )

        # Rule 2: All constraint IDs must be valid
        provided_ids_lower = [cid.lower() for cid in provided_constraint_ids]
        for item in coverage.get("items", []):
            cid = item.get("constraint_id", "")
            if cid.lower() not in provided_ids_lower and cid != "SYSTEM":
                logger.warning(f"Unknown constraint_id in coverage: {cid}")

        for finding in findings:
            cid = finding.get("constraint_id", "")
            if cid.lower() not in provided_ids_lower and cid != "SYSTEM":
                logger.warning(f"Unknown constraint_id in findings: {cid}")

        # Rule 3: Gate must be fail if any contradicted/reopened
        has_error_status = any(
            item.get("status") in ["contradicted", "reopened"]
            for item in coverage.get("items", [])
        )
        if has_error_status and gate != "fail":
            logger.warning(
                f"Gate should be 'fail' due to contradicted/reopened status, but got '{gate}'"
            )

        # Rule 4: Summary counts should match findings
        error_count = len([f for f in findings if f.get("severity") == "error"])
        warning_count = len([f for f in findings if f.get("severity") == "warning"])
        if summary.get("errors") != error_count:
            logger.warning(
                f"Summary errors mismatch: got {summary.get('errors')}, "
                f"counted {error_count}"
            )
        if summary.get("warnings") != warning_count:
            logger.warning(
                f"Summary warnings mismatch: got {summary.get('warnings')}, "
                f"counted {warning_count}"
            )

    def _convert_semantic_findings_to_feedback(
        self,
        report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Convert semantic QA findings to feedback format.

        Args:
            report: Semantic QA report

        Returns:
            List of feedback issues compatible with remediation
        """
        feedback_issues = []

        for finding in report.get("findings", []):
            feedback_issues.append({
                "type": "semantic_qa",
                "check_id": finding.get("code"),
                "severity": finding.get("severity"),
                "message": finding.get("message"),
                "constraint_id": finding.get("constraint_id"),
                "evidence_pointers": finding.get("evidence_pointers", []),
                "remediation": finding.get("suggested_fix"),
            })

        return feedback_issues

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

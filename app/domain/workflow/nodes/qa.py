"""QA node executor for Document Interaction Workflow Plans (ADR-039).

QA nodes validate generated documents against quality criteria.
"""

import logging
from typing import Any, Dict, List, Optional, Protocol

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    LLMService,
    NodeExecutor,
    NodeResult,
    PromptLoader,
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

        # Run schema validation if configured
        if schema_ref and self.schema_validator:
            schema_valid, schema_errors = self.schema_validator.validate(
                document, schema_ref
            )
            if not schema_valid:
                errors.extend(schema_errors)
                feedback["schema_errors"] = schema_errors

        # Run LLM-based QA if configured
        if task_ref and self.llm_service and self.prompt_loader:
            llm_result = await self._run_llm_qa(
                node_id, task_ref, document, context
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
        return NodeResult.success(
            node_id=node_id,
            qa_passed=True,
        )

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

    async def _run_llm_qa(
        self,
        node_id: str,
        task_ref: str,
        document: Dict[str, Any],
        context: DocumentWorkflowContext,
    ) -> Dict[str, Any]:
        """Run LLM-based quality assessment.

        Args:
            node_id: The QA node ID
            task_ref: Reference to QA prompt
            document: Document to validate
            context: Workflow context

        Returns:
            Dict with keys: passed, issues, feedback
        """
        try:
            # Load QA prompt
            qa_prompt = self.prompt_loader.load_task_prompt(task_ref)

            # Build messages
            import json
            messages = [
                {
                    "role": "user",
                    "content": f"{qa_prompt}\n\nDocument to review:\n```json\n{json.dumps(document, indent=2)}\n```",
                }
            ]

            # Get LLM assessment
            response = await self.llm_service.complete(messages)

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
        response_lower = response.lower()

        # Simple heuristic parsing
        # Look for explicit pass/fail indicators
        passed = False
        issues = []

        if any(indicator in response_lower for indicator in [
            "passes all",
            "meets requirements",
            "approved",
            "no issues found",
            "quality: pass",
        ]):
            passed = True
        elif any(indicator in response_lower for indicator in [
            "fails",
            "issues found",
            "rejected",
            "needs revision",
            "quality: fail",
        ]):
            passed = False
            # Extract issues if present
            if "issues:" in response_lower:
                issues_section = response[response_lower.index("issues:"):]
                # Simple line extraction
                for line in issues_section.split("\n")[1:5]:
                    line = line.strip()
                    if line and line.startswith(("-", "*", "•")):
                        issues.append(line.lstrip("-*• "))
        else:
            # Ambiguous - default to pass with warning
            passed = True
            logger.warning("QA response ambiguous, defaulting to pass")

        return {
            "passed": passed,
            "issues": issues,
            "feedback": response,
        }

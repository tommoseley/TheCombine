"""Mock node executors for testing (ADR-039).

These executors simulate workflow node behavior without actual LLM calls,
enabling end-to-end testing of the workflow engine.

Usage:
    from app.domain.workflow.nodes.mock_executors import create_mock_executors

    executors = create_mock_executors()
    executor = PlanExecutor(persistence, registry, executors=executors)
"""

import logging
from typing import Any, Dict

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)
from app.domain.workflow.plan_models import NodeType

logger = logging.getLogger(__name__)


class MockTaskExecutor(NodeExecutor):
    """Mock task executor that simulates document generation.

    Behavior:
    - Always succeeds after a simulated "generation"
    - Returns a mock document structure
    """

    def supported_node_type(self) -> NodeType:
        return NodeType.TASK

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        logger.info(f"MockTask [{node_id}] generating document")

        task_ref = node_config.get("task_ref", "unknown_task")
        produces = node_config.get("produces", "document")

        # Generate mock document content
        mock_document = {
            "type": produces,
            "generated_by": task_ref,
            "content": {
                "title": f"Generated {produces}",
                "summary": "This is a mock document generated for testing.",
                "sections": [
                    {"heading": "Overview", "content": "Mock overview content"},
                    {"heading": "Details", "content": "Mock details content"},
                ],
            },
            "metadata": {
                "project_id": context.project_id,
                "node_id": node_id,
            },
        }

        return NodeResult.success(
            produced_document=mock_document,
            task_ref=task_ref,
            produces=produces,
        )


class MockQAExecutor(NodeExecutor):
    """Mock QA executor that simulates quality assurance.

    Behavior:
    - First call: passes QA (success)
    - Can be configured to fail for testing retry logic
    """

    def __init__(self, fail_first_n: int = 0):
        """Initialize mock QA executor.

        Args:
            fail_first_n: Number of times to fail before passing (for retry testing)
        """
        self._fail_first_n = fail_first_n
        self._call_count: Dict[str, int] = {}

    def supported_node_type(self) -> NodeType:
        return NodeType.QA

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        doc_id = context.project_id
        key = f"{doc_id}:{node_id}"

        self._call_count[key] = self._call_count.get(key, 0) + 1
        call_num = self._call_count[key]

        logger.info(f"MockQA [{node_id}] call #{call_num}, fail_first_n={self._fail_first_n}")

        # Fail first N calls for testing retry logic
        if call_num <= self._fail_first_n:
            return NodeResult.failed(
                reason=f"Mock QA failure #{call_num}",
                issues=["Mock issue 1", "Mock issue 2"],
            )

        # Pass QA
        return NodeResult.success(
            qa_passed=True,
            qa_score=0.95,
            checks_performed=["completeness", "consistency", "clarity"],
        )


class MockGateExecutor(NodeExecutor):
    """Mock gate executor that simulates consent and outcome gates.

    Behavior:
    - Consent gates: requests user consent, then proceeds based on choice
    - Outcome gates: requests outcome selection from configured options
    """

    def supported_node_type(self) -> NodeType:
        return NodeType.GATE

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        requires_consent = node_config.get("requires_consent", False)
        gate_outcomes = node_config.get("gate_outcomes", [])

        selected_option_id = context.extra.get("selected_option_id", "")

        logger.info(f"MockGate [{node_id}] consent={requires_consent}, outcomes={gate_outcomes}, choice='{selected_option_id}'")

        # Consent gate
        if requires_consent:
            if not selected_option_id:
                return NodeResult(
                    outcome="needs_user_input",
                    requires_user_input=True,
                    user_prompt="Do you want to proceed with document generation?",
                    user_choices=["Yes, proceed", "No, I need more time"],
                )

            if "yes" in selected_option_id.lower() or "proceed" in selected_option_id.lower():
                return NodeResult.success(consent_given=True)
            else:
                return NodeResult(
                    outcome="blocked",
                    metadata={"reason": "User declined to proceed"},
                )

        # Outcome gate (e.g., qualified, not_ready, out_of_scope, redirect)
        if gate_outcomes:
            if not selected_option_id:
                return NodeResult(
                    outcome="needs_user_input",
                    requires_user_input=True,
                    user_prompt="Please select the intake outcome:",
                    user_choices=gate_outcomes,
                )

            # Return the selected outcome
            if selected_option_id in gate_outcomes:
                return NodeResult(
                    outcome=selected_option_id,
                    metadata={"gate_outcome": selected_option_id},
                )
            else:
                # Default to first outcome if invalid choice
                return NodeResult(
                    outcome=gate_outcomes[0],
                    metadata={"gate_outcome": gate_outcomes[0], "note": "defaulted"},
                )

        # Simple pass-through gate
        return NodeResult.success()


class MockEndExecutor(NodeExecutor):
    """Mock end executor that returns terminal outcomes.

    Behavior:
    - Returns the configured terminal_outcome
    """

    def supported_node_type(self) -> NodeType:
        return NodeType.END

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        terminal_outcome = node_config.get("terminal_outcome", "completed")
        gate_outcome = node_config.get("gate_outcome")

        logger.info(f"MockEnd [{node_id}] terminal={terminal_outcome}, gate={gate_outcome}")

        return NodeResult(
            outcome=terminal_outcome,
            metadata={
                "terminal_outcome": terminal_outcome,
                "gate_outcome": gate_outcome,
            },
        )


def create_mock_executors(qa_fail_first_n: int = 0) -> Dict[NodeType, NodeExecutor]:
    """Create a complete set of mock executors for testing.

    Args:
        qa_fail_first_n: Number of times QA should fail before passing
                        (useful for testing retry/circuit breaker logic)

    Returns:
        Dict mapping NodeType to mock executor instance
    """
    task_executor = MockTaskExecutor()
    return {
        NodeType.TASK: task_executor,
        NodeType.PGC: task_executor,  # PGC uses same executor as TASK
        NodeType.QA: MockQAExecutor(fail_first_n=qa_fail_first_n),
        NodeType.GATE: MockGateExecutor(),
        NodeType.END: MockEndExecutor(),
    }

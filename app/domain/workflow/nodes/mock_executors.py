"""Mock node executors for testing (ADR-039).

These executors simulate workflow node behavior without actual LLM calls,
enabling end-to-end testing of the workflow engine.

Usage:
    from app.domain.workflow.nodes.mock_executors import create_mock_executors

    executors = create_mock_executors()
    executor = PlanExecutor(persistence, registry, executors=executors)
"""

import logging
from typing import Any, Dict, List, Optional

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)
from app.domain.workflow.plan_models import NodeType

logger = logging.getLogger(__name__)


class MockConciergeExecutor(NodeExecutor):
    """Mock concierge executor that simulates conversation.

    Behavior:
    - First call: requests user input (asks a question)
    - Subsequent calls with user input: proceeds to success
    - Can be configured to return out_of_scope or redirect
    """

    def __init__(self):
        self._call_count: Dict[str, int] = {}

    def supported_node_type(self) -> NodeType:
        return NodeType.CONCIERGE

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        doc_id = context.document_id
        key = f"{doc_id}:{node_id}"

        self._call_count[key] = self._call_count.get(key, 0) + 1
        call_num = self._call_count[key]

        user_input = context.extra.get("user_input", "")
        user_choice = context.extra.get("user_choice", "")

        logger.info(f"MockConcierge [{node_id}] call #{call_num}, input='{user_input}', choice='{user_choice}'")

        # Check for special keywords in user input
        if "out of scope" in user_input.lower():
            return NodeResult(
                outcome="out_of_scope",
                metadata={"reason": "User indicated out of scope"},
            )

        if "redirect" in user_input.lower():
            return NodeResult(
                outcome="redirect",
                metadata={"reason": "User requested redirect"},
            )

        # First call without input - ask for user input
        if call_num == 1 and not user_input and not user_choice:
            return NodeResult(
                outcome="needs_user_input",
                requires_user_input=True,
                user_prompt="What would you like to build today? Please describe your project.",
                metadata={"question_type": "initial_intake"},
            )

        # Second call - ask follow-up question
        if call_num == 2 and user_input and "proceed" not in user_input.lower():
            return NodeResult(
                outcome="needs_user_input",
                requires_user_input=True,
                user_prompt="Thanks! Can you tell me more about the target users? Type 'proceed' when ready to continue.",
                metadata={"question_type": "follow_up"},
            )

        # Ready to proceed
        return NodeResult(
            outcome="success",
            metadata={
                "conversation_summary": f"User wants to build: {user_input}",
                "questions_asked": call_num,
            },
        )


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
                "document_id": context.document_id,
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
        doc_id = context.document_id
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

        user_choice = context.extra.get("user_choice", "")

        logger.info(f"MockGate [{node_id}] consent={requires_consent}, outcomes={gate_outcomes}, choice='{user_choice}'")

        # Consent gate
        if requires_consent:
            if not user_choice:
                return NodeResult(
                    outcome="needs_user_input",
                    requires_user_input=True,
                    user_prompt="Do you want to proceed with document generation?",
                    user_choices=["Yes, proceed", "No, I need more time"],
                )

            if "yes" in user_choice.lower() or "proceed" in user_choice.lower():
                return NodeResult.success(consent_given=True)
            else:
                return NodeResult(
                    outcome="blocked",
                    metadata={"reason": "User declined to proceed"},
                )

        # Outcome gate (e.g., qualified, not_ready, out_of_scope, redirect)
        if gate_outcomes:
            if not user_choice:
                return NodeResult(
                    outcome="needs_user_input",
                    requires_user_input=True,
                    user_prompt="Please select the intake outcome:",
                    user_choices=gate_outcomes,
                )

            # Return the selected outcome
            if user_choice in gate_outcomes:
                return NodeResult(
                    outcome=user_choice,
                    metadata={"gate_outcome": user_choice},
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
    return {
        NodeType.CONCIERGE: MockConciergeExecutor(),
        NodeType.TASK: MockTaskExecutor(),
        NodeType.QA: MockQAExecutor(fail_first_n=qa_fail_first_n),
        NodeType.GATE: MockGateExecutor(),
        NodeType.END: MockEndExecutor(),
    }

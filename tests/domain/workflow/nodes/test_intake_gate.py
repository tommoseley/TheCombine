"""Tests for IntakeGateExecutor.

The intake gate replaces multi-turn concierge with single-pass classification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.workflow.nodes.base import DocumentWorkflowContext
from app.domain.workflow.nodes.intake_gate import (
    IntakeGateExecutor,
    MIN_SUBSTANTIAL_LENGTH,
    MIN_STRUCTURE_INDICATORS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = MagicMock()
    service.complete = AsyncMock()
    return service


@pytest.fixture
def mock_prompt_loader():
    """Create a mock prompt loader."""
    loader = MagicMock()
    loader.load_task_prompt = MagicMock(return_value="Test intake gate prompt")
    return loader


@pytest.fixture
def executor(mock_llm_service, mock_prompt_loader):
    """Create an IntakeGateExecutor with mocks."""
    return IntakeGateExecutor(
        llm_service=mock_llm_service,
        prompt_loader=mock_prompt_loader,
    )


@pytest.fixture
def executor_no_llm():
    """Create an IntakeGateExecutor without LLM (fast path only)."""
    return IntakeGateExecutor(llm_service=None, prompt_loader=None)


@pytest.fixture
def context():
    """Create a basic workflow context."""
    return DocumentWorkflowContext(
        document_id="doc-123",
        document_type="test_document",
    )


@pytest.fixture
def state_snapshot():
    """Create a basic state snapshot."""
    return {"execution_id": "exec-123"}


# =============================================================================
# Basic Tests
# =============================================================================

class TestIntakeGateBasics:
    """Basic functionality tests."""

    def test_supported_node_type(self, executor):
        """Executor reports correct node type."""
        assert executor.get_supported_node_type() == "intake_gate"

    @pytest.mark.asyncio
    async def test_no_input_requests_input(self, executor, context, state_snapshot):
        """Empty input requests user to provide request."""
        context.extra["user_input"] = ""

        result = await executor.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        assert result.requires_user_input is True
        assert "describe" in result.user_prompt.lower()


# =============================================================================
# Fast Path Tests
# =============================================================================

class TestFastPath:
    """Tests for fast path (zero LLM calls)."""

    @pytest.mark.asyncio
    async def test_substantial_input_triggers_fast_path(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """Substantial structured input skips LLM call."""
        # Input with structure (bullets, length)
        context.extra["user_input"] = """
I need an inventory management system for my warehouse.

Requirements:
- Track stock levels across multiple locations
- Generate automatic low-stock alerts
- Support barcode scanning for receiving
- Provide daily inventory reports

We currently use spreadsheets but need something more robust.
"""

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Should be qualified without LLM call
        assert result.outcome == "qualified"
        assert result.metadata.get("source") == "fast_path"
        mock_llm_service.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_short_input_does_not_trigger_fast_path(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """Short input requires LLM classification."""
        mock_llm_service.complete = AsyncMock(return_value='''
{
    "classification": "insufficient",
    "missing": ["What do you want to build?"]
}
''')

        context.extra["user_input"] = "I want an app"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Should call LLM
        mock_llm_service.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_fast_path_extracts_project_type_greenfield(
        self, executor_no_llm, context, state_snapshot
    ):
        """Fast path correctly infers greenfield project type."""
        context.extra["user_input"] = """
I want to build a new task management application from scratch.

It should have:
- User authentication
- Task creation and assignment
- Due date tracking
- Email notifications

This is a brand new project with no existing code.
"""

        result = await executor_no_llm.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "qualified"
        assert result.metadata.get("project_type") == "greenfield"

    @pytest.mark.asyncio
    async def test_fast_path_extracts_project_type_enhancement(
        self, executor_no_llm, context, state_snapshot
    ):
        """Fast path correctly infers enhancement project type."""
        context.extra["user_input"] = """
I need to add new features to our existing CRM system.

We currently have:
- Contact management
- Basic reporting

We want to add:
- Email integration
- Calendar sync
- Mobile app support

The existing system is built in Django.
"""

        result = await executor_no_llm.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "qualified"
        assert result.metadata.get("project_type") == "enhancement"


# =============================================================================
# LLM Classification Tests
# =============================================================================

class TestLLMClassification:
    """Tests for LLM-based classification."""

    @pytest.mark.asyncio
    async def test_qualified_response(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """LLM qualified response returns success."""
        mock_llm_service.complete = AsyncMock(return_value='''
```json
{
    "classification": "qualified",
    "project_type": "greenfield",
    "intake_summary": "User wants to build an inventory system"
}
```
''')

        context.extra["user_input"] = "I need an inventory system"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "qualified"
        assert result.metadata.get("project_type") == "greenfield"
        assert "inventory" in result.metadata.get("intake_summary", "").lower()

    @pytest.mark.asyncio
    async def test_insufficient_response(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """LLM insufficient response requests more info."""
        mock_llm_service.complete = AsyncMock(return_value='''
{
    "classification": "insufficient",
    "missing": ["What problem are you trying to solve?", "What type of users will use this?"]
}
''')

        context.extra["user_input"] = "I want to build something"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        assert "problem" in result.user_prompt.lower()

    @pytest.mark.asyncio
    async def test_out_of_scope_response(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """LLM out_of_scope response returns out_of_scope outcome."""
        mock_llm_service.complete = AsyncMock(return_value='''
{
    "classification": "out_of_scope",
    "reason": "We do not provide hacking services"
}
''')

        context.extra["user_input"] = "Help me hack a website"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "out_of_scope"
        assert "reason" in result.metadata

    @pytest.mark.asyncio
    async def test_redirect_response(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """LLM redirect response returns redirect outcome."""
        mock_llm_service.complete = AsyncMock(return_value='''
{
    "classification": "redirect",
    "reason": "This is a billing question - please contact support"
}
''')

        context.extra["user_input"] = "I need to update my payment method"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "redirect"
        assert "billing" in result.metadata.get("reason", "").lower()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_llm_error_fails_open(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """LLM error results in qualified (fail open)."""
        mock_llm_service.complete = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        context.extra["user_input"] = "I need an inventory system"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Should fail open - let it through
        assert result.outcome == "qualified"
        assert "llm_error_fallback" in result.metadata.get("source", "")

    @pytest.mark.asyncio
    async def test_invalid_json_infers_from_text(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """Invalid JSON response infers classification from text."""
        mock_llm_service.complete = AsyncMock(
            return_value="This request is out of scope for our services."
        )

        context.extra["user_input"] = "Can you hack something?"

        result = await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "out_of_scope"

    @pytest.mark.asyncio
    async def test_no_llm_defaults_to_qualified(
        self, executor_no_llm, context, state_snapshot
    ):
        """Without LLM and below fast path threshold, defaults to qualified."""
        # Short input that doesn't trigger fast path
        context.extra["user_input"] = "Build me a CRM system with contacts and deals"

        result = await executor_no_llm.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "qualified"
        assert "no_llm_fallback" in result.metadata.get("source", "")


# =============================================================================
# Single LLM Call Verification
# =============================================================================

class TestSingleLLMCall:
    """Tests verifying only one LLM call is made."""

    @pytest.mark.asyncio
    async def test_exactly_one_llm_call(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """Intake gate makes exactly one LLM call (not a conversation)."""
        mock_llm_service.complete = AsyncMock(return_value='''
{
    "classification": "qualified",
    "project_type": "greenfield",
    "intake_summary": "Test"
}
''')

        context.extra["user_input"] = "Build a todo app"

        await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Exactly one call
        assert mock_llm_service.complete.call_count == 1

    @pytest.mark.asyncio
    async def test_no_conversation_history_passed(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """LLM call receives single message, not conversation history."""
        mock_llm_service.complete = AsyncMock(return_value='{"classification": "qualified"}')

        # Add some conversation history (should be ignored)
        context.conversation_history = [
            {"role": "user", "content": "Previous message 1"},
            {"role": "assistant", "content": "Previous response 1"},
            {"role": "user", "content": "Previous message 2"},
        ]
        context.extra["user_input"] = "Current request"

        await executor.execute(
            node_id="intake",
            node_config={"task_ref": "Intake Gate v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Check the messages passed to LLM
        call_kwargs = mock_llm_service.complete.call_args
        if call_kwargs.args:
            messages = call_kwargs.args[0]
        else:
            messages = call_kwargs.kwargs.get("messages", [])

        # Should only have ONE message (current request)
        assert len(messages) == 1
        assert messages[0]["content"] == "Current request"

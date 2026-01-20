"""
Tests for Intake Workflow BFF context builders (WS-ADR-025).

Tests the template context builder functions that transform workflow state
into view-ready data for the intake workflow UI.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)
from app.web.routes.public.intake_workflow_routes import (
    _build_template_context,
    _build_message_context,
    _build_completion_context,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_request():
    """Create mock request object."""
    return MagicMock()


@pytest.fixture
def base_state():
    """Create base workflow state for testing."""
    return DocumentWorkflowState(
        execution_id="exec-123",
        workflow_id="wf-intake",
        document_id="doc-456",
        document_type="concierge_intake",
        current_node_id="concierge",
        status=DocumentWorkflowStatus.RUNNING,
    )


@pytest.fixture
def paused_state(base_state):
    """Create paused workflow state."""
    base_state.set_paused(
        prompt="What is the main goal of your project?",
        choices=None,
    )
    return base_state


@pytest.fixture
def state_with_choices(base_state):
    """Create state with pending choices (gate decision)."""
    base_state.set_paused(
        prompt="Based on your requirements, please select an outcome:",
        choices=["qualified", "not_ready", "out_of_scope"],
    )
    return base_state


@pytest.fixture
def state_with_history(base_state):
    """Create state with conversation history."""
    base_state.record_execution(
        node_id="concierge",
        outcome="continue",
        metadata={
            "user_input": "I want to build a mobile app",
            "response": "That sounds interesting! Can you tell me more about the target platform?",
        },
    )
    base_state.record_execution(
        node_id="concierge",
        outcome="continue",
        metadata={
            "user_input": "iOS and Android",
            "response": "Great, cross-platform development. What's your timeline?",
        },
    )
    return base_state


@pytest.fixture
def completed_state(base_state):
    """Create completed workflow state."""
    base_state.set_completed(
        terminal_outcome="stabilized",
        gate_outcome="qualified",
    )
    return base_state


@pytest.fixture
def escalation_state(base_state):
    """Create state with escalation active."""
    base_state.set_escalation(["retry", "skip", "escalate_to_human"])
    return base_state


# =============================================================================
# Test: _build_template_context
# =============================================================================


class TestBuildTemplateContext:
    """Tests for _build_template_context function."""

    def test_basic_state_fields(self, mock_request, base_state):
        """Test basic state fields are included in context."""
        context = _build_template_context(mock_request, base_state)

        assert context["request"] == mock_request
        assert context["execution_id"] == "exec-123"
        assert context["document_id"] == "doc-456"
        assert context["status"] == "running"
        assert context["current_node"] == "concierge"

    def test_empty_messages_initially(self, mock_request, base_state):
        """Test messages list is empty when no history."""
        context = _build_template_context(mock_request, base_state)

        assert context["messages"] == []

    def test_messages_extracted_from_history(self, mock_request, state_with_history):
        """Test conversation messages are extracted from node history."""
        context = _build_template_context(mock_request, state_with_history)

        messages = context["messages"]
        assert len(messages) == 4  # 2 user + 2 assistant

        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "I want to build a mobile app"

        assert messages[1]["role"] == "assistant"
        assert "target platform" in messages[1]["content"]

        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "iOS and Android"

        assert messages[3]["role"] == "assistant"
        assert "timeline" in messages[3]["content"]

    def test_pause_state_flags(self, mock_request, paused_state):
        """Test pause state flags are set correctly."""
        context = _build_template_context(mock_request, paused_state)

        assert context["pending_user_input"] is True
        assert context["pending_prompt"] == "What is the main goal of your project?"
        assert context["is_paused"] is True
        assert context["is_completed"] is False

    def test_pending_choices(self, mock_request, state_with_choices):
        """Test pending choices are included."""
        context = _build_template_context(mock_request, state_with_choices)

        assert context["pending_choices"] == ["qualified", "not_ready", "out_of_scope"]

    def test_escalation_fields(self, mock_request, escalation_state):
        """Test escalation fields are included."""
        context = _build_template_context(mock_request, escalation_state)

        assert context["escalation_active"] is True
        assert context["escalation_options"] == ["retry", "skip", "escalate_to_human"]

    def test_completion_flags(self, mock_request, completed_state):
        """Test completion flags are set correctly."""
        context = _build_template_context(mock_request, completed_state)

        assert context["is_completed"] is True
        assert context["is_paused"] is False
        assert context["gate_outcome"] == "qualified"
        assert context["terminal_outcome"] == "stabilized"

    def test_running_state_flags(self, mock_request, base_state):
        """Test running state has correct flags."""
        context = _build_template_context(mock_request, base_state)

        assert context["is_completed"] is False
        assert context["is_paused"] is False
        assert context["pending_user_input"] is False


# =============================================================================
# Test: _build_message_context
# =============================================================================


class TestBuildMessageContext:
    """Tests for _build_message_context function."""

    def test_basic_fields(self, mock_request, base_state):
        """Test basic fields are included."""
        context = _build_message_context(mock_request, base_state, "Hello")

        assert context["request"] == mock_request
        assert context["execution_id"] == "exec-123"
        assert context["user_message"] is None  # Shown optimistically in frontend

    def test_assistant_response_from_history(self, mock_request, state_with_history):
        """Test assistant response is extracted from last history entry."""
        context = _build_message_context(
            mock_request, state_with_history, "iOS and Android"
        )

        assert "timeline" in context["assistant_response"]

    def test_fallback_to_pending_prompt(self, mock_request, paused_state):
        """Test fallback to pending_prompt when no history response."""
        context = _build_message_context(mock_request, paused_state, "Hello")

        assert context["assistant_response"] == "What is the main goal of your project?"

    def test_state_flags(self, mock_request, paused_state):
        """Test state flags are included."""
        context = _build_message_context(mock_request, paused_state, "Hello")

        assert context["is_paused"] is True
        assert context["is_completed"] is False

    def test_pending_choices_included(self, mock_request, state_with_choices):
        """Test pending choices are included."""
        context = _build_message_context(mock_request, state_with_choices, "Select")

        assert context["pending_choices"] == ["qualified", "not_ready", "out_of_scope"]


# =============================================================================
# Test: _build_completion_context
# =============================================================================


class TestBuildCompletionContext:
    """Tests for _build_completion_context function."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_qualified_outcome(self, mock_request, base_state, mock_db):
        """Test qualified outcome display (no project created in mock)."""
        base_state.set_completed(
            terminal_outcome="stabilized", gate_outcome="qualified"
        )
        # Note: mock db won't actually create project, so outcome is "Project Qualified"
        context = await _build_completion_context(mock_request, base_state, mock_db, None)

        assert context["execution_id"] == "exec-123"
        assert context["gate_outcome"] == "qualified"
        assert context["terminal_outcome"] == "stabilized"
        assert context["outcome_title"] == "Project Qualified"
        assert "PM Discovery" in context["outcome_description"]
        assert context["outcome_color"] == "green"
        assert context["next_action"] == "View Discovery Document"

    @pytest.mark.asyncio
    async def test_not_ready_outcome(self, mock_request, base_state, mock_db):
        """Test not_ready outcome display."""
        base_state.set_completed(
            terminal_outcome="blocked", gate_outcome="not_ready"
        )
        context = await _build_completion_context(mock_request, base_state, mock_db, None)

        assert context["outcome_title"] == "Not Ready"
        assert "Additional information" in context["outcome_description"]
        assert context["outcome_color"] == "yellow"
        assert context["next_action"] == "Start Over"

    @pytest.mark.asyncio
    async def test_out_of_scope_outcome(self, mock_request, base_state, mock_db):
        """Test out_of_scope outcome display."""
        base_state.set_completed(
            terminal_outcome="abandoned", gate_outcome="out_of_scope"
        )
        context = await _build_completion_context(mock_request, base_state, mock_db, None)

        assert context["outcome_title"] == "Out of Scope"
        assert "outside the scope" in context["outcome_description"]
        assert context["outcome_color"] == "gray"
        assert context["next_action"] is None

    @pytest.mark.asyncio
    async def test_redirect_outcome(self, mock_request, base_state, mock_db):
        """Test redirect outcome display."""
        base_state.set_completed(
            terminal_outcome="stabilized", gate_outcome="redirect"
        )
        context = await _build_completion_context(mock_request, base_state, mock_db, None)

        assert context["outcome_title"] == "Redirected"
        assert "engagement type" in context["outcome_description"]
        assert context["outcome_color"] == "blue"
        assert context["next_action"] is None

    @pytest.mark.asyncio
    async def test_unknown_outcome_fallback(self, mock_request, base_state, mock_db):
        """Test fallback for unknown outcome."""
        base_state.set_completed(
            terminal_outcome="custom", gate_outcome="unknown_gate"
        )
        context = await _build_completion_context(mock_request, base_state, mock_db, None)

        assert context["outcome_title"] == "Complete"
        assert "completed" in context["outcome_description"].lower()
        assert context["outcome_color"] == "gray"
        assert context["next_action"] is None


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_history_with_missing_metadata(self, mock_request, base_state):
        """Test handling of history entries with missing metadata."""
        base_state.record_execution(
            node_id="concierge",
            outcome="continue",
            metadata={},  # No user_input or response
        )
        base_state.record_execution(
            node_id="concierge",
            outcome="continue",
            metadata={"user_input": "Hello"},  # Only user input
        )

        context = _build_template_context(mock_request, base_state)

        # Should only have the user message from second execution
        assert len(context["messages"]) == 1
        assert context["messages"][0]["role"] == "user"
        assert context["messages"][0]["content"] == "Hello"

    def test_none_pending_fields(self, mock_request, base_state):
        """Test handling of None values in pending fields."""
        context = _build_template_context(mock_request, base_state)

        assert context["pending_prompt"] is None
        assert context["pending_choices"] is None
        assert context["gate_outcome"] is None
        assert context["terminal_outcome"] is None

    def test_empty_escalation_options(self, mock_request, base_state):
        """Test empty escalation options."""
        context = _build_template_context(mock_request, base_state)

        assert context["escalation_active"] is False
        assert context["escalation_options"] == []

    def test_message_context_empty_history(self, mock_request, base_state):
        """Test message context with empty history."""
        context = _build_message_context(mock_request, base_state, "Hello")

        # Should use pending_prompt as fallback (None in this case)
        assert context["assistant_response"] is None

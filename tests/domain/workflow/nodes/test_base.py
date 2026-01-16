"""Tests for node executor base classes (ADR-039)."""

import pytest

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    DocumentWorkflowStatus,
    NodeResult,
)


class TestNodeResult:
    """Tests for NodeResult dataclass."""

    def test_success_factory(self):
        """success() creates a success result."""
        result = NodeResult.success(
            produced_document={"key": "value"},
            custom_meta="test",
        )

        assert result.outcome == "success"
        assert result.produced_document == {"key": "value"}
        assert result.metadata["custom_meta"] == "test"
        assert result.requires_user_input is False

    def test_failed_factory(self):
        """failed() creates a failed result."""
        result = NodeResult.failed(
            reason="Something went wrong",
            error_code=500,
        )

        assert result.outcome == "failed"
        assert result.metadata["failure_reason"] == "Something went wrong"
        assert result.metadata["error_code"] == 500

    def test_needs_user_input_factory(self):
        """needs_user_input() creates a user input request."""
        result = NodeResult.needs_user_input(
            prompt="What is your name?",
            choices=["Alice", "Bob"],
            question_type="name",
        )

        assert result.outcome == "needs_user_input"
        assert result.requires_user_input is True
        assert result.user_prompt == "What is your name?"
        assert result.user_choices == ["Alice", "Bob"]
        assert result.metadata["question_type"] == "name"

    def test_default_values(self):
        """Default values are set correctly."""
        result = NodeResult(outcome="test")

        assert result.produced_document is None
        assert result.requires_user_input is False
        assert result.user_prompt is None
        assert result.user_choices is None
        assert result.metadata == {}


class TestDocumentWorkflowContext:
    """Tests for DocumentWorkflowContext."""

    def test_initialization(self):
        """Context initializes with required fields."""
        context = DocumentWorkflowContext(
            document_id="doc-123",
            document_type="test_document",
        )

        assert context.document_id == "doc-123"
        assert context.document_type == "test_document"
        assert context.thread_id is None
        assert context.document_content == {}
        assert context.conversation_history == []

    def test_add_message(self):
        """add_message adds to conversation history."""
        context = DocumentWorkflowContext(
            document_id="doc-123",
            document_type="test",
        )

        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there!")

        assert len(context.conversation_history) == 2
        assert context.conversation_history[0] == {"role": "user", "content": "Hello"}
        assert context.conversation_history[1] == {"role": "assistant", "content": "Hi there!"}

    def test_get_last_assistant_message(self):
        """get_last_assistant_message returns last assistant message."""
        context = DocumentWorkflowContext(
            document_id="doc-123",
            document_type="test",
        )

        context.add_message("user", "Hello")
        context.add_message("assistant", "First response")
        context.add_message("user", "More")
        context.add_message("assistant", "Second response")

        assert context.get_last_assistant_message() == "Second response"

    def test_get_last_assistant_message_none(self):
        """get_last_assistant_message returns None if no assistant messages."""
        context = DocumentWorkflowContext(
            document_id="doc-123",
            document_type="test",
        )

        context.add_message("user", "Hello")

        assert context.get_last_assistant_message() is None

    def test_user_responses(self):
        """set_user_response and get_user_response work correctly."""
        context = DocumentWorkflowContext(
            document_id="doc-123",
            document_type="test",
        )

        context.set_user_response("answer", "42")
        context.set_user_response("consent", True)

        assert context.get_user_response("answer") == "42"
        assert context.get_user_response("consent") is True
        assert context.get_user_response("missing") is None
        assert context.get_user_response("missing", "default") == "default"


class TestDocumentWorkflowStatus:
    """Tests for DocumentWorkflowStatus enum."""

    def test_status_values(self):
        """All expected status values exist."""
        assert DocumentWorkflowStatus.PENDING.value == "pending"
        assert DocumentWorkflowStatus.RUNNING.value == "running"
        assert DocumentWorkflowStatus.PAUSED.value == "paused"
        assert DocumentWorkflowStatus.COMPLETED.value == "completed"
        assert DocumentWorkflowStatus.FAILED.value == "failed"

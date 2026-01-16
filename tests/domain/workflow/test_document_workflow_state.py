"""Tests for DocumentWorkflowState (ADR-039)."""

import pytest
from datetime import datetime

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)


class TestNodeExecution:
    """Tests for NodeExecution dataclass."""

    def test_to_dict(self):
        """NodeExecution serializes to dict."""
        ts = datetime(2026, 1, 16, 12, 0, 0)
        execution = NodeExecution(
            node_id="test_node",
            outcome="success",
            timestamp=ts,
            metadata={"key": "value"},
        )

        data = execution.to_dict()

        assert data["node_id"] == "test_node"
        assert data["outcome"] == "success"
        assert data["timestamp"] == "2026-01-16T12:00:00"
        assert data["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """NodeExecution deserializes from dict."""
        data = {
            "node_id": "test_node",
            "outcome": "success",
            "timestamp": "2026-01-16T12:00:00",
            "metadata": {"key": "value"},
        }

        execution = NodeExecution.from_dict(data)

        assert execution.node_id == "test_node"
        assert execution.outcome == "success"
        assert execution.timestamp == datetime(2026, 1, 16, 12, 0, 0)


class TestDocumentWorkflowState:
    """Tests for DocumentWorkflowState."""

    @pytest.fixture
    def state(self):
        """Create a basic workflow state."""
        return DocumentWorkflowState(
            execution_id="exec-123",
            workflow_id="concierge_intake",
            document_id="doc-456",
            document_type="concierge_intake",
            current_node_id="clarification",
            status=DocumentWorkflowStatus.RUNNING,
        )

    def test_initialization(self, state):
        """State initializes with required fields."""
        assert state.execution_id == "exec-123"
        assert state.workflow_id == "concierge_intake"
        assert state.document_id == "doc-456"
        assert state.current_node_id == "clarification"
        assert state.status == DocumentWorkflowStatus.RUNNING
        assert state.node_history == []
        assert state.retry_counts == {}

    def test_record_execution(self, state):
        """record_execution adds to history."""
        state.record_execution(
            node_id="clarification",
            outcome="success",
            metadata={"turns": 3},
        )

        assert len(state.node_history) == 1
        assert state.node_history[0].node_id == "clarification"
        assert state.node_history[0].outcome == "success"
        assert state.node_history[0].metadata == {"turns": 3}

    def test_increment_retry(self, state):
        """increment_retry increases retry count."""
        assert state.get_retry_count("generation") == 0

        count1 = state.increment_retry("generation")
        assert count1 == 1
        assert state.get_retry_count("generation") == 1

        count2 = state.increment_retry("generation")
        assert count2 == 2
        assert state.get_retry_count("generation") == 2

    def test_retry_count_scoped_to_node(self, state):
        """Retry counts are scoped per node."""
        state.increment_retry("node_a")
        state.increment_retry("node_a")
        state.increment_retry("node_b")

        assert state.get_retry_count("node_a") == 2
        assert state.get_retry_count("node_b") == 1
        assert state.get_retry_count("node_c") == 0

    def test_set_paused(self, state):
        """set_paused updates status and pause fields."""
        state.set_paused(
            prompt="What is your project about?",
            choices=["Option A", "Option B"],
        )

        assert state.status == DocumentWorkflowStatus.PAUSED
        assert state.pending_user_input is True
        assert state.pending_prompt == "What is your project about?"
        assert state.pending_choices == ["Option A", "Option B"]

    def test_clear_pause(self, state):
        """clear_pause resets pause state."""
        state.set_paused(prompt="Question?")
        state.clear_pause()

        assert state.status == DocumentWorkflowStatus.RUNNING
        assert state.pending_user_input is False
        assert state.pending_prompt is None
        assert state.pending_choices is None

    def test_set_escalation(self, state):
        """set_escalation activates escalation mode."""
        state.set_escalation(["ask_more_questions", "narrow_scope", "abandon"])

        assert state.escalation_active is True
        assert state.escalation_options == ["ask_more_questions", "narrow_scope", "abandon"]
        assert state.status == DocumentWorkflowStatus.PAUSED

    def test_clear_escalation(self, state):
        """clear_escalation resets escalation state."""
        state.set_escalation(["option1"])
        state.clear_escalation()

        assert state.escalation_active is False
        assert state.escalation_options == []

    def test_set_completed(self, state):
        """set_completed sets terminal outcomes."""
        state.set_completed(
            terminal_outcome="stabilized",
            gate_outcome="qualified",
        )

        assert state.status == DocumentWorkflowStatus.COMPLETED
        assert state.terminal_outcome == "stabilized"
        assert state.gate_outcome == "qualified"

    def test_set_failed(self, state):
        """set_failed sets failed status and records execution."""
        state.set_failed("Connection timeout")

        assert state.status == DocumentWorkflowStatus.FAILED
        assert len(state.node_history) == 1
        assert state.node_history[0].outcome == "failed"
        assert "timeout" in state.node_history[0].metadata.get("failure_reason", "").lower()

    def test_serialization_roundtrip(self, state):
        """State serializes and deserializes correctly."""
        state.record_execution("clarification", "success")
        state.increment_retry("generation")
        state.set_completed("stabilized", "qualified")
        state.thread_id = "thread-789"

        data = state.to_dict()
        restored = DocumentWorkflowState.from_dict(data)

        assert restored.execution_id == state.execution_id
        assert restored.workflow_id == state.workflow_id
        assert restored.current_node_id == state.current_node_id
        assert restored.status == state.status
        assert len(restored.node_history) == 1
        assert restored.retry_counts == {"generation": 1}
        assert restored.terminal_outcome == "stabilized"
        assert restored.gate_outcome == "qualified"
        assert restored.thread_id == "thread-789"

    def test_json_roundtrip(self, state):
        """State serializes to JSON and back."""
        state.record_execution("test", "success")

        json_str = state.to_json()
        restored = DocumentWorkflowState.from_json(json_str)

        assert restored.execution_id == state.execution_id
        assert len(restored.node_history) == 1


class TestDocumentWorkflowStatus:
    """Tests for DocumentWorkflowStatus enum."""

    def test_all_statuses(self):
        """All expected statuses exist."""
        assert DocumentWorkflowStatus.PENDING.value == "pending"
        assert DocumentWorkflowStatus.RUNNING.value == "running"
        assert DocumentWorkflowStatus.PAUSED.value == "paused"
        assert DocumentWorkflowStatus.COMPLETED.value == "completed"
        assert DocumentWorkflowStatus.FAILED.value == "failed"

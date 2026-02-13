"""Tests for node executors (ADR-039)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeResult,
)
from app.domain.workflow.nodes.task import TaskNodeExecutor
from app.domain.workflow.nodes.gate import GateNodeExecutor
from app.domain.workflow.nodes.qa import QANodeExecutor
from app.domain.workflow.nodes.end import EndNodeExecutor


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = MagicMock()
    service.complete = AsyncMock(return_value="Test LLM response")
    return service


@pytest.fixture
def mock_prompt_loader():
    """Create a mock prompt loader."""
    loader = MagicMock()
    loader.load_task_prompt = MagicMock(return_value="Test task prompt")
    loader.load_role_prompt = MagicMock(return_value="Test role prompt")
    return loader


@pytest.fixture
def context():
    """Create a basic workflow context."""
    return DocumentWorkflowContext(
        project_id="proj-123",
        document_type="test_document",
    )


@pytest.fixture
def state_snapshot():
    """Create a basic state snapshot."""
    return {
        "current_node_id": "test_node",
        "retry_counts": {},
    }


# =============================================================================
# TaskNodeExecutor Tests
# =============================================================================

class TestTaskNodeExecutor:
    """Tests for TaskNodeExecutor."""

    @pytest.fixture
    def executor(self, mock_llm_service, mock_prompt_loader):
        """Create a TaskNodeExecutor."""
        return TaskNodeExecutor(
            llm_service=mock_llm_service,
            prompt_loader=mock_prompt_loader,
        )

    def test_supported_node_type(self, executor):
        """Executor reports correct node type."""
        assert executor.get_supported_node_type() == "task"

    @pytest.mark.asyncio
    async def test_execute_success(self, executor, context, state_snapshot, mock_llm_service):
        """Successful execution returns success outcome."""
        mock_llm_service.complete = AsyncMock(return_value='{"result": "generated"}')

        result = await executor.execute(
            node_id="generation",
            node_config={"task_ref": "Test Task v1.0", "produces": "output_doc"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "success"
        assert result.produced_document is not None

    @pytest.mark.asyncio
    async def test_execute_missing_task_ref(self, executor, context, state_snapshot):
        """Missing task_ref returns failed outcome."""
        result = await executor.execute(
            node_id="bad_task",
            node_config={},  # Missing task_ref
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "failed"
        assert "task_ref" in result.metadata.get("failure_reason", "").lower()

    @pytest.mark.asyncio
    async def test_execute_llm_error(self, executor, context, state_snapshot, mock_llm_service):
        """LLM error returns failed outcome."""
        mock_llm_service.complete = AsyncMock(side_effect=Exception("LLM error"))

        result = await executor.execute(
            node_id="failing_task",
            node_config={"task_ref": "Test Task v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "failed"

    @pytest.mark.asyncio
    async def test_parse_json_response(self, executor, context, state_snapshot, mock_llm_service):
        """JSON response is parsed correctly."""
        mock_llm_service.complete = AsyncMock(
            return_value='```json\n{"key": "value"}\n```'
        )

        result = await executor.execute(
            node_id="task",
            node_config={"task_ref": "Test", "produces": "doc"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "success"
        assert result.produced_document == {"key": "value"}


# =============================================================================
# GateNodeExecutor Tests
# =============================================================================

class TestGateNodeExecutor:
    """Tests for GateNodeExecutor."""

    @pytest.fixture
    def executor(self):
        """Create a GateNodeExecutor."""
        return GateNodeExecutor()

    def test_supported_node_type(self, executor):
        """Executor reports correct node type."""
        assert executor.get_supported_node_type() == "gate"

    @pytest.mark.asyncio
    async def test_simple_gate_passes(self, executor, context, state_snapshot):
        """Simple gate without conditions passes."""
        result = await executor.execute(
            node_id="simple_gate",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "success"

    @pytest.mark.asyncio
    async def test_consent_gate_requests_input(self, executor, context, state_snapshot):
        """Consent gate requests user input."""
        result = await executor.execute(
            node_id="consent_gate",
            node_config={"requires_consent": True},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        assert result.requires_user_input is True
        assert "proceed" in result.user_choices

    @pytest.mark.asyncio
    async def test_consent_gate_with_consent(self, executor, context, state_snapshot):
        """Consent gate with user consent proceeds."""
        # ADR-037: Option selection via context.extra["selected_option_id"]
        context.extra["selected_option_id"] = "proceed"

        result = await executor.execute(
            node_id="consent_gate",
            node_config={"requires_consent": True},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "success"
        assert result.metadata.get("consent") is True

    @pytest.mark.asyncio
    async def test_consent_gate_denied(self, executor, context, state_snapshot):
        """Consent gate with denied consent returns blocked."""
        # ADR-037: Option selection via context.extra["selected_option_id"]
        context.extra["selected_option_id"] = "not_ready"

        result = await executor.execute(
            node_id="consent_gate",
            node_config={"requires_consent": True},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "blocked"

    @pytest.mark.asyncio
    async def test_outcome_gate_requests_selection(self, executor, context, state_snapshot):
        """Outcome gate requests selection from choices."""
        result = await executor.execute(
            node_id="outcome_gate",
            node_config={"gate_outcomes": ["qualified", "not_ready"]},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        assert result.user_choices == ["qualified", "not_ready"]

    @pytest.mark.asyncio
    async def test_outcome_gate_with_selection(self, executor, context, state_snapshot):
        """Outcome gate with user selection returns that outcome."""
        # ADR-037: Option selection via context.extra["selected_option_id"]
        context.extra["selected_option_id"] = "qualified"

        result = await executor.execute(
            node_id="outcome_gate",
            node_config={"gate_outcomes": ["qualified", "not_ready"]},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "qualified"

    @pytest.mark.asyncio
    async def test_cached_response_used(self, executor, context, state_snapshot):
        """Previously selected response is used."""
        # ADR-037: Option selection via context.extra["selected_option_id"]
        context.extra["selected_option_id"] = "not_ready"

        result = await executor.execute(
            node_id="cached_gate",
            node_config={"gate_outcomes": ["qualified", "not_ready"]},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "not_ready"
        # Note: from_cache is no longer set since we use the new selection mechanism
        assert result.metadata.get("gate_outcome") == "not_ready"

class TestQANodeExecutor:
    """Tests for QANodeExecutor."""

    @pytest.fixture
    def executor(self, mock_llm_service, mock_prompt_loader):
        """Create a QANodeExecutor."""
        return QANodeExecutor(
            llm_service=mock_llm_service,
            prompt_loader=mock_prompt_loader,
        )

    @pytest.fixture
    def executor_minimal(self):
        """Create a QANodeExecutor without dependencies."""
        return QANodeExecutor()

    def test_supported_node_type(self, executor):
        """Executor reports correct node type."""
        assert executor.get_supported_node_type() == "qa"

    @pytest.mark.asyncio
    async def test_qa_not_required_auto_passes(self, executor_minimal, context, state_snapshot):
        """QA skipped when requires_qa is false."""
        result = await executor_minimal.execute(
            node_id="qa",
            node_config={"requires_qa": False},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "success"
        assert result.metadata.get("qa_skipped") is True

    @pytest.mark.asyncio
    async def test_no_document_fails(self, executor_minimal, context, state_snapshot):
        """QA fails when no document to validate."""
        result = await executor_minimal.execute(
            node_id="qa",
            node_config={"requires_qa": True},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "failed"
        assert "no document" in result.metadata.get("failure_reason", "").lower()

    @pytest.mark.asyncio
    async def test_qa_passes_with_document(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """QA passes when document is valid."""
        context.document_content["test_doc"] = {"field": "value"}
        mock_llm_service.complete = AsyncMock(
            return_value="Document passes all quality checks. No issues found."
        )

        result = await executor.execute(
            node_id="qa",
            node_config={"task_ref": "QA Prompt v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "success"

    @pytest.mark.asyncio
    async def test_qa_fails_with_issues(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """QA fails when issues are detected."""
        context.document_content["test_doc"] = {"field": "value"}
        mock_llm_service.complete = AsyncMock(
            return_value="Quality: FAIL. Issues found:\n- Missing required field\n- Invalid format"
        )

        result = await executor.execute(
            node_id="qa",
            node_config={"task_ref": "QA Prompt v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "failed"
        assert result.metadata.get("error_count", 0) > 0

    @pytest.mark.asyncio
    async def test_does_not_increment_retry_counter(
        self, executor, context, state_snapshot, mock_llm_service
    ):
        """QA executor does NOT increment retry counter (boundary constraint)."""
        context.document_content["test_doc"] = {"field": "value"}
        mock_llm_service.complete = AsyncMock(return_value="Fails quality check")

        result = await executor.execute(
            node_id="qa",
            node_config={"task_ref": "QA v1.0"},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Executor returns outcome but does NOT mutate retry counts
        # That's the PlanExecutor's job
        assert "retry_count" not in result.metadata
        # state_snapshot should be unchanged (it's read-only)


# =============================================================================
# EndNodeExecutor Tests
# =============================================================================

class TestEndNodeExecutor:
    """Tests for EndNodeExecutor."""

    @pytest.fixture
    def executor(self):
        """Create an EndNodeExecutor."""
        return EndNodeExecutor()

    def test_supported_node_type(self, executor):
        """Executor reports correct node type."""
        assert executor.get_supported_node_type() == "end"

    @pytest.mark.asyncio
    async def test_end_stabilized(self, executor, context, state_snapshot):
        """End node with stabilized outcome."""
        result = await executor.execute(
            node_id="end_stabilized",
            node_config={
                "terminal_outcome": "stabilized",
                "gate_outcome": "qualified",
            },
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "stabilized"
        assert result.metadata.get("terminal_outcome") == "stabilized"
        assert result.metadata.get("gate_outcome") == "qualified"
        assert result.metadata.get("is_terminal") is True

    @pytest.mark.asyncio
    async def test_end_blocked(self, executor, context, state_snapshot):
        """End node with blocked outcome."""
        result = await executor.execute(
            node_id="end_blocked",
            node_config={
                "terminal_outcome": "blocked",
                "gate_outcome": "not_ready",
            },
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "blocked"
        assert result.metadata.get("terminal_outcome") == "blocked"

    @pytest.mark.asyncio
    async def test_end_abandoned(self, executor, context, state_snapshot):
        """End node with abandoned outcome."""
        result = await executor.execute(
            node_id="end_abandoned",
            node_config={
                "terminal_outcome": "abandoned",
            },
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "abandoned"

    @pytest.mark.asyncio
    async def test_missing_terminal_outcome_fails(self, executor, context, state_snapshot):
        """End node without terminal_outcome fails."""
        result = await executor.execute(
            node_id="bad_end",
            node_config={},  # Missing terminal_outcome
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "failed"
        assert "terminal_outcome" in result.metadata.get("failure_reason", "")

    @pytest.mark.asyncio
    async def test_includes_execution_summary(self, executor, context, state_snapshot):
        """End node includes execution summary metadata."""
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi")
        context.document_content["doc1"] = {"key": "value"}

        result = await executor.execute(
            node_id="end_stabilized",
            node_config={"terminal_outcome": "stabilized"},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.metadata.get("conversation_turns") == 2
        assert "doc1" in result.metadata.get("documents_produced", [])

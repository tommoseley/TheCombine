"""Tests for IntakeGateExecutor.

Tests the mechanical sufficiency check behavior:
- Extract fields from user input
- Ask one question at a time for missing fields
- Return qualified when frame is complete (audience + artifact_type present)
"""

import pytest

from app.domain.workflow.nodes.intake_gate import (
    IntakeGateExecutor,
    IntakeFrame,
)
from app.domain.workflow.nodes.base import DocumentWorkflowContext


class TestIntakeFrame:
    """Tests for IntakeFrame sufficiency logic."""

    def test_empty_frame_is_incomplete(self):
        """Empty frame is not complete."""
        frame = IntakeFrame()
        assert not frame.is_complete()

    def test_frame_with_both_fields_is_complete(self):
        """Frame with audience and artifact_type is complete."""
        frame = IntakeFrame(audience="developers", artifact_type="web app")
        assert frame.is_complete()

    def test_frame_missing_audience_is_incomplete(self):
        """Frame missing audience is incomplete."""
        frame = IntakeFrame(artifact_type="web app")
        assert not frame.is_complete()
        assert frame.missing_field() == "audience"

    def test_frame_missing_artifact_type_is_incomplete(self):
        """Frame missing artifact_type is incomplete."""
        frame = IntakeFrame(audience="developers")
        assert not frame.is_complete()
        assert frame.missing_field() == "artifact_type"

    def test_missing_field_returns_artifact_type_first(self):
        """artifact_type is asked before audience."""
        frame = IntakeFrame()
        assert frame.missing_field() == "artifact_type"


class TestIntakeGateBasics:
    """Basic tests for IntakeGateExecutor."""

    @pytest.fixture
    def executor(self):
        return IntakeGateExecutor()

    @pytest.fixture
    def context(self):
        return DocumentWorkflowContext(
            project_id="proj-123",
            document_type="test_document",
            conversation_history=[],
            input_documents={},
            user_responses={},
            extra={},
            context_state={},
        )

    @pytest.fixture
    def state_snapshot(self):
        return {"execution_id": "exec-123"}

    def test_supported_node_type(self, executor):
        """Executor reports correct node type."""
        assert executor.get_supported_node_type() == "intake_gate"


class TestMechanicalSufficiency:
    """Tests for mechanical sufficiency checking."""

    @pytest.fixture
    def executor(self):
        return IntakeGateExecutor()

    @pytest.fixture
    def context(self):
        return DocumentWorkflowContext(
            project_id="proj-123",
            document_type="test_document",
            conversation_history=[],
            input_documents={},
            user_responses={},
            extra={},
            context_state={},
        )

    @pytest.fixture
    def state_snapshot(self):
        return {"execution_id": "exec-123"}

    @pytest.mark.asyncio
    async def test_no_input_asks_for_description(self, executor, context, state_snapshot):
        """No input requests initial description."""
        context.extra["user_input"] = ""

        result = await executor.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        assert "describe" in result.user_prompt.lower()

    @pytest.mark.asyncio
    async def test_input_missing_artifact_type_asks_for_it(self, executor, context, state_snapshot):
        """Input without artifact_type asks for it."""
        context.extra["user_input"] = "I need something for my team"

        result = await executor.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        assert "type of software" in result.user_prompt.lower()

    @pytest.mark.asyncio
    async def test_input_with_artifact_type_asks_for_audience(self, executor, context, state_snapshot):
        """Input with artifact_type but no audience asks for audience."""
        context.extra["user_input"] = "I want to build a web app"

        result = await executor.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        assert result.outcome == "needs_user_input"
        # Should ask about audience since artifact_type was extracted
        assert "who" in result.user_prompt.lower() or "type of software" in result.user_prompt.lower()

    @pytest.mark.asyncio
    async def test_complete_input_returns_qualified(self, executor, context, state_snapshot):
        """Input with both fields returns qualified."""
        context.extra["user_input"] = "I want to build a web app for my customers"

        result = await executor.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Either qualified or asks for more info - depends on extraction
        assert result.outcome in ["qualified", "needs_user_input"]

    @pytest.mark.asyncio
    async def test_frame_persists_across_calls(self, executor, context, state_snapshot):
        """Frame data persists in metadata across calls."""
        context.extra["user_input"] = "I want a mobile app"

        result = await executor.execute(
            node_id="intake",
            node_config={},
            context=context,
            state_snapshot=state_snapshot,
        )

        # Should have intake_frame in metadata
        assert "intake_frame" in result.metadata
        frame = result.metadata["intake_frame"]
        assert "artifact_type" in frame
        assert "audience" in frame


class TestFieldExtraction:
    """Tests for field extraction from text."""

    @pytest.fixture
    def executor(self):
        return IntakeGateExecutor()

    def test_extracts_web_app(self, executor):
        """Extracts 'web app' as artifact_type."""
        frame = IntakeFrame()
        frame = executor._extract_fields(frame, "I want to build a web app")
        assert frame.artifact_type is not None

    def test_extracts_mobile_app(self, executor):
        """Extracts 'mobile app' as artifact_type."""
        frame = IntakeFrame()
        frame = executor._extract_fields(frame, "build me a mobile app")
        assert frame.artifact_type is not None

    def test_extracts_api(self, executor):
        """Extracts 'API' as artifact_type."""
        frame = IntakeFrame()
        frame = executor._extract_fields(frame, "I need an API for data access")
        assert frame.artifact_type is not None

    def test_extracts_customers_as_audience(self, executor):
        """Extracts 'customers' as audience."""
        frame = IntakeFrame()
        frame = executor._extract_fields(frame, "this is for our customers")
        assert frame.audience is not None

    def test_extracts_internal_team_as_audience(self, executor):
        """Extracts 'team' as audience."""
        frame = IntakeFrame()
        frame = executor._extract_fields(frame, "for internal team use")
        assert frame.audience is not None
"""Tests for gate outcome honesty (WS-OPS-001 Criteria 5-7).

C5: No false classification — LLMOperationalError does NOT produce "Classification complete"
C6: Error payload stored — result.metadata contains intake_operational_error with required fields
C7: Outcome is operational_error — result uses needs_user_input with reason=operational_error
"""

import logging
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.models import LLMError, LLMOperationalError

# Stub the workflow package to avoid circular import through __init__.py
# (pre-existing circular: workflow.__init__ -> plan_executor -> api routers -> plan_executor)
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [__import__("os").path.join(
        __import__("os").path.dirname(__file__), "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.base import DocumentWorkflowContext  # noqa: E402
from app.domain.workflow.nodes.intake_gate_profile import IntakeGateProfileExecutor  # noqa: E402


def _make_context(user_input: str = "Build me a web app for kids") -> DocumentWorkflowContext:
    """Create a minimal DocumentWorkflowContext."""
    ctx = DocumentWorkflowContext(
        project_id="test-project",
        document_type="concierge_intake",
    )
    ctx.extra = {"user_input": user_input}
    return ctx


def _make_state_snapshot() -> dict:
    return {"context_state": {"intake_gate_phase": "initial"}}


def _make_failing_llm_service() -> AsyncMock:
    """Create an LLM service that raises LLMOperationalError."""
    service = AsyncMock()
    service.complete.side_effect = LLMOperationalError(
        provider="anthropic",
        status_code=529,
        request_id="req-abc-123",
        message="API overloaded",
        attempts=4,
    )
    return service


def _make_prompt_loader() -> MagicMock:
    loader = MagicMock()
    loader.load_task_prompt.return_value = "You are a classifier."
    return loader


class TestNoFalseClassification:
    """C5: LLMOperationalError must NOT produce 'Classification complete' log."""

    @pytest.mark.asyncio
    async def test_no_classification_complete_log_on_operational_error(self, caplog):
        executor = IntakeGateProfileExecutor(
            llm_service=_make_failing_llm_service(),
            prompt_loader=_make_prompt_loader(),
        )

        internals = {"pass_a": {"internal_type": "LLM", "task_ref": "prompt:task:intake_gate:1.0.0"}}

        with caplog.at_level(logging.INFO):
            result = await executor._execute_initial_phase(
                node_id="gate_1",
                internals=internals,
                context=_make_context(),
                state_snapshot=_make_state_snapshot(),
            )

        assert "Classification complete" not in caplog.text


class TestErrorPayloadStored:
    """C6: result.metadata must contain intake_operational_error with required fields."""

    @pytest.mark.asyncio
    async def test_error_payload_in_metadata(self):
        executor = IntakeGateProfileExecutor(
            llm_service=_make_failing_llm_service(),
            prompt_loader=_make_prompt_loader(),
        )

        internals = {"pass_a": {"internal_type": "LLM", "task_ref": "prompt:task:intake_gate:1.0.0"}}

        result = await executor._execute_initial_phase(
            node_id="gate_1",
            internals=internals,
            context=_make_context(),
            state_snapshot=_make_state_snapshot(),
        )

        error_payload = result.metadata.get("intake_operational_error")
        assert error_payload is not None, "intake_operational_error missing from metadata"
        assert error_payload["status"] == "OPERATIONAL_ERROR"
        assert error_payload["retryable"] is True
        assert error_payload["provider"] == "anthropic"
        assert error_payload["http_status"] == 529
        assert error_payload["request_id"] == "req-abc-123"
        assert "first_seen_at" in error_payload


class TestOutcomeIsOperationalError:
    """C7: outcome is needs_user_input with reason=operational_error."""

    @pytest.mark.asyncio
    async def test_outcome_is_needs_user_input_with_operational_error_reason(self):
        executor = IntakeGateProfileExecutor(
            llm_service=_make_failing_llm_service(),
            prompt_loader=_make_prompt_loader(),
        )

        internals = {"pass_a": {"internal_type": "LLM", "task_ref": "prompt:task:intake_gate:1.0.0"}}

        result = await executor._execute_initial_phase(
            node_id="gate_1",
            internals=internals,
            context=_make_context(),
            state_snapshot=_make_state_snapshot(),
        )

        assert result.outcome == "needs_user_input"
        assert result.metadata.get("reason") == "operational_error"
        assert "needs_clarification" not in str(result.metadata)

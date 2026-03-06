"""CRAP score remediation tests for LoggingLLMService.complete.

Target: LoggingLLMService.complete (CC=18, 64.2% cov -> need ~73%)

Tests focus on UNCOVERED branches: logger start failures, UUID parsing,
prompt_sources metadata, log error paths, non-UUID project_id handling, etc.
"""

import os
import sys
import types

import pytest
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the workflow package to avoid circular import through __init__.py
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.llm_executors import LoggingLLMService  # noqa: E402
from app.llm.models import LLMResponse, Message, MessageRole  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

@dataclass
class FakeLLMResponse:
    content: str = "LLM response"
    input_tokens: int = 100
    output_tokens: int = 50
    total_tokens: int = 150
    latency_ms: float = 120.5
    cached: bool = False
    stop_reason: str = "end_turn"
    model: str = "test-model"


class FakeProvider:
    """Fake AnthropicProvider."""

    def __init__(self, response=None, error=None):
        self._response = response or FakeLLMResponse()
        self._error = error
        self.called_with = None

    @property
    def provider_name(self):
        return "fake"

    async def complete_with_retry(self, **kwargs):
        self.called_with = kwargs
        if self._error:
            raise self._error
        return self._response


class FakeLogger:
    """Fake LLMExecutionLogger."""

    def __init__(self, start_run_error=False, complete_run_error=False, add_output_error=False):
        self.started = []
        self.inputs = []
        self.outputs = []
        self.completed = []
        self.errors = []
        self._start_run_error = start_run_error
        self._complete_run_error = complete_run_error
        self._add_output_error = add_output_error

    async def start_run(self, **kwargs):
        if self._start_run_error:
            raise RuntimeError("Logger DB down")
        run_id = uuid4()
        self.started.append({"run_id": run_id, **kwargs})
        return run_id

    async def add_input(self, run_id, name, content):
        self.inputs.append({"run_id": run_id, "name": name, "content": content})

    async def add_output(self, run_id, name, content):
        if self._add_output_error:
            raise RuntimeError("Output log failed")
        self.outputs.append({"run_id": run_id, "name": name, "content": content})

    async def complete_run(self, **kwargs):
        if self._complete_run_error:
            raise RuntimeError("Complete log failed")
        self.completed.append(kwargs)

    async def log_error(self, **kwargs):
        self.errors.append(kwargs)


# ====================================================================
# Tests
# ====================================================================


class TestLoggingLLMServiceComplete:
    """Tests for LoggingLLMService.complete uncovered branches."""

    @pytest.mark.asyncio
    async def test_basic_completion_no_logger(self):
        """Branch: no execution_logger -> skip all logging."""
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=None)

        result = await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result == "LLM response"
        assert provider.called_with is not None

    @pytest.mark.asyncio
    async def test_completion_with_logger(self):
        """Branch: logger present -> logs start, inputs, output, complete."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        result = await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            task_ref="test_task",
            artifact_type="test_doc",
            project_id=str(uuid4()),
        )

        assert result == "LLM response"
        assert len(logger.started) == 1
        assert len(logger.inputs) == 1  # 1 message
        assert len(logger.outputs) == 1
        assert len(logger.completed) == 1
        assert logger.completed[0]["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_system_prompt_logged(self):
        """Branch: system_prompt provided -> logged as input."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant",
        )

        # Should have 2 inputs: system_prompt + 1 message
        assert len(logger.inputs) == 2
        assert logger.inputs[0]["name"] == "system_prompt"

    @pytest.mark.asyncio
    async def test_multiple_messages_logged(self):
        """Branch: multiple messages -> each logged as input."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[
                {"role": "user", "content": "First"},
                {"role": "user", "content": "Second"},
            ],
        )

        assert len(logger.inputs) == 2
        assert logger.inputs[0]["name"] == "message_0_user"
        assert logger.inputs[1]["name"] == "message_1_user"

    @pytest.mark.asyncio
    async def test_non_uuid_project_id_skipped(self):
        """Branch: project_id is not a valid UUID -> safe_project_id = None."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            project_id="intake-f9237d92569a",  # Not a UUID
        )

        # Should still work, safe_project_id should be None
        assert len(logger.started) == 1
        assert logger.started[0]["project_id"] is None

    @pytest.mark.asyncio
    async def test_valid_uuid_project_id(self):
        """Branch: project_id is a valid UUID -> parsed and passed."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        pid = uuid4()
        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            project_id=str(pid),
        )

        assert logger.started[0]["project_id"] == pid

    @pytest.mark.asyncio
    async def test_uuid_object_project_id(self):
        """Branch: project_id is already a UUID object."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        pid = uuid4()
        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            project_id=pid,
        )

        assert logger.started[0]["project_id"] == pid

    @pytest.mark.asyncio
    async def test_none_project_id(self):
        """Branch: project_id is None -> safe_project_id = None."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            project_id=None,
        )

        assert logger.started[0]["project_id"] is None

    @pytest.mark.asyncio
    async def test_start_run_failure_continues(self):
        """Branch: logger.start_run raises -> run_id = None, LLM still called."""
        logger = FakeLogger(start_run_error=True)
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        result = await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result == "LLM response"
        # No logging happened since start_run failed
        assert len(logger.outputs) == 0
        assert len(logger.completed) == 0

    @pytest.mark.asyncio
    async def test_complete_run_failure_swallowed(self):
        """Branch: logger.complete_run raises -> warning logged, not propagated."""
        logger = FakeLogger(complete_run_error=True)
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        result = await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        # LLM response still returned despite logging failure
        assert result == "LLM response"

    @pytest.mark.asyncio
    async def test_add_output_failure_swallowed(self):
        """Branch: logger.add_output raises -> warning logged, not propagated."""
        logger = FakeLogger(add_output_error=True)
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        result = await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result == "LLM response"

    @pytest.mark.asyncio
    async def test_llm_error_logged_and_reraised(self):
        """Branch: provider raises -> error logged, then re-raised."""
        logger = FakeLogger()
        error = RuntimeError("LLM provider down")
        provider = FakeProvider(error=error)
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        with pytest.raises(RuntimeError, match="LLM provider down"):
            await service.complete(
                messages=[{"role": "user", "content": "Hello"}],
                node_id="task-1",
            )

        # Error should have been logged
        assert len(logger.errors) == 1
        assert logger.errors[0]["severity"] == "ERROR"
        assert logger.errors[0]["error_code"] == "LLM_ERROR"

        # Run should have been completed as FAILED
        assert len(logger.completed) == 1
        assert logger.completed[0]["status"] == "FAILED"
        assert logger.completed[0]["metadata"]["node_id"] == "task-1"

    @pytest.mark.asyncio
    async def test_llm_error_with_logger_failure(self):
        """Branch: provider raises AND logger.log_error raises -> still propagates original."""
        logger = FakeLogger()
        # Make log_error fail too
        logger.log_error = AsyncMock(side_effect=RuntimeError("DB down"))
        logger.complete_run = AsyncMock(side_effect=RuntimeError("DB down"))

        error = RuntimeError("LLM provider down")
        provider = FakeProvider(error=error)
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        with pytest.raises(RuntimeError, match="LLM provider down"):
            await service.complete(
                messages=[{"role": "user", "content": "Hello"}],
            )

    @pytest.mark.asyncio
    async def test_llm_error_without_logger(self):
        """Branch: provider raises and no logger -> re-raised directly."""
        error = RuntimeError("No API key")
        provider = FakeProvider(error=error)
        service = LoggingLLMService(provider=provider, execution_logger=None)

        with pytest.raises(RuntimeError, match="No API key"):
            await service.complete(
                messages=[{"role": "user", "content": "Hello"}],
            )

    @pytest.mark.asyncio
    async def test_prompt_sources_in_metadata(self):
        """Branch: prompt_sources kwarg -> included in run metadata."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            prompt_sources=["prompts/tasks/gen_v1.md", "prompts/roles/ba_v1.md"],
        )

        # Check metadata in complete_run
        assert len(logger.completed) == 1
        metadata = logger.completed[0]["metadata"]
        assert "prompt_sources" in metadata
        assert len(metadata["prompt_sources"]) == 2

    @pytest.mark.asyncio
    async def test_no_prompt_sources(self):
        """Branch: no prompt_sources -> not in metadata."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        metadata = logger.completed[0]["metadata"]
        assert "prompt_sources" not in metadata

    @pytest.mark.asyncio
    async def test_node_id_in_metadata(self):
        """Branch: node_id kwarg -> included in run metadata."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            node_id="pgc-1",
        )

        metadata = logger.completed[0]["metadata"]
        assert metadata["node_id"] == "pgc-1"

    @pytest.mark.asyncio
    async def test_workflow_execution_id_passed(self):
        """Branch: workflow_execution_id kwarg -> passed to logger."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            workflow_execution_id="exec-abc",
        )

        assert logger.started[0]["workflow_execution_id"] == "exec-abc"

    @pytest.mark.asyncio
    async def test_custom_model_and_temperature(self):
        """Branch: model/max_tokens/temperature kwargs -> passed to provider."""
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=None)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            model="opus",
            max_tokens=8192,
            temperature=0.2,
        )

        assert provider.called_with["model"] == "opus"
        assert provider.called_with["max_tokens"] == 8192
        assert provider.called_with["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_default_model_and_temperature(self):
        """Branch: no model kwargs -> uses defaults."""
        provider = FakeProvider()
        service = LoggingLLMService(
            provider=provider,
            execution_logger=None,
            default_model="haiku",
            default_max_tokens=2048,
            default_temperature=0.5,
        )

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert provider.called_with["model"] == "haiku"
        assert provider.called_with["max_tokens"] == 2048
        assert provider.called_with["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_correlation_id_auto_generated(self):
        """Branch: no correlation_id kwarg -> auto-generated UUID."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        correlation_id = logger.started[0]["correlation_id"]
        assert isinstance(correlation_id, UUID)

    @pytest.mark.asyncio
    async def test_role_kwarg_in_logger(self):
        """Branch: role kwarg -> passed through to logger start_run."""
        logger = FakeLogger()
        provider = FakeProvider()
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
            role="Business Analyst",
        )

        assert logger.started[0]["role"] == "Business Analyst"

    @pytest.mark.asyncio
    async def test_cached_response_logged(self):
        """Branch: response.cached = True -> reflected in metadata."""
        logger = FakeLogger()
        provider = FakeProvider(response=FakeLLMResponse(cached=True))
        service = LoggingLLMService(provider=provider, execution_logger=logger)

        await service.complete(
            messages=[{"role": "user", "content": "Hello"}],
        )

        metadata = logger.completed[0]["metadata"]
        assert metadata["cached"] is True

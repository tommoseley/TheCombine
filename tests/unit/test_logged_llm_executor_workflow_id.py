"""
Tests for LoggingLLMService workflow_execution_id handling.

Verifies that LoggingLLMService extracts workflow_execution_id from kwargs
and passes it to the LLM execution logger.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from app.domain.workflow.nodes.llm_executors import LoggingLLMService


@dataclass
class MockLLMResponse:
    content: str = '{"result": "test"}'
    input_tokens: int = 100
    output_tokens: int = 50
    total_tokens: int = 150
    latency_ms: int = 500


class MockLLMProvider:
    """Mock LLM provider."""
    @property
    def provider_name(self):
        return "mock"

    async def complete(self, **kwargs):
        return MockLLMResponse()

    async def complete_with_retry(self, **kwargs):
        return await self.complete(**kwargs)


class MockLogger:
    """Mock execution logger that captures calls."""
    def __init__(self):
        self.start_run_calls = []
        self.add_input_calls = []
        self.add_output_calls = []
        self.complete_run_calls = []
    
    async def start_run(self, **kwargs):
        self.start_run_calls.append(kwargs)
        return uuid4()
    
    async def add_input(self, run_id, kind, content):
        self.add_input_calls.append((run_id, kind, content))
    
    async def add_output(self, run_id, kind, content):
        self.add_output_calls.append((run_id, kind, content))
    
    async def complete_run(self, **kwargs):
        self.complete_run_calls.append(kwargs)


@pytest.fixture
def mock_provider():
    return MockLLMProvider()


@pytest.fixture
def mock_logger():
    return MockLogger()


@pytest.fixture
def executor(mock_provider, mock_logger):
    return LoggingLLMService(
        provider=mock_provider,
        execution_logger=mock_logger,
    )


@pytest.mark.asyncio
async def test_logged_executor_passes_workflow_execution_id_to_logger(executor, mock_logger):
    """Verify LoggingLLMService passes workflow_execution_id to start_run."""
    workflow_execution_id = "exec-logged-test-456"
    
    await executor.complete(
        messages=[{"role": "user", "content": "Hello"}],
        correlation_id=uuid4(),
        workflow_execution_id=workflow_execution_id,
    )
    
    assert len(mock_logger.start_run_calls) == 1
    assert mock_logger.start_run_calls[0].get("workflow_execution_id") == workflow_execution_id


@pytest.mark.asyncio
async def test_logged_executor_handles_no_workflow_execution_id(executor, mock_logger):
    """Verify LoggingLLMService handles missing workflow_execution_id."""
    await executor.complete(
        messages=[{"role": "user", "content": "Hello"}],
        correlation_id=uuid4(),
        # No workflow_execution_id
    )
    
    assert len(mock_logger.start_run_calls) == 1
    assert mock_logger.start_run_calls[0].get("workflow_execution_id") is None


@pytest.mark.asyncio
async def test_logged_executor_without_logger(mock_provider):
    """Verify LoggingLLMService works without a logger."""
    executor = LoggingLLMService(
        provider=mock_provider,
        execution_logger=None,  # No logger
    )
    
    response = await executor.complete(
        messages=[{"role": "user", "content": "Hello"}],
        workflow_execution_id="exec-no-logger",
    )
    
    # Should complete without error
    assert response is not None
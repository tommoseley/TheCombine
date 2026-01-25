"""
Tests for workflow_execution_id passing through node executors.

Verifies that task and QA nodes extract execution_id from context
and pass it to the LLM service.
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from app.domain.workflow.nodes.base import DocumentWorkflowContext
from app.domain.workflow.nodes.task import TaskNodeExecutor


@dataclass
class MockLLMService:
    """Mock LLM service that captures kwargs."""
    captured_kwargs: Dict[str, Any] = field(default_factory=dict)
    response: str = '{"result": "test"}'
    
    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        self.captured_kwargs = kwargs
        return self.response


class MockPromptLoader:
    """Mock prompt loader."""
    def load_task_prompt(self, task_ref: str) -> str:
        return f"Task prompt for {task_ref}"


@pytest.fixture
def mock_llm_service():
    return MockLLMService()


@pytest.fixture
def mock_prompt_loader():
    return MockPromptLoader()


@pytest.fixture
def task_executor(mock_llm_service, mock_prompt_loader):
    return TaskNodeExecutor(
        llm_service=mock_llm_service,
        prompt_loader=mock_prompt_loader,
    )


def make_context(execution_id: Optional[str] = None) -> DocumentWorkflowContext:
    """Create a test context with optional execution_id."""
    extra = {}
    if execution_id:
        extra["execution_id"] = execution_id
    
    return DocumentWorkflowContext(
        project_id="proj-123",
        document_type="test_document",
        extra=extra,
    )


@pytest.mark.asyncio
async def test_task_node_passes_execution_id_to_llm_service(task_executor, mock_llm_service):
    """Verify TaskNodeExecutor passes workflow_execution_id from context to LLM service."""
    execution_id = "exec-task-test-123"
    context = make_context(execution_id=execution_id)
    
    node_config = {
        "task_ref": "test/task",
        "produces": "test_output",
    }
    state_snapshot = {}
    
    await task_executor.execute(
        node_id="task_1",
        node_config=node_config,
        context=context,
        state_snapshot=state_snapshot,
    )
    
    assert mock_llm_service.captured_kwargs.get("workflow_execution_id") == execution_id


@pytest.mark.asyncio
async def test_task_node_handles_missing_execution_id(task_executor, mock_llm_service):
    """Verify TaskNodeExecutor handles context without execution_id."""
    context = make_context(execution_id=None)
    
    node_config = {
        "task_ref": "test/task",
        "produces": "test_output",
    }
    state_snapshot = {}
    
    await task_executor.execute(
        node_id="task_1",
        node_config=node_config,
        context=context,
        state_snapshot=state_snapshot,
    )
    
    # Should pass None, not raise an exception
    assert mock_llm_service.captured_kwargs.get("workflow_execution_id") is None


@pytest.mark.asyncio
async def test_task_node_with_empty_extra(task_executor, mock_llm_service):
    """Verify TaskNodeExecutor handles context with empty extra dict."""
    context = DocumentWorkflowContext(
        project_id="proj-123",
        document_type="test_document",
        extra={},  # Empty but present
    )
    
    node_config = {
        "task_ref": "test/task",
        "produces": "test_output",
    }
    state_snapshot = {}
    
    await task_executor.execute(
        node_id="task_1",
        node_config=node_config,
        context=context,
        state_snapshot=state_snapshot,
    )
    
    assert mock_llm_service.captured_kwargs.get("workflow_execution_id") is None
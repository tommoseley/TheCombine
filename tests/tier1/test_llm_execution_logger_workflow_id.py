"""
Tier-1 tests for workflow_execution_id tracking in LLM logging.

Verifies that execution IDs flow correctly from PlanExecutor → nodes → logger → repository.
"""

import pytest
from uuid import uuid4

from app.domain.services.llm_execution_logger import LLMExecutionLogger
from app.domain.repositories.in_memory_llm_log_repository import InMemoryLLMLogRepository


@pytest.fixture
def repo():
    return InMemoryLLMLogRepository()


@pytest.fixture
def logger(repo):
    return LLMExecutionLogger(repo)


@pytest.mark.asyncio
async def test_start_run_persists_workflow_execution_id(logger, repo):
    """Verify workflow_execution_id is persisted in LLM run record."""
    correlation_id = uuid4()
    workflow_execution_id = "exec-abc123def456"
    
    run_id = await logger.start_run(
        correlation_id=correlation_id,
        project_id=uuid4(),
        artifact_type="project_discovery",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="architect/discovery",
        prompt_version="1.0.0",
        effective_prompt="You are an architect.",
        workflow_execution_id=workflow_execution_id,
    )
    
    run = await repo.get_run(run_id)
    
    assert run is not None
    assert run.workflow_execution_id == workflow_execution_id


@pytest.mark.asyncio
async def test_start_run_without_workflow_execution_id(logger, repo):
    """Verify workflow_execution_id defaults to None when not provided."""
    correlation_id = uuid4()
    
    run_id = await logger.start_run(
        correlation_id=correlation_id,
        project_id=uuid4(),
        artifact_type="project_discovery",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="architect/discovery",
        prompt_version="1.0.0",
        effective_prompt="You are an architect.",
        # No workflow_execution_id
    )
    
    run = await repo.get_run(run_id)
    
    assert run is not None
    assert run.workflow_execution_id is None


@pytest.mark.asyncio
async def test_multiple_runs_same_execution_id(logger, repo):
    """Verify multiple LLM runs can share the same workflow_execution_id."""
    workflow_execution_id = "exec-shared123"
    
    run_ids = []
    for i in range(3):
        run_id = await logger.start_run(
            correlation_id=uuid4(),
            project_id=uuid4(),
            artifact_type=f"artifact_{i}",
            role="architect",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            prompt_id=f"task_{i}",
            prompt_version="1.0.0",
            effective_prompt=f"Prompt {i}",
            workflow_execution_id=workflow_execution_id,
        )
        run_ids.append(run_id)
    
    for run_id in run_ids:
        run = await repo.get_run(run_id)
        assert run.workflow_execution_id == workflow_execution_id
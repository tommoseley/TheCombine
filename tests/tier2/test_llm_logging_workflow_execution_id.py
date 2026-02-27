"""
Tier-2 tests for workflow_execution_id wiring.

Verifies the full chain: context → node executor → LLM service → logger → repository.
"""

import pytest
from uuid import uuid4

from app.domain.services.llm_execution_logger import LLMExecutionLogger
from tests.helpers.spy_llm_log_repository import SpyLLMLogRepository


@pytest.fixture
def spy_repo():
    return SpyLLMLogRepository()


@pytest.fixture
def logger(spy_repo):
    return LLMExecutionLogger(spy_repo)


@pytest.mark.asyncio
async def test_logger_passes_workflow_execution_id_to_repository(logger, spy_repo):
    """Verify logger passes workflow_execution_id to repository insert_run."""
    workflow_execution_id = "exec-test12345"
    
    await logger.start_run(
        correlation_id=uuid4(),
        project_id=uuid4(),
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test prompt",
        workflow_execution_id=workflow_execution_id,
    )
    
    spy_repo.assert_insert_run_has_workflow_execution_id(workflow_execution_id)


@pytest.mark.asyncio
async def test_logger_passes_none_when_no_workflow_execution_id(logger, spy_repo):
    """Verify logger passes None for workflow_execution_id when not provided."""
    await logger.start_run(
        correlation_id=uuid4(),
        project_id=uuid4(),
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test prompt",
    )
    
    record = spy_repo.get_insert_run_record()
    assert record.workflow_execution_id is None


@pytest.mark.asyncio
async def test_insert_run_record_structure(logger, spy_repo):
    """Verify insert_run record has all expected fields including workflow_execution_id."""
    correlation_id = uuid4()
    project_id = uuid4()
    workflow_execution_id = "exec-structure-test"
    
    await logger.start_run(
        correlation_id=correlation_id,
        project_id=project_id,
        artifact_type="project_discovery",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="discovery/task",
        prompt_version="2.0.0",
        effective_prompt="You are an architect.",
        schema_id="project_discovery.v1",
        schema_bundle_hash="abc123",
        workflow_execution_id=workflow_execution_id,
    )
    
    record = spy_repo.get_insert_run_record()
    
    # Verify all key fields
    assert record.correlation_id == correlation_id
    assert record.project_id == project_id
    assert record.artifact_type == "project_discovery"
    assert record.role == "architect"
    assert record.model_provider == "anthropic"
    assert record.model_name == "claude-sonnet-4-20250514"
    assert record.prompt_id == "discovery/task"
    assert record.prompt_version == "2.0.0"
    assert record.schema_id == "project_discovery.v1"
    assert record.schema_bundle_hash == "abc123"
    assert record.workflow_execution_id == workflow_execution_id
    assert record.status == "IN_PROGRESS"
    assert record.started_at is not None
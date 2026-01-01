"""
Tier-1 tests: Business logic + persistence semantics.

Uses InMemoryLLMLogRepository - no SQLAlchemy, no DB.
Verifies ACTUAL persisted, queryable data.
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
async def test_start_run_persists_record(logger, repo):
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
    )
    
    run = await repo.get_run(run_id)
    
    assert run is not None
    assert run.correlation_id == correlation_id
    assert run.status == "IN_PROGRESS"
    assert run.role == "architect"


@pytest.mark.asyncio
async def test_start_run_rejects_none_correlation_id(logger):
    with pytest.raises(ValueError, match="correlation_id cannot be None"):
        await logger.start_run(
            correlation_id=None,
            project_id=None,
            artifact_type="test",
            role="architect",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            prompt_id="test",
            prompt_version="1.0.0",
            effective_prompt="test",
        )


@pytest.mark.asyncio
async def test_add_input_persists_with_content(logger, repo):
    run_id = await logger.start_run(
        correlation_id=uuid4(),
        project_id=None,
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test",
    )
    
    await logger.add_input(run_id, "system_prompt", "You are a helpful assistant.")
    
    inputs = await repo.get_inputs_for_run(run_id)
    
    assert len(inputs) == 1
    assert inputs[0].kind == "system_prompt"
    
    content = repo.get_content_text(inputs[0].content_hash)
    assert content == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_content_deduplication(logger, repo):
    run_id = await logger.start_run(
        correlation_id=uuid4(),
        project_id=None,
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test",
    )
    
    same_content = "This is the same content."
    
    await logger.add_input(run_id, "system_prompt", same_content)
    await logger.add_input(run_id, "user_prompt", same_content)
    
    inputs = await repo.get_inputs_for_run(run_id)
    assert len(inputs) == 2
    assert repo.count_unique_content() == 1
    assert inputs[0].content_hash == inputs[1].content_hash


@pytest.mark.asyncio
async def test_log_error_updates_run_summary(logger, repo):
    run_id = await logger.start_run(
        correlation_id=uuid4(),
        project_id=None,
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test",
    )
    
    await logger.log_error(
        run_id,
        stage="PARSE",
        severity="ERROR",
        error_code="PARSE_FAILED",
        message="Invalid JSON response",
    )
    
    errors = await repo.get_errors_for_run(run_id)
    assert len(errors) == 1
    
    run = await repo.get_run(run_id)
    assert run.error_count == 1
    assert run.primary_error_code == "PARSE_FAILED"


@pytest.mark.asyncio
async def test_complete_run_sets_final_status(logger, repo):
    run_id = await logger.start_run(
        correlation_id=uuid4(),
        project_id=None,
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test",
    )
    
    await logger.complete_run(
        run_id,
        status="SUCCESS",
        usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
    )
    
    run = await repo.get_run(run_id)
    assert run.status == "SUCCESS"
    assert run.ended_at is not None
    assert run.input_tokens == 100
    assert run.output_tokens == 50
    assert run.total_tokens == 150


@pytest.mark.asyncio
async def test_get_run_by_correlation_id(logger, repo):
    correlation_id = uuid4()
    
    await logger.start_run(
        correlation_id=correlation_id,
        project_id=None,
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt="test",
    )
    
    run = await repo.get_run_by_correlation_id(correlation_id)
    assert run is not None
    assert run.correlation_id == correlation_id


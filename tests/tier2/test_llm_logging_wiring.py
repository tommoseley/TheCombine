"""
Tier-2 tests: Wiring (HTTP -> Logger -> Repo).

Uses SpyLLMLogRepository to verify call contracts.
Verifies methods called with correct payload shapes.
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
async def test_start_run_calls_insert_run_and_commit(logger, spy_repo):
    """Verify start_run calls insert_run then commit."""
    correlation_id = uuid4()
    
    await logger.start_run(
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
    
    spy_repo.assert_called("insert_run")
    spy_repo.assert_committed()
    
    call = spy_repo.assert_called("insert_run")
    record = call.kwargs["record"]
    assert record.correlation_id == correlation_id
    assert record.role == "architect"
    assert record.status == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_add_input_calls_content_check_insert_commit(logger, spy_repo):
    """Verify add_input checks content, inserts, and commits."""
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
    
    spy_repo.calls.clear()
    
    await logger.add_input(run_id, "system_prompt", "You are helpful.")
    
    spy_repo.assert_called("get_content_by_hash")
    spy_repo.assert_called("insert_content")
    spy_repo.assert_called("insert_input_ref")
    spy_repo.assert_committed()


@pytest.mark.asyncio
async def test_add_input_records_correct_kind(logger, spy_repo):
    """Verify input ref has correct kind."""
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
    
    await logger.add_input(run_id, "schema", '{"type": "object"}')
    
    spy_repo.assert_input_logged("schema")


@pytest.mark.asyncio
async def test_add_output_calls_correct_methods(logger, spy_repo):
    """Verify add_output calls insert_output_ref."""
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
    
    await logger.add_output(run_id, "raw_text", '{"title": "Test"}')
    
    spy_repo.assert_output_logged("raw_text")
    spy_repo.assert_committed()


@pytest.mark.asyncio
async def test_log_error_calls_insert_and_bump(logger, spy_repo):
    """Verify ERROR severity calls bump_error_summary."""
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
    
    spy_repo.calls.clear()
    
    await logger.log_error(
        run_id,
        stage="PARSE",
        severity="ERROR",
        error_code="PARSE_FAILED",
        message="Bad JSON",
    )
    
    spy_repo.assert_called("insert_error")
    spy_repo.assert_called("bump_error_summary")
    spy_repo.assert_committed()
    
    call = spy_repo.assert_called("bump_error_summary")
    assert call.kwargs["error_code"] == "PARSE_FAILED"
    assert call.kwargs["message"] == "Bad JSON"


@pytest.mark.asyncio
async def test_log_warning_does_not_bump(logger, spy_repo):
    """Verify WARN severity does not call bump_error_summary."""
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
    
    spy_repo.calls.clear()
    
    await logger.log_error(
        run_id,
        stage="MODEL_CALL",
        severity="WARN",
        error_code="RATE_LIMITED",
        message="Retrying",
    )
    
    spy_repo.assert_called("insert_error")
    
    bump_calls = spy_repo.get_calls("bump_error_summary")
    assert len(bump_calls) == 0


@pytest.mark.asyncio
async def test_complete_run_calls_update_and_commit(logger, spy_repo):
    """Verify complete_run calls update_run_completion."""
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
    
    spy_repo.calls.clear()
    
    await logger.complete_run(
        run_id,
        status="SUCCESS",
        usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
    )
    
    spy_repo.assert_called("update_run_completion")
    spy_repo.assert_run_completed_with_status("SUCCESS")
    spy_repo.assert_committed()


@pytest.mark.asyncio
async def test_complete_run_passes_token_counts(logger, spy_repo):
    """Verify token counts are passed to update_run_completion."""
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
        usage={"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
    )
    
    call = spy_repo.assert_called("update_run_completion")
    assert call.kwargs["input_tokens"] == 200
    assert call.kwargs["output_tokens"] == 100
    assert call.kwargs["total_tokens"] == 300


@pytest.mark.asyncio
async def test_correlation_id_propagates_to_run_record(logger, spy_repo):
    """Verify correlation_id is in the run record."""
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
    
    spy_repo.assert_insert_run_has_correlation_id(correlation_id)


@pytest.mark.asyncio
async def test_effective_prompt_hash_computed(logger, spy_repo):
    """Verify effective_prompt_hash is in run record."""
    import hashlib
    prompt = "You are a helpful assistant."
    expected_hash = hashlib.sha256(prompt.encode()).hexdigest()
    
    await logger.start_run(
        correlation_id=uuid4(),
        project_id=None,
        artifact_type="test",
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0.0",
        effective_prompt=prompt,
    )
    
    call = spy_repo.assert_called("insert_run")
    record = call.kwargs["record"]
    assert record.effective_prompt_hash == expected_hash

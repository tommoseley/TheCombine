"""
Tests for LLMRunRecord dataclass structure.

Verifies the LLMRunRecord includes workflow_execution_id field.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.domain.repositories.llm_log_repository import LLMRunRecord


def test_llm_run_record_has_workflow_execution_id_field():
    """Verify LLMRunRecord has workflow_execution_id field."""
    record = LLMRunRecord(
        id=uuid4(),
        correlation_id=uuid4(),
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0",
        effective_prompt_hash="abc123",
        status="IN_PROGRESS",
        started_at=datetime.now(timezone.utc),
        workflow_execution_id="exec-test-123",
    )
    
    assert record.workflow_execution_id == "exec-test-123"


def test_llm_run_record_workflow_execution_id_defaults_to_none():
    """Verify workflow_execution_id defaults to None."""
    record = LLMRunRecord(
        id=uuid4(),
        correlation_id=uuid4(),
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0",
        effective_prompt_hash="abc123",
        status="IN_PROGRESS",
        started_at=datetime.now(timezone.utc),
        # No workflow_execution_id
    )
    
    assert record.workflow_execution_id is None


def test_llm_run_record_is_dataclass():
    """Verify LLMRunRecord behaves as expected dataclass."""
    record = LLMRunRecord(
        id=uuid4(),
        correlation_id=uuid4(),
        role="architect",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        prompt_id="test",
        prompt_version="1.0",
        effective_prompt_hash="abc123",
        status="IN_PROGRESS",
        started_at=datetime.now(timezone.utc),
        workflow_execution_id="exec-123",
    )
    
    # Should be able to access all fields
    assert hasattr(record, "id")
    assert hasattr(record, "correlation_id")
    assert hasattr(record, "workflow_execution_id")
    assert hasattr(record, "status")
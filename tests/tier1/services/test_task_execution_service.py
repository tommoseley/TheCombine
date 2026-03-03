"""Tier-1 tests for task_execution_service.

Tests the reusable task execution primitive (WS-WB-022).
All dependencies (LLM client, prompt loader, schema resolver) are mocked/stubbed.
No database, no filesystem, no network.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.task_execution_service import (
    execute_task,
    TaskExecutionError,
    TaskPromptNotFoundError,
    TaskOutputParseError,
    TaskOutputValidationError,
)


# ---------------------------------------------------------------------------
# Stub factories
# ---------------------------------------------------------------------------


def make_prompt_loader(*, prompt_text: str = "You are a task prompt."):
    """Return a stub prompt loader that returns prompt_text on load_task."""
    loader = MagicMock()
    loader.load_task.return_value = prompt_text
    return loader


def make_prompt_loader_missing():
    """Return a stub prompt loader that raises on load_task.

    Uses a plain Exception rather than importing PromptNotFoundError
    from app.domain.workflow.prompt_loader to avoid the pre-existing
    circular import chain in app.domain.workflow.__init__.
    The service catches any exception from load_task and wraps it as
    TaskPromptNotFoundError.
    """
    loader = MagicMock()
    loader.load_task.side_effect = Exception("prompt not found")
    return loader


def make_llm_client(*, response_text: str = '{"result": "ok"}'):
    """Return a stub async LLM client whose complete() returns response_text."""
    client = AsyncMock()
    client.complete.return_value = response_text
    return client


def make_schema_resolver(*, schema: dict | None = None):
    """Return a stub schema resolver that returns a schema dict.

    If schema is None, uses a permissive schema that accepts any object.
    """
    if schema is None:
        schema = {"type": "object"}
    resolver = MagicMock()
    resolver.resolve.return_value = schema
    return resolver


def make_schema_resolver_missing():
    """Return a stub schema resolver that raises on resolve()."""
    from app.config.package_loader import PackageNotFoundError

    resolver = MagicMock()
    resolver.resolve.side_effect = PackageNotFoundError("schema not found")
    return resolver


# ---------------------------------------------------------------------------
# Test: missing prompt -> TaskPromptNotFoundError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_prompt_raises_task_prompt_not_found():
    """When the prompt loader cannot find the task prompt, execute_task must
    raise TaskPromptNotFoundError."""
    result = None
    with pytest.raises(TaskPromptNotFoundError):
        result = await execute_task(
            task_id="nonexistent_task",
            version="1.0.0",
            inputs={"user_input": "hello"},
            expected_schema_id="some_schema",
            llm_client=make_llm_client(),
            prompt_loader=make_prompt_loader_missing(),
            schema_resolver=make_schema_resolver(),
        )
    assert result is None


# ---------------------------------------------------------------------------
# Test: invalid JSON from LLM -> TaskOutputParseError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_json_from_llm_raises_task_output_parse_error():
    """When the LLM returns non-JSON text, execute_task must raise
    TaskOutputParseError."""
    with pytest.raises(TaskOutputParseError):
        await execute_task(
            task_id="some_task",
            version="1.0.0",
            inputs={"user_input": "hello"},
            expected_schema_id="some_schema",
            llm_client=make_llm_client(response_text="This is not JSON at all."),
            prompt_loader=make_prompt_loader(),
            schema_resolver=make_schema_resolver(),
        )


# ---------------------------------------------------------------------------
# Test: schema violation -> TaskOutputValidationError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schema_violation_raises_task_output_validation_error():
    """When the LLM returns valid JSON that fails schema validation,
    execute_task must raise TaskOutputValidationError."""
    strict_schema = {
        "type": "object",
        "required": ["title", "summary"],
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
        },
    }
    # LLM returns valid JSON but missing required fields
    with pytest.raises(TaskOutputValidationError):
        await execute_task(
            task_id="some_task",
            version="1.0.0",
            inputs={"user_input": "hello"},
            expected_schema_id="strict_schema",
            llm_client=make_llm_client(response_text='{"wrong_field": "value"}'),
            prompt_loader=make_prompt_loader(),
            schema_resolver=make_schema_resolver(schema=strict_schema),
        )


# ---------------------------------------------------------------------------
# Test: happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_validated_output():
    """When everything succeeds, execute_task returns a dict with
    correlation_id, output, task_id, and version."""
    schema = {
        "type": "object",
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
        },
    }
    llm_output = json.dumps({"title": "My Document"})

    result = await execute_task(
        task_id="doc_task",
        version="2.0.0",
        inputs={"user_input": "make a doc"},
        expected_schema_id="doc_schema",
        llm_client=make_llm_client(response_text=llm_output),
        prompt_loader=make_prompt_loader(),
        schema_resolver=make_schema_resolver(schema=schema),
    )

    assert result["task_id"] == "doc_task"
    assert result["version"] == "2.0.0"
    assert result["output"] == {"title": "My Document"}
    assert "correlation_id" in result


# ---------------------------------------------------------------------------
# Test: correlation_id is a valid UUID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_correlation_id_is_valid_uuid():
    """The correlation_id in the return dict must be a valid UUID string."""
    llm_output = json.dumps({"status": "done"})

    result = await execute_task(
        task_id="task_a",
        version="1.0.0",
        inputs={},
        expected_schema_id="basic_schema",
        llm_client=make_llm_client(response_text=llm_output),
        prompt_loader=make_prompt_loader(),
        schema_resolver=make_schema_resolver(),
    )

    # Must not raise
    parsed = uuid.UUID(result["correlation_id"])
    assert parsed.version == 4


# ---------------------------------------------------------------------------
# Test: no persistence (no DB calls)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_persistence_no_db_calls():
    """execute_task must not make any database calls.
    We verify by ensuring no unexpected side-effect objects are called."""
    llm_output = json.dumps({"data": "value"})

    result = await execute_task(
        task_id="task_b",
        version="1.0.0",
        inputs={"x": 1},
        expected_schema_id="basic_schema",
        llm_client=make_llm_client(response_text=llm_output),
        prompt_loader=make_prompt_loader(),
        schema_resolver=make_schema_resolver(),
    )

    # The function signature has no db parameter -- the absence of a db parameter
    # is the structural guarantee. We verify the function completed successfully
    # and returned a result without any db dependency.
    assert result is not None
    assert result["output"] == {"data": "value"}


# ---------------------------------------------------------------------------
# Test: schema resolver failure -> TaskOutputValidationError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_schema_raises_task_output_validation_error():
    """When the schema resolver cannot find the schema, execute_task must
    raise TaskOutputValidationError."""
    with pytest.raises(TaskOutputValidationError):
        await execute_task(
            task_id="some_task",
            version="1.0.0",
            inputs={"user_input": "hello"},
            expected_schema_id="nonexistent_schema",
            llm_client=make_llm_client(),
            prompt_loader=make_prompt_loader(),
            schema_resolver=make_schema_resolver_missing(),
        )


# ---------------------------------------------------------------------------
# Test: custom exception hierarchy
# ---------------------------------------------------------------------------


def test_exception_hierarchy():
    """All custom exceptions must inherit from TaskExecutionError."""
    assert issubclass(TaskPromptNotFoundError, TaskExecutionError)
    assert issubclass(TaskOutputParseError, TaskExecutionError)
    assert issubclass(TaskOutputValidationError, TaskExecutionError)


# ---------------------------------------------------------------------------
# Test: array of objects validated per-item against object schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_array_output_validated_per_item():
    """When the LLM returns a JSON array and the schema type is 'object',
    each array item must be validated individually.

    This is the propose_work_statements pattern: task prompt asks for a JSON
    array of WS objects, schema defines a single WS object.
    """
    ws_schema = {
        "type": "object",
        "required": ["ws_id", "title"],
        "properties": {
            "ws_id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
        },
    }
    llm_output = json.dumps([
        {"ws_id": "WS-001", "title": "First"},
        {"ws_id": "WS-002", "title": "Second"},
    ])

    result = await execute_task(
        task_id="propose_ws",
        version="1.0.0",
        inputs={"work_package": "wp data", "technical_architecture": "ta data"},
        expected_schema_id="work_statement",
        llm_client=make_llm_client(response_text=llm_output),
        prompt_loader=make_prompt_loader(),
        schema_resolver=make_schema_resolver(schema=ws_schema),
    )

    assert result["output"] == [
        {"ws_id": "WS-001", "title": "First"},
        {"ws_id": "WS-002", "title": "Second"},
    ]


@pytest.mark.asyncio
async def test_array_output_invalid_item_raises():
    """When an array item fails schema validation, TaskOutputValidationError
    must be raised."""
    ws_schema = {
        "type": "object",
        "required": ["ws_id", "title"],
        "properties": {
            "ws_id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
        },
    }
    llm_output = json.dumps([
        {"ws_id": "WS-001", "title": "Valid"},
        {"ws_id": "WS-002"},  # missing required 'title'
    ])

    with pytest.raises(TaskOutputValidationError):
        await execute_task(
            task_id="propose_ws",
            version="1.0.0",
            inputs={},
            expected_schema_id="work_statement",
            llm_client=make_llm_client(response_text=llm_output),
            prompt_loader=make_prompt_loader(),
            schema_resolver=make_schema_resolver(schema=ws_schema),
        )

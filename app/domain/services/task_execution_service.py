"""Task Execution Service - reusable primitive for non-workflow LLM call sites.

This module provides a single entry point (execute_task) that handles the full
lifecycle of a certified task prompt execution:

  1. Prompt resolution from combine-config via PromptLoader
  2. LLM invocation via an injectable async client
  3. ADR-010 aligned correlation logging
  4. JSON parsing of LLM output
  5. Schema validation of parsed output

NO PERSISTENCE -- callers are responsible for persisting results.

WS-WB-022 deliverable.
"""

import logging
import uuid
from typing import Any, Protocol, runtime_checkable

import jsonschema

from app.config.package_loader import (
    PackageNotFoundError,
    VersionNotFoundError,
)
from app.domain.services.llm_response_parser import LLMResponseParser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class TaskExecutionError(Exception):
    """Base exception for task execution failures."""
    pass


class TaskPromptNotFoundError(TaskExecutionError):
    """Raised when the certified task prompt cannot be resolved."""
    pass


class TaskOutputParseError(TaskExecutionError):
    """Raised when the LLM output cannot be parsed as valid JSON."""
    pass


class TaskOutputValidationError(TaskExecutionError):
    """Raised when the parsed output fails schema validation."""
    pass


# ---------------------------------------------------------------------------
# Protocols for injectable dependencies
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for an async LLM client with a complete() method."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str: ...


@runtime_checkable
class SchemaResolver(Protocol):
    """Protocol for resolving a schema dict by ID."""

    def resolve(self, schema_id: str) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Default schema resolver (delegates to PackageLoader)
# ---------------------------------------------------------------------------


class PackageSchemaResolver:
    """Resolves schemas from combine-config via PackageLoader.get_schema()."""

    def __init__(self) -> None:
        from app.config.package_loader import get_package_loader
        self._loader = get_package_loader()

    def resolve(self, schema_id: str) -> dict[str, Any]:
        """Load and return a schema dict.

        Raises PackageNotFoundError or VersionNotFoundError if not available.
        """
        standalone = self._loader.get_schema(schema_id)
        return standalone.content


# ---------------------------------------------------------------------------
# Core execute_task function
# ---------------------------------------------------------------------------


async def execute_task(
    task_id: str,
    version: str,
    inputs: dict[str, Any],
    expected_schema_id: str,
    *,
    llm_client: Any = None,
    prompt_loader: Any = None,
    schema_resolver: Any = None,
) -> dict[str, Any]:
    """Execute a certified task prompt and return schema-validated output.

    This is the reusable primitive for non-workflow LLM call sites.
    No persistence -- caller is responsible for persisting results.

    Args:
        task_id: Task prompt identifier in combine-config (e.g. "intake_gate").
        version: Prompt version (e.g. "1.0.0").
        inputs: Dict of input variables to format into the prompt.
        expected_schema_id: Schema identifier to validate LLM output against.
        llm_client: Injectable async LLM client (default: None -> must be provided).
        prompt_loader: Injectable prompt loader (default: PromptLoader()).
        schema_resolver: Injectable schema resolver (default: PackageSchemaResolver()).

    Returns:
        Dict with keys:
            - correlation_id: str (UUID4, unique per run)
            - output: dict (schema-validated parsed LLM output)
            - task_id: str
            - version: str

    Raises:
        TaskPromptNotFoundError: If the task prompt does not exist.
        TaskOutputParseError: If the LLM output is not valid JSON.
        TaskOutputValidationError: If the output fails schema validation,
            or if the schema itself cannot be resolved.
    """
    correlation_id = str(uuid.uuid4())

    # --- Default dependencies ---
    # PromptLoader is imported lazily to avoid the pre-existing circular import
    # chain in app.domain.workflow.__init__ (see MEMORY.md).
    if prompt_loader is None:
        from app.domain.workflow.prompt_loader import PromptLoader
        prompt_loader = PromptLoader()
    if schema_resolver is None:
        schema_resolver = PackageSchemaResolver()

    # --- 1. Prompt resolution ---
    task_ref = f"prompt:task:{task_id}:{version}"
    logger.info(
        "TaskExecution[%s] starting: task_ref=%s",
        correlation_id, task_ref,
    )
    try:
        prompt_text = prompt_loader.load_task(task_ref)
    except Exception as exc:
        logger.error(
            "TaskExecution[%s] prompt not found: %s",
            correlation_id, task_ref,
        )
        raise TaskPromptNotFoundError(
            f"Task prompt not found: {task_ref}"
        ) from exc

    # --- 2. Schema resolution (eager, before LLM call) ---
    try:
        schema = schema_resolver.resolve(expected_schema_id)
    except (PackageNotFoundError, VersionNotFoundError) as exc:
        logger.error(
            "TaskExecution[%s] schema not found: %s",
            correlation_id, expected_schema_id,
        )
        raise TaskOutputValidationError(
            f"Schema not found: {expected_schema_id}"
        ) from exc

    # --- 3. LLM invocation ---
    # Format prompt with inputs
    formatted_prompt = prompt_text
    for key, value in inputs.items():
        formatted_prompt = formatted_prompt.replace(f"{{{{{key}}}}}", str(value))

    messages = [{"role": "user", "content": formatted_prompt}]

    logger.info(
        "TaskExecution[%s] invoking LLM",
        correlation_id,
    )
    raw_output = await llm_client.complete(
        messages,
        correlation_id=correlation_id,
        task_ref=task_ref,
        artifact_type="task_execution",
    )

    # --- 4. JSON parsing ---
    logger.debug(
        "TaskExecution[%s] raw_output (first 500 chars): %.500s",
        correlation_id, raw_output,
    )
    parser = LLMResponseParser()
    parse_result = parser.parse(raw_output)

    if not parse_result.success or parse_result.data is None:
        error_detail = "; ".join(parse_result.error_messages) if parse_result.error_messages else "unknown parse failure"
        logger.error(
            "TaskExecution[%s] output parse failed: %s",
            correlation_id, error_detail,
        )
        raise TaskOutputParseError(
            f"Failed to parse LLM output as JSON: {error_detail}"
        )

    parsed_output = parse_result.data

    # --- 5. Schema validation ---
    # When the LLM returns a JSON array but the schema expects an object,
    # validate each item individually (e.g., propose_work_statements returns
    # an array of WS objects, each validated against the work_statement schema).
    try:
        if (
            isinstance(parsed_output, list)
            and schema.get("type") == "object"
        ):
            for i, item in enumerate(parsed_output):
                jsonschema.validate(item, schema)
        else:
            jsonschema.validate(parsed_output, schema)
    except jsonschema.ValidationError as exc:
        logger.error(
            "TaskExecution[%s] schema validation failed: %s",
            correlation_id, exc.message,
        )
        raise TaskOutputValidationError(
            f"Output failed schema validation: {exc.message}"
        ) from exc

    logger.info(
        "TaskExecution[%s] completed successfully",
        correlation_id,
    )

    return {
        "correlation_id": correlation_id,
        "output": parsed_output,
        "task_id": task_id,
        "version": version,
    }

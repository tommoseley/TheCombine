"""LLM-backed node executors for Document Interaction Workflows (ADR-039).

This module provides factory functions to create node executors with real LLM
integration, including ADR-010 logging compliance.

Key Requirements (WS-ADR-025 Phase 1):
- Load task prompts from seed/prompts/tasks/
- Use existing LLM providers (app/llm/providers/)
- Integrate with ADR-010 logging (LLMExecutionLogger)
- Maintain Control Boundary Invariant: executors MUST NOT make routing decisions

Usage:
    from app.domain.workflow.nodes.llm_executors import create_llm_executors

    async def get_executor(db: AsyncSession):
        executors = await create_llm_executors(db)
        return PlanExecutor(persistence, registry, executors=executors)
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    LLMService,
    NodeExecutor,
    PromptLoader,
)
from app.domain.workflow.nodes.task import TaskNodeExecutor
from app.domain.workflow.nodes.intake_gate import IntakeGateExecutor
from app.domain.workflow.nodes.qa import QANodeExecutor
from app.domain.workflow.nodes.gate import GateNodeExecutor
from app.domain.workflow.nodes.end import EndNodeExecutor
from app.domain.workflow.plan_models import NodeType
from app.domain.workflow.prompt_loader import PromptLoader as FilePromptLoader
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.models import Message, MessageRole

if TYPE_CHECKING:
    from app.domain.services.llm_execution_logger import LLMExecutionLogger
    from app.domain.repositories.llm_log_repository import LLMLogRepository

logger = logging.getLogger(__name__)


class PromptLoaderAdapter:
    """Adapts the file-based PromptLoader to the PromptLoader protocol.

    Maps protocol method names to existing PromptLoader methods:
    - load_task_prompt() -> load_task()
    - load_role_prompt() -> load_role()
    """

    def __init__(self, file_loader: Optional[FilePromptLoader] = None):
        self._loader = file_loader or FilePromptLoader()

    def load_task_prompt(self, task_ref: str) -> str:
        """Load a task prompt by reference."""
        return self._loader.load_task(task_ref)

    def load_role_prompt(self, role_ref: str) -> str:
        """Load a role prompt by reference."""
        return self._loader.load_role(role_ref)


class LoggingLLMService:
    """LLM service with ADR-010 logging integration.

    Wraps an LLM provider (e.g., AnthropicProvider) and logs all executions
    using LLMExecutionLogger for audit compliance.

    INVARIANT: This service performs LLM completion only. It does NOT:
    - Make workflow routing decisions
    - Emit terminal outcomes
    - Bypass governance controls
    """

    DEFAULT_MODEL = "sonnet"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.7

    def __init__(
        self,
        provider: AnthropicProvider,
        execution_logger: Optional[LLMExecutionLogger] = None,
        default_model: str = DEFAULT_MODEL,
        default_max_tokens: int = DEFAULT_MAX_TOKENS,
        default_temperature: float = DEFAULT_TEMPERATURE,
    ):
        """Initialize the logging LLM service.

        Args:
            provider: The underlying LLM provider
            execution_logger: Optional ADR-010 logger (if None, logging is skipped)
            default_model: Default model to use
            default_max_tokens: Default max tokens
            default_temperature: Default temperature
        """
        self._provider = provider
        self._logger = execution_logger
        self._default_model = default_model
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a completion with ADR-010 logging.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Additional parameters (model, max_tokens, temperature,
                     correlation_id, artifact_type, task_ref)

        Returns:
            The LLM response content as a string
        """
        # Extract logging metadata from kwargs
        correlation_id = kwargs.pop("correlation_id", uuid4())
        project_id = kwargs.pop("project_id", None)
        artifact_type = kwargs.pop("artifact_type", "workflow_node")
        task_ref = kwargs.pop("task_ref", "unknown")
        node_id = kwargs.pop("node_id", None)

        # Extract LLM parameters
        model = kwargs.pop("model", self._default_model)
        max_tokens = kwargs.pop("max_tokens", self._default_max_tokens)
        temperature = kwargs.pop("temperature", self._default_temperature)

        # Convert messages to Message objects
        message_objects = []
        for msg in messages:
            role = MessageRole(msg["role"])
            message_objects.append(Message(role=role, content=msg["content"]))

        # Start logging run if logger available
        run_id = None
        if self._logger:
            try:
                effective_prompt = self._build_effective_prompt(messages, system_prompt)
                run_id = await self._logger.start_run(
                    correlation_id=correlation_id if isinstance(correlation_id, UUID) else UUID(str(correlation_id)),
                    project_id=project_id,
                    artifact_type=artifact_type,
                    role="workflow_executor",
                    model_provider="anthropic",
                    model_name=model,
                    prompt_id=task_ref,
                    prompt_version="1.0",
                    effective_prompt=effective_prompt,
                )

                # Log inputs
                if system_prompt:
                    await self._logger.add_input(run_id, "system_prompt", system_prompt)
                for i, msg in enumerate(messages):
                    await self._logger.add_input(
                        run_id,
                        f"message_{i}_{msg['role']}",
                        msg["content"],
                    )
            except Exception as e:
                logger.warning(f"Failed to start LLM logging: {e}")
                run_id = None

        # Execute LLM call
        try:
            response = await self._provider.complete(
                messages=message_objects,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )

            # Log success
            if run_id and self._logger:
                try:
                    await self._logger.add_output(run_id, "response", response.content)
                    await self._logger.complete_run(
                        run_id=run_id,
                        status="SUCCESS",
                        usage={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "total_tokens": response.total_tokens,
                        },
                        metadata={
                            "latency_ms": response.latency_ms,
                            "cached": response.cached,
                            "stop_reason": response.stop_reason,
                            "node_id": node_id,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to complete LLM logging: {e}")

            return response.content

        except Exception as e:
            # Log error
            if run_id and self._logger:
                try:
                    await self._logger.log_error(
                        run_id=run_id,
                        stage="llm_completion",
                        severity="ERROR",
                        error_code="LLM_ERROR",
                        message=str(e),
                    )
                    await self._logger.complete_run(
                        run_id=run_id,
                        status="FAILED",
                        usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        metadata={"error": str(e), "node_id": node_id},
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log LLM error: {log_error}")
            raise

    def _build_effective_prompt(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
    ) -> str:
        """Build the effective prompt string for hashing/logging."""
        parts = []
        if system_prompt:
            parts.append(f"[SYSTEM]\n{system_prompt}")
        for msg in messages:
            parts.append(f"[{msg['role'].upper()}]\n{msg['content']}")
        return "\n\n".join(parts)


async def create_llm_executors(
    db: AsyncSession,
    api_key: Optional[str] = None,
    enable_logging: bool = True,
) -> Dict[NodeType, NodeExecutor]:
    """Create a complete set of LLM-backed executors.

    Args:
        db: Database session for LLM logging
        api_key: Optional Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        enable_logging: Whether to enable ADR-010 logging (default True)

    Returns:
        Dict mapping NodeType to executor instance

    Raises:
        ValueError: If API key not provided and not in environment
    """
    # Get API key
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
            "or pass api_key parameter."
        )

    # Create provider
    provider = AnthropicProvider(api_key=api_key)

    # Create logger if enabled (deferred import to avoid circular dependency)
    execution_logger = None
    if enable_logging:
        from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
        from app.domain.services.llm_execution_logger import LLMExecutionLogger
        repo = PostgresLLMLogRepository(db)
        execution_logger = LLMExecutionLogger(repo)

    # Create LLM service
    llm_service = LoggingLLMService(
        provider=provider,
        execution_logger=execution_logger,
    )

    # Create prompt loader
    prompt_loader = PromptLoaderAdapter()

    # Create executors
    task_executor = TaskNodeExecutor(
        llm_service=llm_service,
        prompt_loader=prompt_loader,
    )
    
    return {
        NodeType.INTAKE_GATE: IntakeGateExecutor(
            llm_service=llm_service,
            prompt_loader=prompt_loader,
        ),
        NodeType.TASK: task_executor,
        NodeType.PGC: task_executor,  # PGC uses same executor as TASK
        NodeType.QA: QANodeExecutor(
            llm_service=llm_service,
            prompt_loader=prompt_loader,
        ),
        NodeType.GATE: GateNodeExecutor(),
        NodeType.END: EndNodeExecutor(),
    }


def create_mock_llm_service() -> LoggingLLMService:
    """Create a mock LLM service for testing without API calls.

    Returns a service that will fail on actual LLM calls - use for
    unit testing executor logic without LLM integration.
    """
    class MockProvider:
        @property
        def provider_name(self) -> str:
            return "mock"

        async def complete(self, **kwargs):
            raise NotImplementedError("Mock provider - no real LLM calls")

    return LoggingLLMService(
        provider=MockProvider(),  # type: ignore
        execution_logger=None,
    )

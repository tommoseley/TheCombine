"""LLM provider factory."""

from typing import Optional

from app.llm import (
    LLMProvider,
    AnthropicProvider,
    MockLLMProvider,
    PromptBuilder,
    OutputParser,
    DocumentCondenser,
    TelemetryService,
    InMemoryTelemetryStore,
)
from app.persistence import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
)
from app.execution.llm_step_executor import LLMStepExecutor


def create_llm_provider(
    environment: str = "development",
    api_key: Optional[str] = None,
    enable_caching: bool = True,
) -> LLMProvider:
    """
    Create appropriate LLM provider based on environment.
    
    Args:
        environment: deployment environment (test, development, production)
        api_key: Anthropic API key (required for non-test)
        enable_caching: Enable prompt caching
        
    Returns:
        Configured LLM provider
    """
    if environment == "test":
        return MockLLMProvider(
            default_response='{"status": "ok", "data": {}}',
        )
    
    if not api_key:
        raise ValueError("API key required for non-test environments")
    
    return AnthropicProvider(
        api_key=api_key,
        enable_caching=enable_caching,
    )


def create_step_executor(
    llm_provider: LLMProvider,
    telemetry_store: Optional[InMemoryTelemetryStore] = None,
    default_model: str = "sonnet",
) -> LLMStepExecutor:
    """
    Create a fully configured step executor.
    
    Args:
        llm_provider: LLM provider to use
        telemetry_store: Optional telemetry store (creates one if not provided)
        default_model: Default model for LLM calls
        
    Returns:
        Configured LLMStepExecutor
    """
    store = telemetry_store or InMemoryTelemetryStore()
    
    return LLMStepExecutor(
        llm_provider=llm_provider,
        prompt_builder=PromptBuilder(),
        output_parser=OutputParser(),
        telemetry=TelemetryService(store),
        condenser=DocumentCondenser(),
        default_model=default_model,
    )


def create_test_executor() -> tuple[LLMStepExecutor, InMemoryTelemetryStore]:
    """
    Create executor configured for testing.
    
    Returns:
        Tuple of (executor, telemetry_store)
    """
    store = InMemoryTelemetryStore()
    provider = MockLLMProvider(
        default_response='{"status": "ok"}',
    )
    
    executor = LLMStepExecutor(
        llm_provider=provider,
        prompt_builder=PromptBuilder(),
        output_parser=OutputParser(),
        telemetry=TelemetryService(store),
        condenser=DocumentCondenser(),
        default_model="mock",
    )
    
    return executor, store

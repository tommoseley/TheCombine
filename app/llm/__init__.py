"""LLM integration module for The Combine."""

from app.llm.models import (
    Message,
    MessageRole,
    LLMResponse,
    LLMRequest,
    LLMError,
    LLMException,
)
from app.llm.providers.base import LLMProvider, BaseLLMProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.mock import (
    MockLLMProvider,
    MockCall,
    create_json_response_provider,
    create_echo_provider,
)
from app.llm.prompt_builder import (
    PromptBuilder,
    PromptContext,
    DEFAULT_ROLE_TEMPLATES,
)
from app.llm.document_condenser import (
    DocumentCondenser,
    CondenseConfig,
    ROLE_FOCUS,
)
from app.llm.output_parser import (
    OutputParser,
    OutputValidator,
    ValidationResult,
    ValidationError,
    ClarificationDetector,
    ClarificationResult,
    ClarificationQuestion,
)
from app.llm.telemetry import (
    CostCalculator,
    MODEL_PRICING,
    LLMCallRecord,
    CostSummary,
    ModelUsage,
    InMemoryTelemetryStore,
    TelemetryService,
)

__all__ = [
    # Models
    "Message",
    "MessageRole",
    "LLMResponse",
    "LLMRequest",
    "LLMError",
    "LLMException",
    # Providers
    "LLMProvider",
    "BaseLLMProvider",
    "AnthropicProvider",
    "MockLLMProvider",
    "MockCall",
    "create_json_response_provider",
    "create_echo_provider",
    # Prompt building
    "PromptBuilder",
    "PromptContext",
    "DEFAULT_ROLE_TEMPLATES",
    # Document condensing
    "DocumentCondenser",
    "CondenseConfig",
    "ROLE_FOCUS",
    # Output parsing
    "OutputParser",
    "OutputValidator",
    "ValidationResult",
    "ValidationError",
    "ClarificationDetector",
    "ClarificationResult",
    "ClarificationQuestion",
    # Telemetry
    "CostCalculator",
    "MODEL_PRICING",
    "LLMCallRecord",
    "CostSummary",
    "ModelUsage",
    "InMemoryTelemetryStore",
    "TelemetryService",
]

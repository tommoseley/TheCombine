"""LLM domain models."""

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum


class MessageRole(str, Enum):
    """Message roles for LLM conversations."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A message in an LLM conversation."""
    role: MessageRole
    content: str
    
    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for API calls."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    stop_reason: str = "end_turn"
    cached: bool = False
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


@dataclass
class LLMRequest:
    """Request to an LLM provider (for logging)."""
    messages: List[Message]
    model: str
    max_tokens: int
    temperature: float
    system_prompt: Optional[str] = None
    
    @property
    def prompt_text(self) -> str:
        """Get combined prompt text for hashing/logging."""
        parts = []
        if self.system_prompt:
            parts.append(f"[SYSTEM]\n{self.system_prompt}")
        for msg in self.messages:
            parts.append(f"[{msg.role.value.upper()}]\n{msg.content}")
        return "\n\n".join(parts)


@dataclass
class LLMError:
    """Error from an LLM provider."""
    error_type: str
    message: str
    retryable: bool = False
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    retry_after_seconds: Optional[float] = None

    @classmethod
    def rate_limit(
        cls,
        message: str,
        request_id: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
    ) -> "LLMError":
        """Create a rate limit error."""
        return cls(
            error_type="rate_limit",
            message=message,
            retryable=True,
            status_code=429,
            request_id=request_id,
            retry_after_seconds=retry_after_seconds,
        )

    @classmethod
    def timeout(cls, message: str) -> "LLMError":
        """Create a timeout error."""
        return cls(
            error_type="timeout",
            message=message,
            retryable=True,
        )

    @classmethod
    def api_error(
        cls,
        message: str,
        status_code: int,
        request_id: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
    ) -> "LLMError":
        """Create an API error."""
        return cls(
            error_type="api_error",
            message=message,
            retryable=status_code >= 500,
            status_code=status_code,
            request_id=request_id,
            retry_after_seconds=retry_after_seconds,
        )


class LLMException(Exception):
    """Exception wrapping LLM errors."""

    def __init__(self, error: LLMError):
        self.error = error
        super().__init__(error.message)


class LLMOperationalError(LLMException):
    """Raised when all retries are exhausted for a retryable LLM error.

    Carries structured fields for honest error reporting to callers.
    """

    def __init__(
        self,
        provider: str,
        status_code: int,
        request_id: Optional[str],
        message: str,
        attempts: int,
    ):
        self.provider = provider
        self.status_code = status_code
        self.request_id = request_id
        self.attempts = attempts
        error = LLMError(
            error_type="operational_error",
            message=message,
            retryable=True,
            status_code=status_code,
            request_id=request_id,
        )
        super().__init__(error)

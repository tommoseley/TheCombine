"""LLM domain models."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
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
    
    @classmethod
    def rate_limit(cls, message: str) -> "LLMError":
        """Create a rate limit error."""
        return cls(
            error_type="rate_limit",
            message=message,
            retryable=True,
            status_code=429,
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
    def api_error(cls, message: str, status_code: int) -> "LLMError":
        """Create an API error."""
        return cls(
            error_type="api_error",
            message=message,
            retryable=status_code >= 500,
            status_code=status_code,
        )


class LLMException(Exception):
    """Exception wrapping LLM errors."""
    
    def __init__(self, error: LLMError):
        self.error = error
        super().__init__(error.message)

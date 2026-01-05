"""Mock LLM provider for testing."""

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union

from app.llm.models import Message, LLMResponse, LLMError, LLMException
from app.llm.providers.base import BaseLLMProvider


@dataclass
class MockCall:
    """Record of a mock LLM call."""
    messages: List[Message]
    model: str
    max_tokens: int
    temperature: float
    system_prompt: Optional[str]
    timestamp: float = field(default_factory=time.time)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing without API calls."""
    
    def __init__(
        self,
        default_response: str = "Mock response",
        responses: Optional[Dict[str, str]] = None,
        response_fn: Optional[Callable[[List[Message], str], str]] = None,
        latency_ms: float = 100.0,
        input_tokens: int = 100,
        output_tokens: int = 50,
    ):
        """
        Initialize mock provider.
        
        Args:
            default_response: Default response when no match found
            responses: Dict mapping prompt substrings to responses
            response_fn: Custom function to generate responses
            latency_ms: Simulated latency
            input_tokens: Simulated input token count
            output_tokens: Simulated output token count
        """
        self._default_response = default_response
        self._responses = responses or {}
        self._response_fn = response_fn
        self._latency_ms = latency_ms
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._calls: List[MockCall] = []
        self._error_on_next: Optional[LLMError] = None
    
    @property
    def provider_name(self) -> str:
        return "mock"
    
    @property
    def calls(self) -> List[MockCall]:
        """Get list of all calls made to this provider."""
        return self._calls
    
    @property
    def call_count(self) -> int:
        """Get number of calls made."""
        return len(self._calls)
    
    def last_call(self) -> Optional[MockCall]:
        """Get the most recent call."""
        return self._calls[-1] if self._calls else None
    
    def set_error_on_next(self, error: LLMError) -> None:
        """Configure an error to be raised on the next call."""
        self._error_on_next = error
    
    def set_response(self, trigger: str, response: str) -> None:
        """Set a response for prompts containing the trigger string."""
        self._responses[trigger] = response
    
    def clear_calls(self) -> None:
        """Clear call history."""
        self._calls.clear()
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate mock completion."""
        # Record the call
        self._calls.append(MockCall(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        ))
        
        # Check for configured error
        if self._error_on_next:
            error = self._error_on_next
            self._error_on_next = None
            raise LLMException(error)
        
        # Get response content
        content = self._get_response(messages, system_prompt)
        
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            latency_ms=self._latency_ms,
            stop_reason="end_turn",
            cached=False,
        )
    
    def _get_response(
        self, 
        messages: List[Message], 
        system_prompt: Optional[str]
    ) -> str:
        """Determine response based on configuration."""
        # Custom function takes priority
        if self._response_fn:
            return self._response_fn(messages, system_prompt or "")
        
        # Check for trigger matches
        all_text = (system_prompt or "") + " ".join(m.content for m in messages)
        for trigger, response in self._responses.items():
            if trigger in all_text:
                return response
        
        # Default response
        return self._default_response


def create_json_response_provider(schema: Dict) -> MockLLMProvider:
    """Create a mock provider that returns JSON matching a schema."""
    import json
    
    def response_fn(messages: List[Message], system_prompt: str) -> str:
        return json.dumps(schema, indent=2)
    
    return MockLLMProvider(response_fn=response_fn)


def create_echo_provider() -> MockLLMProvider:
    """Create a mock provider that echoes the last user message."""
    def response_fn(messages: List[Message], system_prompt: str) -> str:
        user_messages = [m for m in messages if m.role.value == "user"]
        if user_messages:
            return f"Echo: {user_messages[-1].content}"
        return "No user message"
    
    return MockLLMProvider(response_fn=response_fn)

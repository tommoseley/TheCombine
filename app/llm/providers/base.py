"""LLM provider base protocol."""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol, runtime_checkable

from app.llm.models import Message, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""
    
    @property
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'anthropic', 'openai')."""
        ...
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: Conversation messages
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system prompt (some providers handle separately)
            
        Returns:
            LLMResponse with content and metadata
            
        Raises:
            LLMException: On provider errors
        """
        ...


class BaseLLMProvider(ABC):
    """Base class for LLM providers with common functionality."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        ...
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate a completion."""
        ...
    
    async def complete_with_retry(
        self,
        messages: List[Message],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> LLMResponse:
        """
        Complete with exponential backoff retry.
        
        Args:
            messages: Conversation messages
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            max_retries: Maximum retry attempts
            base_delay: Base delay between retries (doubles each attempt)
            
        Returns:
            LLMResponse with content and metadata
            
        Raises:
            LLMException: After all retries exhausted
        """
        import asyncio
        from app.llm.models import LLMException
        
        last_error = None
        delay = base_delay
        
        for attempt in range(max_retries + 1):
            try:
                return await self.complete(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt,
                )
            except LLMException as e:
                last_error = e
                if not e.error.retryable or attempt == max_retries:
                    raise
                
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
        
        raise last_error

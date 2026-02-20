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
        base_delay: float = 0.5,
    ) -> LLMResponse:
        """
        Complete with exponential backoff retry.

        Backoff schedule (default): 0.5s, 2s, 8s (base * 4^attempt).
        Respects retry_after_seconds from provider errors when present.
        Adds jitter (up to 25% of sleep time) to avoid thundering herd.

        Args:
            messages: Conversation messages
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            max_retries: Maximum retry attempts
            base_delay: Base delay between retries

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMOperationalError: After all retries exhausted on retryable errors
            LLMException: On non-retryable errors (immediate, no retry)
        """
        import asyncio
        import random
        from app.llm.models import LLMException, LLMOperationalError

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
                    break

                # Use retry_after_seconds from provider if available
                sleep_time = e.error.retry_after_seconds if e.error.retry_after_seconds else delay
                # Add jitter (up to 25% of sleep time)
                sleep_time += random.uniform(0, 0.25 * sleep_time)
                await asyncio.sleep(sleep_time)
                delay *= 4  # Exponential backoff: 0.5 → 2 → 8

        # If we broke out due to non-retryable error, raise it directly
        if last_error and not last_error.error.retryable:
            raise last_error

        # All retries exhausted on retryable error → structured operational error
        if last_error:
            raise LLMOperationalError(
                provider=self.provider_name,
                status_code=last_error.error.status_code or 0,
                request_id=last_error.error.request_id,
                message=last_error.error.message,
                attempts=max_retries + 1,
            )

        raise last_error  # Should not reach here

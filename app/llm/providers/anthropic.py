"""Anthropic Claude LLM provider."""

import time
import logging
from typing import List, Optional

import httpx

from app.llm.models import Message, MessageRole, LLMResponse, LLMError, LLMException
from app.llm.providers.base import BaseLLMProvider


logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""
    
    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"
    
    # Model aliases for convenience
    MODELS = {
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-haiku-4-20250514",
        "opus": "claude-opus-4-20250514",
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 300.0,
        enable_caching: bool = True,
    ):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
            enable_caching: Enable prompt caching headers
        """
        self._api_key = api_key
        self._base_url = base_url or self.API_URL
        self._timeout = timeout
        self._enable_caching = enable_caching
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to full model name."""
        return self.MODELS.get(model, model)
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate completion via Anthropic API."""
        model = self._resolve_model(model)
        
        # Build request
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._format_messages(messages),
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
        
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }
        
        # Add caching headers if enabled
        if self._enable_caching:
            headers["anthropic-beta"] = "prompt-caching-2024-07-31"
        
        start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._base_url,
                    json=request_body,
                    headers=headers,
                )
        except httpx.TimeoutException as e:
            raise LLMException(LLMError.timeout(f"Request timed out: {e}"))
        except httpx.RequestError as e:
            raise LLMException(LLMError.api_error(f"Request failed: {e}", 0))
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        if response.status_code == 429:
            raise LLMException(LLMError.rate_limit("Rate limit exceeded"))
        
        if response.status_code >= 400:
            error_body = response.json() if response.content else {}
            error_msg = error_body.get("error", {}).get("message", response.text)
            raise LLMException(LLMError.api_error(error_msg, response.status_code))
        
        data = response.json()
        
        # Extract content
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        
        # Extract usage
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        # Check for cache hits
        cached = usage.get("cache_read_input_tokens", 0) > 0
        
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            stop_reason=data.get("stop_reason", "end_turn"),
            cached=cached,
        )
    
    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """Format messages for Anthropic API."""
        formatted = []
        for msg in messages:
            # Anthropic API uses 'user' and 'assistant' roles only in messages
            # System is handled separately
            if msg.role == MessageRole.SYSTEM:
                continue  # Skip - handled via system parameter
            formatted.append(msg.to_dict())
        return formatted

"""
LLM Caller - Thin wrapper for Anthropic API calls.

This module provides a mockable interface to the Anthropic API with consistent
error handling, timing measurement, and token usage tracking.

Author: D-2 (Mid-Level Developer)
Epic: PIPELINE-175B
"""

from dataclasses import dataclass
from typing import Optional, Dict
import time
import logging

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)


@dataclass
class LLMCallResult:
    """Result of LLM API call with metrics."""
    success: bool
    response_text: Optional[str]
    execution_time_ms: int
    token_usage: Optional[Dict[str, int]]  # {"input_tokens": N, "output_tokens": M}
    error: Optional[str]


class LLMCaller:
    """Thin wrapper for Anthropic API calls."""
    
    def __init__(self, client):
        """
        Initialize caller with Anthropic client.
        
        Args:
            client: Configured Anthropic client instance
        """
        self._client = client
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> LLMCallResult:
        """
        Call Anthropic API and return response.
        
        Args:
            system_prompt: System prompt (role bootstrap + instructions + context)
            user_message: User message (typically "Please proceed with this phase.")
            model: Model identifier
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            
        Returns:
            LLMCallResult with response text or error
            
        Raises:
            Never raises - all errors captured in LLMCallResult
        """
        logger.debug(
            f"Calling LLM: model={model}, max_tokens={max_tokens}, temp={temperature}"
        )
        start_time = time.time()
        
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Extract response text
            response_text = response.content[0].text
            
            # Extract token usage
            token_usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
            
            logger.debug(
                f"LLM call succeeded in {elapsed_ms}ms, "
                f"tokens: input={token_usage['input_tokens']}, "
                f"output={token_usage['output_tokens']}"
            )
            
            return LLMCallResult(
                success=True,
                response_text=response_text,
                execution_time_ms=elapsed_ms,
                token_usage=token_usage,
                error=None
            )
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            logger.error(f"LLM call failed after {elapsed_ms}ms: {error_msg}")
            
            return LLMCallResult(
                success=False,
                response_text=None,
                execution_time_ms=elapsed_ms,
                token_usage=None,
                error=error_msg
            )
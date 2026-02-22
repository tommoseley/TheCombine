"""Tests for LLM retry with backoff (WS-OPS-001 Criteria 1-4).

C1: Retries on 529 — succeeds after transient failures
C2: No retries on 400/401/403 — non-retryable codes fail immediately
C3: Retry-after respected — provider-specified delay is honored
C4: Structured error on exhaustion — LLMOperationalError raised with fields
"""

import time

import pytest

from app.llm.models import LLMError, LLMException, LLMOperationalError
from app.llm.providers.mock import MockLLMProvider


class TestRetryOnTransientErrors:
    """C1: Mock provider fails twice with 529, succeeds third. Assert call_count == 3."""

    @pytest.mark.asyncio
    async def test_retries_on_529_and_succeeds(self):
        provider = MockLLMProvider(default_response="success")
        provider.set_error_sequence([
            LLMError.api_error("Overloaded", 529),
            LLMError.api_error("Overloaded", 529),
        ])

        from app.llm.models import Message, MessageRole

        result = await provider.complete_with_retry(
            messages=[Message(role=MessageRole.USER, content="test")],
            model="mock",
            max_retries=3,
            base_delay=0.01,  # Fast for tests
        )

        assert result.content == "success"
        assert provider.call_count == 3


class TestNoRetryOnNonRetryable:
    """C2: Non-retryable status codes fail immediately with call_count == 1."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401, 403])
    async def test_no_retry_on_client_errors(self, status_code):
        provider = MockLLMProvider()
        provider.set_error_sequence([
            LLMError.api_error(f"Client error {status_code}", status_code),
        ])

        from app.llm.models import Message, MessageRole

        with pytest.raises(LLMException):
            await provider.complete_with_retry(
                messages=[Message(role=MessageRole.USER, content="test")],
                model="mock",
                max_retries=3,
                base_delay=0.01,
            )

        assert provider.call_count == 1


class TestRetryAfterRespected:
    """C3: retry_after_seconds from error is honored."""

    @pytest.mark.asyncio
    async def test_retry_after_delay_is_respected(self):
        provider = MockLLMProvider(default_response="success")
        error = LLMError.api_error("Overloaded", 529)
        error.retry_after_seconds = 2.0
        provider.set_error_sequence([error])

        from app.llm.models import Message, MessageRole

        start = time.monotonic()
        result = await provider.complete_with_retry(
            messages=[Message(role=MessageRole.USER, content="test")],
            model="mock",
            max_retries=3,
            base_delay=0.01,
        )
        elapsed = time.monotonic() - start

        assert result.content == "success"
        assert elapsed >= 1.5, f"Expected >= 1.5s delay, got {elapsed:.2f}s"


class TestStructuredErrorOnExhaustion:
    """C4: All retries fail → LLMOperationalError with structured fields."""

    @pytest.mark.asyncio
    async def test_raises_operational_error_on_exhaustion(self):
        provider = MockLLMProvider()
        provider.set_error_sequence([
            LLMError.api_error("Overloaded", 529),
            LLMError.api_error("Overloaded", 529),
            LLMError.api_error("Overloaded", 529),
            LLMError.api_error("Overloaded", 529),
        ])

        from app.llm.models import Message, MessageRole

        with pytest.raises(LLMOperationalError) as exc_info:
            await provider.complete_with_retry(
                messages=[Message(role=MessageRole.USER, content="test")],
                model="mock",
                max_retries=3,
                base_delay=0.01,
            )

        err = exc_info.value
        assert err.provider == "mock"
        assert err.status_code == 529
        assert err.attempts == 4  # 1 initial + 3 retries
        assert hasattr(err, "request_id")

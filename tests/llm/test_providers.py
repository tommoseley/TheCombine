"""Tests for LLM providers."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.llm.models import Message, MessageRole, LLMResponse, LLMError, LLMException
from app.llm.providers.base import LLMProvider, BaseLLMProvider
from app.llm.providers.mock import (
    MockLLMProvider,
    create_json_response_provider,
    create_echo_provider,
)
from app.llm.providers.anthropic import AnthropicProvider


class TestMessage:
    """Tests for Message model."""
    
    def test_create_system_message(self):
        """Can create system message."""
        msg = Message.system("You are helpful.")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are helpful."
    
    def test_create_user_message(self):
        """Can create user message."""
        msg = Message.user("Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
    
    def test_create_assistant_message(self):
        """Can create assistant message."""
        msg = Message.assistant("Hi there!")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hi there!"
    
    def test_to_dict(self):
        """Message converts to dict correctly."""
        msg = Message.user("Test")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Test"}


class TestLLMResponse:
    """Tests for LLMResponse model."""
    
    def test_total_tokens(self):
        """Total tokens calculated correctly."""
        response = LLMResponse(
            content="Test",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
            latency_ms=500.0,
        )
        assert response.total_tokens == 150


class TestLLMError:
    """Tests for LLMError model."""
    
    def test_rate_limit_error(self):
        """Rate limit error is retryable."""
        error = LLMError.rate_limit("Too many requests")
        assert error.retryable is True
        assert error.status_code == 429
    
    def test_timeout_error(self):
        """Timeout error is retryable."""
        error = LLMError.timeout("Connection timed out")
        assert error.retryable is True
    
    def test_server_error_retryable(self):
        """5xx errors are retryable."""
        error = LLMError.api_error("Server error", 500)
        assert error.retryable is True
    
    def test_client_error_not_retryable(self):
        """4xx errors are not retryable."""
        error = LLMError.api_error("Bad request", 400)
        assert error.retryable is False


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""
    
    @pytest.mark.asyncio
    async def test_default_response(self):
        """Returns default response."""
        provider = MockLLMProvider(default_response="Hello!")
        
        response = await provider.complete(
            messages=[Message.user("Hi")],
            model="test-model",
        )
        
        assert response.content == "Hello!"
        assert response.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_trigger_response(self):
        """Returns response based on trigger."""
        provider = MockLLMProvider(
            default_response="Default",
            responses={"weather": "It's sunny!"},
        )
        
        response = await provider.complete(
            messages=[Message.user("What's the weather?")],
            model="test",
        )
        
        assert response.content == "It's sunny!"
    
    @pytest.mark.asyncio
    async def test_call_tracking(self):
        """Tracks all calls."""
        provider = MockLLMProvider()
        
        await provider.complete([Message.user("First")], "model1")
        await provider.complete([Message.user("Second")], "model2")
        
        assert provider.call_count == 2
        assert provider.last_call().model == "model2"
    
    @pytest.mark.asyncio
    async def test_error_injection(self):
        """Can inject errors."""
        provider = MockLLMProvider()
        provider.set_error_on_next(LLMError.rate_limit("Test rate limit"))
        
        with pytest.raises(LLMException) as exc_info:
            await provider.complete([Message.user("Test")], "model")
        
        assert exc_info.value.error.error_type == "rate_limit"
    
    @pytest.mark.asyncio
    async def test_error_clears_after_raise(self):
        """Error is cleared after being raised."""
        provider = MockLLMProvider(default_response="OK")
        provider.set_error_on_next(LLMError.rate_limit("Test"))
        
        with pytest.raises(LLMException):
            await provider.complete([Message.user("Test")], "model")
        
        # Next call should succeed
        response = await provider.complete([Message.user("Test")], "model")
        assert response.content == "OK"
    
    @pytest.mark.asyncio
    async def test_custom_response_function(self):
        """Custom response function works."""
        def custom_fn(messages, system):
            return f"Got {len(messages)} messages"
        
        provider = MockLLMProvider(response_fn=custom_fn)
        
        response = await provider.complete(
            messages=[Message.user("A"), Message.user("B")],
            model="test",
        )
        
        assert response.content == "Got 2 messages"
    
    @pytest.mark.asyncio
    async def test_provider_name(self):
        """Provider name is 'mock'."""
        provider = MockLLMProvider()
        assert provider.provider_name == "mock"


class TestCreateJsonResponseProvider:
    """Tests for JSON response provider factory."""
    
    @pytest.mark.asyncio
    async def test_returns_json(self):
        """Returns JSON matching schema."""
        schema = {"name": "Test", "value": 42}
        provider = create_json_response_provider(schema)
        
        response = await provider.complete([Message.user("Test")], "model")
        
        parsed = json.loads(response.content)
        assert parsed == schema


class TestCreateEchoProvider:
    """Tests for echo provider factory."""
    
    @pytest.mark.asyncio
    async def test_echoes_user_message(self):
        """Echoes the last user message."""
        provider = create_echo_provider()
        
        response = await provider.complete(
            messages=[Message.user("Hello world")],
            model="test",
        )
        
        assert "Hello world" in response.content


class TestBaseLLMProviderRetry:
    """Tests for retry logic in BaseLLMProvider."""
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Retries on rate limit error."""
        provider = MockLLMProvider(default_response="Success")
        
        # Fail first time, succeed second
        call_count = 0
        original_complete = provider.complete
        
        async def failing_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMException(LLMError.rate_limit("Rate limited"))
            return await original_complete(*args, **kwargs)
        
        provider.complete = failing_complete
        
        response = await provider.complete_with_retry(
            messages=[Message.user("Test")],
            model="test",
            max_retries=3,
            base_delay=0.01,
        )
        
        assert response.content == "Success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable(self):
        """Does not retry non-retryable errors."""
        provider = MockLLMProvider()
        provider.set_error_on_next(LLMError.api_error("Bad request", 400))
        
        with pytest.raises(LLMException):
            await provider.complete_with_retry(
                messages=[Message.user("Test")],
                model="test",
                max_retries=3,
            )
        
        assert provider.call_count == 1

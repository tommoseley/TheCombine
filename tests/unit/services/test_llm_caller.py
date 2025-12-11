"""
Unit tests for LLMCaller.

Tests cover successful calls, error handling, and timing measurement.

Author: D-2 (Mid-Level Developer)
Epic: PIPELINE-175B
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.combine.services.llm_caller import LLMCaller, LLMCallResult


class TestLLMCaller:
    """Tests for LLMCaller."""
    
    def test_successful_call(self):
        """Should return success result with response text and metrics."""
        # Mock Anthropic client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_client.messages.create.return_value = mock_response
        
        caller = LLMCaller(mock_client)
        result = caller.call("system prompt", "user message")
        
        assert result.success is True
        assert result.response_text == "Test response"
        assert result.token_usage == {"input_tokens": 100, "output_tokens": 50}
        assert result.execution_time_ms >= 0  # Fixed: Mocked calls may be 0ms
        assert result.error is None
    
    def test_api_error(self):
        """Should return failure result on API error."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        
        caller = LLMCaller(mock_client)
        result = caller.call("system prompt", "user message")
        
        assert result.success is False
        assert result.response_text is None
        assert result.token_usage is None
        assert "Exception: API Error" in result.error
        assert result.execution_time_ms >= 0  # Fixed: Still measures time, may be 0ms for mock
    
    def test_custom_parameters(self):
        """Should pass custom parameters to API."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_client.messages.create.return_value = mock_response
        
        caller = LLMCaller(mock_client)
        caller.call(
            "system",
            "user",
            model="custom-model",
            max_tokens=2048,
            temperature=0.5
        )
        
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "custom-model"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.5
    
    def test_never_raises_exceptions(self):
        """Should never raise exceptions, always return LLMCallResult."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = RuntimeError("Unexpected error")
        
        caller = LLMCaller(mock_client)
        # Should not raise
        result = caller.call("system", "user")
        
        assert isinstance(result, LLMCallResult)
        assert result.success is False
    
    def test_timing_measurement_accuracy(self):
        """Should measure execution time accurately."""
        import time
        
        mock_client = Mock()
        def slow_create(*args, **kwargs):
            time.sleep(0.1)  # 100ms delay
            response = Mock()
            response.content = [Mock(text="Response")]
            response.usage = Mock(input_tokens=10, output_tokens=5)
            return response
        
        mock_client.messages.create.side_effect = slow_create
        
        caller = LLMCaller(mock_client)
        result = caller.call("system", "user")
        
        # For real delays, timing should be measured
        assert result.execution_time_ms >= 100
        assert result.execution_time_ms < 200  # Some tolerance
    
    def test_token_usage_extraction(self):
        """Should correctly extract token usage from response."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=123, output_tokens=456)
        mock_client.messages.create.return_value = mock_response
        
        caller = LLMCaller(mock_client)
        result = caller.call("system", "user")
        
        assert result.token_usage["input_tokens"] == 123
        assert result.token_usage["output_tokens"] == 456
    
    def test_message_structure(self):
        """Should structure messages correctly for API."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_client.messages.create.return_value = mock_response
        
        caller = LLMCaller(mock_client)
        caller.call("system prompt", "user message")
        
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "system prompt"
        assert call_kwargs["messages"] == [{"role": "user", "content": "user message"}]
    
    def test_error_types_captured(self):
        """Should capture error type in error message."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = ValueError("Invalid value")
        
        caller = LLMCaller(mock_client)
        result = caller.call("system", "user")
        
        assert "ValueError" in result.error
        assert "Invalid value" in result.error


# Total: 8 tests
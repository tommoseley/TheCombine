"""Tests for UsageRecorder with token tracking."""
import pytest
from unittest.mock import Mock
from app.orchestrator_api.services.usage_recorder import UsageRecorder, UsageRecord

class TestUsageRecorderTokens:
    def test_records_token_counts(self):
        repo = Mock()
        # Mock to return object with .id attribute
        mock_usage = Mock()
        mock_usage.id = "usage_123"
        repo.record_usage.return_value = mock_usage
        
        recorder = UsageRecorder(repo)
        
        usage = UsageRecord(
            pipeline_id="pip_test",
            prompt_id="rp_123",
            role_name="pm",
            phase_name="pm_phase",
            input_tokens=1000,
            output_tokens=500
        )
        
        result = recorder.record_usage(usage)
        assert result is True
        repo.record_usage.assert_called_once()
        call_args = repo.record_usage.call_args[1]
        assert call_args["input_tokens"] == 1000
        assert call_args["output_tokens"] == 500
        assert "cost_usd" in call_args
    
    def test_calculates_cost(self):
        repo = Mock()
        mock_usage = Mock()
        mock_usage.id = "usage_123"
        repo.record_usage.return_value = mock_usage
        
        recorder = UsageRecorder(repo)
        
        usage = UsageRecord(
            pipeline_id="pip_test",
            prompt_id="rp_123",
            role_name="pm",
            phase_name="pm_phase",
            input_tokens=10000,
            output_tokens=2000
        )
        
        recorder.record_usage(usage)
        call_args = repo.record_usage.call_args[1]
        expected_cost = (10000 / 1_000_000 * 3.0) + (2000 / 1_000_000 * 15.0)
        assert call_args["cost_usd"] == round(expected_cost, 6)
    
    def test_never_raises(self):
        repo = Mock()
        repo.record_usage.side_effect = Exception("DB error")
        recorder = UsageRecorder(repo)
        
        usage = UsageRecord(
            pipeline_id="pip_test",
            prompt_id="rp_123",
            role_name="pm",
            phase_name="pm_phase"
        )
        
        result = recorder.record_usage(usage)
        assert result is False
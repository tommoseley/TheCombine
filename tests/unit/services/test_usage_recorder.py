"""
Unit tests for UsageRecorder.

Tests cover successful recording, error handling, and QA Issue #4
(structured logging).

Author: D-3 (Junior Developer)
Epic: PIPELINE-175B
"""

import pytest
from unittest.mock import Mock
from app.orchestrator_api.services.usage_recorder import (
    UsageRecorder,
    UsageRecord
)


class TestUsageRecorder:
    """Tests for UsageRecorder."""
    
    def test_successful_recording(self):
        """Should return True on successful recording."""
        mock_repo = Mock()
        mock_repo.record_usage.return_value = "usage_123"
        
        recorder = UsageRecorder(mock_repo)
        usage = UsageRecord(
            pipeline_id="pip_123",
            prompt_id="rp_456",
            role_name="pm",
            phase_name="pm_phase"
        )
        
        result = recorder.record_usage(usage)
        
        assert result is True
        mock_repo.record_usage.assert_called_once_with(
            pipeline_id="pip_123",
            prompt_id="rp_456"
        )
    
    def test_repository_error_returns_false(self):
        """Should return False on repository error."""
        mock_repo = Mock()
        mock_repo.record_usage.side_effect = Exception("Database error")
        
        recorder = UsageRecorder(mock_repo)
        usage = UsageRecord(
            pipeline_id="pip_123",
            prompt_id="rp_456",
            role_name="pm",
            phase_name="pm_phase"
        )
        
        result = recorder.record_usage(usage)
        
        assert result is False
    
    def test_never_raises_exceptions(self):
        """Should never raise exceptions."""
        mock_repo = Mock()
        mock_repo.record_usage.side_effect = RuntimeError("Unexpected error")
        
        recorder = UsageRecorder(mock_repo)
        usage = UsageRecord(
            pipeline_id="pip_123",
            prompt_id="rp_456",
            role_name="pm",
            phase_name="pm_phase"
        )
        
        # Should not raise
        result = recorder.record_usage(usage)
        assert result is False
    
    def test_structured_logging_on_failure(self, caplog):
        """QA Issue #4: Should log structured warning on failure."""
        import logging
        caplog.set_level(logging.WARNING)
        
        mock_repo = Mock()
        mock_repo.record_usage.side_effect = Exception("IntegrityError: FK constraint")
        
        recorder = UsageRecorder(mock_repo)
        usage = UsageRecord(
            pipeline_id="pip_abc123",
            prompt_id="rp_xyz789",
            role_name="pm",
            phase_name="pm_phase"
        )
        
        recorder.record_usage(usage)
        
        # Check structured fields are logged
        assert "Usage record failure" in caplog.text
        # Extra fields should be in log record
        for record in caplog.records:
            if record.levelname == "WARNING":
                assert record.pipeline_id == "pip_abc123"
                assert record.prompt_id == "rp_xyz789"
                assert record.role_name == "pm"
                assert record.phase_name == "pm_phase"
                assert "event" in record.__dict__
                assert record.event == "usage_record_failure"
    
    def test_logs_debug_on_success(self, caplog):
        """Should log DEBUG on successful recording."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        mock_repo = Mock()
        mock_repo.record_usage.return_value = "usage_123"
        
        recorder = UsageRecorder(mock_repo)
        usage = UsageRecord(
            pipeline_id="pip_123",
            prompt_id="rp_456",
            role_name="pm",
            phase_name="pm_phase"
        )
        
        recorder.record_usage(usage)
        
        assert "Recorded usage: usage_id=usage_123" in caplog.text


# Total: 5 tests
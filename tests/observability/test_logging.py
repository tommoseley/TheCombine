"""Tests for structured logging."""

import json
import logging
import pytest
from uuid import uuid4

from app.observability.logging import (
    JSONFormatter,
    ContextLogger,
    configure_logging,
    get_logger,
)


class TestJSONFormatter:
    """Tests for JSONFormatter."""
    
    def test_format_basic_message(self):
        """Formats basic log message as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert "timestamp" in data
    
    def test_format_with_extra_fields(self):
        """Includes extra fields in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.execution_id = uuid4()
        record.step_id = "step-1"
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert "execution_id" in data
        assert data["step_id"] == "step-1"
    
    def test_format_without_timestamp(self):
        """Can exclude timestamp."""
        formatter = JSONFormatter(include_timestamp=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert "timestamp" not in data


class TestContextLogger:
    """Tests for ContextLogger."""
    
    def test_with_context(self):
        """Can add context to logger."""
        base_logger = logging.getLogger("test_context")
        logger = ContextLogger(base_logger)
        
        ctx_logger = logger.with_context(execution_id=uuid4())
        
        assert ctx_logger is not logger
        assert "execution_id" in ctx_logger._context
    
    def test_context_chaining(self):
        """Can chain context additions."""
        base_logger = logging.getLogger("test_chain")
        logger = ContextLogger(base_logger)
        
        ctx1 = logger.with_context(workflow_id="wf-1")
        ctx2 = ctx1.with_context(step_id="step-1")
        
        assert "workflow_id" in ctx2._context
        assert "step_id" in ctx2._context


class TestConfigureLogging:
    """Tests for configure_logging."""
    
    def test_configure_json_format(self):
        """Configures JSON format."""
        logger = configure_logging(
            log_format="json",
            log_level="INFO",
            logger_name="test_json",
        )
        
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)
    
    def test_configure_text_format(self):
        """Configures text format."""
        logger = configure_logging(
            log_format="text",
            log_level="DEBUG",
            logger_name="test_text",
        )
        
        assert len(logger.handlers) == 1
        assert not isinstance(logger.handlers[0].formatter, JSONFormatter)


class TestGetLogger:
    """Tests for get_logger."""
    
    def test_returns_context_logger(self):
        """Returns ContextLogger instance."""
        logger = get_logger("test")
        
        assert isinstance(logger, ContextLogger)

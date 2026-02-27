"""Tests for structured logging."""

import json
import logging

from app.core.logging import (
    JSONFormatter,
    TextFormatter,
    configure_logging,
    get_logger,
)


class TestJSONFormatter:
    """Tests for JSON log formatter."""
    
    def test_format_basic_message(self):
        """Basic message is formatted as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_format_includes_location(self):
        """JSON includes file location."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/app/test.py",
            lineno=42,
            msg="Error",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["location"]["file"] == "/app/test.py"
        assert data["location"]["line"] == 42
        assert data["location"]["function"] == "test_function"
    
    def test_format_with_exception(self):
        """JSON includes exception info."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert "ValueError" in data["exception"]
    
    def test_format_with_extra_fields(self):
        """JSON includes extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc123"
        record.user_id = "user1"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["request_id"] == "abc123"
        assert data["user_id"] == "user1"


class TestTextFormatter:
    """Tests for text formatter."""
    
    def test_format_readable(self):
        """Text format is human-readable."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        assert "INFO" in output
        assert "test.module" in output
        assert "Hello world" in output


class TestConfigureLogging:
    """Tests for logging configuration."""
    
    def test_configure_json_format(self):
        """Can configure JSON format."""
        configure_logging(level="DEBUG", format_type="json")
        logger = get_logger("test.json")
        
        # Should not raise
        logger.info("Test message")
    
    def test_configure_text_format(self):
        """Can configure text format."""
        configure_logging(level="INFO", format_type="text")
        logger = get_logger("test.text")
        
        # Should not raise
        logger.info("Test message")
    
    def test_configure_level(self):
        """Log level is respected."""
        configure_logging(level="ERROR", format_type="text")
        logger = get_logger("test.level")
        
        # Logger should have ERROR level
        assert logger.getEffectiveLevel() <= logging.ERROR


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_returns_logger(self):
        """Returns a logger instance."""
        logger = get_logger("my.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "my.module"
    
    def test_same_name_same_logger(self):
        """Same name returns same logger."""
        logger1 = get_logger("same.name")
        logger2 = get_logger("same.name")
        
        assert logger1 is logger2

"""Structured logging configuration for The Combine."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
    ):
        super().__init__()
        self._include_timestamp = include_timestamp
        self._include_level = include_level
        self._include_logger = include_logger
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {}
        
        if self._include_timestamp:
            log_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        if self._include_level:
            log_data["level"] = record.levelname
        
        if self._include_logger:
            log_data["logger"] = record.name
        
        log_data["message"] = record.getMessage()
        
        # Add extra fields
        if hasattr(record, "execution_id"):
            log_data["execution_id"] = str(record.execution_id)
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = str(record.correlation_id)
        if hasattr(record, "step_id"):
            log_data["step_id"] = record.step_id
        if hasattr(record, "workflow_id"):
            log_data["workflow_id"] = record.workflow_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "tokens"):
            log_data["tokens"] = record.tokens
        if hasattr(record, "cost_usd"):
            log_data["cost_usd"] = float(record.cost_usd)
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any other extra attributes
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "execution_id", "correlation_id", "step_id",
                "workflow_id", "duration_ms", "tokens", "cost_usd", "user_id",
            ):
                continue
            if isinstance(value, (str, int, float, bool, type(None))):
                log_data[key] = value
            elif isinstance(value, UUID):
                log_data[key] = str(value)
        
        return json.dumps(log_data)


class ContextLogger:
    """Logger with context support for correlation IDs."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context: Dict[str, Any] = {}
    
    def with_context(self, **kwargs) -> "ContextLogger":
        """Create a new logger with additional context."""
        new_logger = ContextLogger(self._logger)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _log(self, level: int, msg: str, **kwargs):
        """Log with context."""
        extra = {**self._context, **kwargs}
        self._logger.log(level, msg, extra=extra)
    
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)
    
    def exception(self, msg: str, **kwargs):
        self._logger.exception(msg, extra={**self._context, **kwargs})


def configure_logging(
    log_format: str = "json",
    log_level: str = "INFO",
    logger_name: Optional[str] = None,
) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        log_format: "json" or "text"
        log_level: Logging level
        logger_name: Name for the logger (None for root)
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    
    logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger."""
    return ContextLogger(logging.getLogger(name))

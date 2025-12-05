# workforce/utils/logging.py

"""Logging utilities for The Combine."""

import logging
import sys
from datetime import datetime
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with standard configuration.
    
    Args:
        name: Logger name (typically module name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='[%(asctime)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def log_info(message: str, logger_name: str = "combine") -> None:
    """Log info message."""
    logger = get_logger(logger_name)
    logger.info(message)


def log_warning(message: str, logger_name: str = "combine") -> None:
    """Log warning message."""
    logger = get_logger(logger_name)
    logger.warning(message)


def log_error(message: str, exc_info: bool = False):
    """Log error message."""
    # Your existing implementation
    print(f"ERROR: {message}")
    # Optionally handle exc_info if you want stack traces


def log_debug(message: str, logger_name: str = "combine") -> None:
    """Log debug message."""
    logger = get_logger(logger_name)
    logger.debug(message)
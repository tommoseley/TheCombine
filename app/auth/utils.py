"""
Authentication utilities.

ADR-008: Multi-Provider OAuth Authentication
Helper functions for auth system.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Return current UTC time as timezone-aware datetime.
    
    CRITICAL: All datetime operations must use timezone-aware datetimes.
    This prevents comparison errors and ensures correct behavior across timezones.
    
    Returns:
        datetime: Current UTC time with timezone info
        
    Example:
        >>> now = utcnow()
        >>> now.tzinfo is not None
        True
        >>> now.tzinfo.tzname(None)
        'UTC'
    """
    return datetime.now(timezone.utc)
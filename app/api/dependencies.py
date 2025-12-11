"""
Shared FastAPI dependencies for The Combine API.

Updated for new architecture - no global orchestrator, uses database sessions.
"""

import os
from typing import List
from datetime import datetime
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session
import logging

from database import get_db_session

logger = logging.getLogger(__name__)

# Global state
_startup_time: datetime = None


def set_startup_time(startup_time: datetime):
    """Set the application startup time (called from main.py)."""
    global _startup_time
    _startup_time = startup_time


def get_startup_time() -> datetime:
    """Get application startup time."""
    if _startup_time is None:
        # Return current time if not set
        return datetime.utcnow()
    return _startup_time


def get_valid_api_keys() -> List[str]:
    """
    Get valid API keys from environment.
    
    Returns list of valid API keys from API_KEYS env var (comma-separated).
    """
    keys_str = os.getenv("API_KEYS", "")
    if not keys_str:
        return []
    return [key.strip() for key in keys_str.split(",") if key.strip()]


async def require_api_key(
    x_api_key: str = Header(None),
    authorization: str = Header(None)
) -> str:
    """
    Require valid API key for endpoint access.
    
    Checks X-API-Key header or Authorization: Bearer header.
    Raises 401 Unauthorized if missing or invalid.
    
    Args:
        x_api_key: API key from X-API-Key header
        authorization: Bearer token from Authorization header
    
    Returns:
        Valid API key
        
    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    valid_keys = get_valid_api_keys()
    
    if not valid_keys:
        # No keys configured - allow all requests in development
        logger.warning("No API keys configured - allowing request (development mode)")
        return "dev-mode-no-auth"
    
    # Try X-API-Key header first
    api_key = x_api_key
    
    # Try Authorization: Bearer if X-API-Key not present
    if not api_key and authorization:
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]  # Strip "Bearer "
    
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Missing API key"
            }
        )
    
    if api_key not in valid_keys:
        logger.warning(f"Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Invalid API key"
            }
        )
    
    return api_key
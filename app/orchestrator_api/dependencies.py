"""Shared FastAPI dependencies."""

import os
from typing import List, Optional
from datetime import datetime
from fastapi import Header, HTTPException, status

from workforce.utils.logging import log_warning

# Global state (set by main.py during startup)
_orchestrator: Optional["Orchestrator"] = None
_startup_time: Optional[datetime] = None


def set_orchestrator(orchestrator: "Orchestrator"):
    """Set the global orchestrator instance (called from main.py)."""
    global _orchestrator
    _orchestrator = orchestrator


def set_startup_time(startup_time: datetime):
    """Set the startup time (called from main.py)."""
    global _startup_time
    _startup_time = startup_time


def get_orchestrator():
    """Get global Orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator


def get_startup_time() -> datetime:
    """Get application startup time."""
    if _startup_time is None:
        raise RuntimeError("Application not started")
    return _startup_time


def get_valid_api_keys() -> List[str]:
    """Get valid API keys from environment."""
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
    """
    valid_keys = get_valid_api_keys()
    
    if not valid_keys:
        # No keys configured - reject all requests
        log_warning("No API keys configured, rejecting request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "No API keys configured"
            }
        )
    
    # Try X-API-Key header first
    api_key = x_api_key
    
    # Try Authorization: Bearer if X-API-Key not present
    if not api_key and authorization:
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]  # Strip "Bearer "
    
    if not api_key:
        log_warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Missing API key"
            }
        )
    
    if api_key not in valid_keys:
        log_warning(f"Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Invalid API key"
            }
        )
    
    return api_key
"""
FastAPI dependencies for The Combine.

Centralized dependency injection for:
- Authentication and authorization
- Archive enforcement
- API key validation
"""

from .auth import (
    get_oidc_config, 
    require_api_key, 
    get_valid_api_keys,
    set_startup_time,
    get_startup_time
)
from .archive import verify_project_not_archived

__all__ = [
    'get_oidc_config',
    'require_api_key', 
    'get_valid_api_keys',
    'set_startup_time',
    'get_startup_time',
    'verify_project_not_archived'
]
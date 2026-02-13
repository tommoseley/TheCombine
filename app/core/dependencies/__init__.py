"""
FastAPI dependencies for The Combine.

Centralized dependency injection for:
- Authentication and authorization
- Archive enforcement
- API key validation
- LLM execution logging (ADR-010)
"""

from .auth import (
    get_oidc_config, 
    require_api_key, 
    get_valid_api_keys,
    set_startup_time,
    get_startup_time
)
from .archive import verify_project_not_archived
from .llm_logging import (
    get_llm_log_repository,
    get_llm_execution_logger,
)

__all__ = [
    'get_oidc_config',
    'require_api_key', 
    'get_valid_api_keys',
    'set_startup_time',
    'get_startup_time',
    'verify_project_not_archived',
    'get_llm_log_repository',
    'get_llm_execution_logger',
]

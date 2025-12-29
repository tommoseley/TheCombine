"""
Core infrastructure for The Combine.

Shared components used across all modules:
- Database connections and sessions
- Configuration management
- Dependency injection
- Common utilities
"""

from app.core.database import get_db, init_database
from app.core.dependencies import get_oidc_config
from app.core.config import settings

__all__ = [
    'get_db',
    'init_database',
    'get_oidc_config',
    'settings',
]
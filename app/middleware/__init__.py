"""
Middleware module.

Contains rate limiting and other middleware components.
"""
from .rate_limit import get_client_ip

__all__ = [
    'get_client_ip',
]
"""Core middleware package."""

from .deprecation import (
    DeprecationMiddleware,
    add_deprecation_warning,
    create_deprecated_redirect,
    get_deprecation_info,
    DEPRECATED_ROUTES,
)

__all__ = [
    "DeprecationMiddleware",
    "add_deprecation_warning",
    "create_deprecated_redirect",
    "get_deprecation_info",
    "DEPRECATED_ROUTES",
]
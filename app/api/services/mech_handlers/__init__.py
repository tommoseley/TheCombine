"""
Mechanical Operation Handlers.

Per ADR-047, these handlers execute deterministic data transformations
without LLM invocation.
"""

from app.api.services.mech_handlers.base import (
    MechHandler,
    MechResult,
    ExecutionContext,
    MechHandlerError,
)
from app.api.services.mech_handlers.extractor import ExtractorHandler
from app.api.services.mech_handlers.merger import MergerHandler
from app.api.services.mech_handlers.registry import (
    get_handler,
    register_handler,
    HANDLER_REGISTRY,
)

__all__ = [
    "MechHandler",
    "MechResult",
    "ExecutionContext",
    "MechHandlerError",
    "ExtractorHandler",
    "MergerHandler",
    "get_handler",
    "register_handler",
    "HANDLER_REGISTRY",
]

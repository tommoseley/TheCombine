"""
Mechanical Operation Handlers.

Per ADR-047, these handlers execute deterministic data transformations
without LLM invocation. Entry handlers return pending_entry for UI capture.
"""

from app.api.services.mech_handlers.base import (
    MechHandler,
    MechResult,
    ExecutionContext,
    MechHandlerError,
)

# Import registry first - handlers use @register_handler decorator
from app.api.services.mech_handlers.registry import (
    get_handler,
    register_handler,
    HANDLER_REGISTRY,
)

# Handler imports trigger decorator registration
from app.api.services.mech_handlers.extractor import ExtractorHandler
from app.api.services.mech_handlers.merger import MergerHandler
from app.api.services.mech_handlers.entry import EntryHandler
from app.api.services.mech_handlers.clarification_merger import (
    ClarificationMergerHandler,
)
from app.api.services.mech_handlers.invariant_pinner import InvariantPinnerHandler
from app.api.services.mech_handlers.exclusion_filter import ExclusionFilterHandler
from app.api.services.mech_handlers.router import RouterHandler
from app.api.services.mech_handlers.validator import ValidatorHandler

from app.api.services.mech_handlers.executor import (
    execute_operation,
    execute_operation_by_ref,
)

__all__ = [
    "MechHandler",
    "MechResult",
    "ExecutionContext",
    "MechHandlerError",
    "ExtractorHandler",
    "MergerHandler",
    "EntryHandler",
    "ClarificationMergerHandler",
    "InvariantPinnerHandler",
    "ExclusionFilterHandler",
    "RouterHandler",
    "ValidatorHandler",
    "get_handler",
    "register_handler",
    "HANDLER_REGISTRY",
    "execute_operation",
    "execute_operation_by_ref",
]

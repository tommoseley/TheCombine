"""
Handler registry for mechanical operations.

Maps operation type IDs to their handler classes.
"""

from typing import Dict, Optional, Type

from app.api.services.mech_handlers.base import MechHandler


# Global handler registry
HANDLER_REGISTRY: Dict[str, Type[MechHandler]] = {}


def register_handler(handler_class: Type[MechHandler]) -> Type[MechHandler]:
    """
    Register a handler class for its operation type.

    Can be used as a decorator:
        @register_handler
        class MyHandler(MechHandler):
            operation_type = "my_type"
    """
    op_type = handler_class.operation_type
    HANDLER_REGISTRY[op_type] = handler_class
    return handler_class


def get_handler(operation_type: str) -> Optional[MechHandler]:
    """
    Get a handler instance for an operation type.

    Args:
        operation_type: The operation type ID

    Returns:
        Handler instance or None if not found
    """
    handler_class = HANDLER_REGISTRY.get(operation_type)
    if handler_class:
        return handler_class()
    return None


# Register built-in handlers
def _register_builtin_handlers():
    """Register the built-in handlers."""
    from app.api.services.mech_handlers.extractor import ExtractorHandler
    from app.api.services.mech_handlers.merger import MergerHandler
    from app.api.services.mech_handlers.entry import EntryHandler

    register_handler(ExtractorHandler)
    register_handler(MergerHandler)
    register_handler(EntryHandler)


# Auto-register on module load
_register_builtin_handlers()

"""
Domain Event Bus.

Provides a publish_event function that domain code can call without
importing API-layer modules. The API layer registers its handler
(e.g., SSE broadcasting) at startup.

This breaks the circular dependency:
  domain/workflow/plan_executor.py → api/v1/routers/production.py

Before: domain imports API router directly
After:  domain publishes to event bus, API subscribes to event bus
"""

import logging
from typing import Any, Callable, Coroutine, Dict

logger = logging.getLogger(__name__)

# Registry of event handlers
# Key: handler name, Value: async callable(project_id, event_type, data)
_handlers: Dict[str, Callable[..., Coroutine]] = {}


def register_event_handler(
    name: str,
    handler: Callable[[str, str, Dict[str, Any]], Coroutine],
) -> None:
    """Register an event handler.

    Called by the API layer at startup to wire SSE broadcasting.

    Args:
        name: Handler identifier (e.g., "sse_broadcast")
        handler: Async callable(project_id, event_type, data)
    """
    _handlers[name] = handler
    logger.info(f"Registered event handler: {name}")


def unregister_event_handler(name: str) -> None:
    """Remove an event handler."""
    _handlers.pop(name, None)


async def publish_event(
    project_id: str,
    event_type: str,
    data: Dict[str, Any],
) -> None:
    """Publish a domain event to all registered handlers.

    Domain code calls this instead of importing API router functions.

    Args:
        project_id: Project to publish to
        event_type: Event type (station_transition, track_started, etc.)
        data: Event payload
    """
    for handler_name, handler in _handlers.items():
        try:
            await handler(project_id, event_type, data)
        except Exception as e:
            logger.warning(f"Event handler '{handler_name}' failed for {event_type}: {e}")

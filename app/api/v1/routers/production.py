"""Production Line API routes (ADR-043).

Provides:
- SSE endpoint for real-time production state updates
- Status endpoint for current production state
- Control endpoints for starting production

Terminology per ADR-043:
- assemble (not generate)
- remediation (not retry)
- stabilized (not success)
- halted (not failed)
- awaiting_operator (not paused)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.services.production_service import get_production_status
from app.domain.workflow.production_state import (
    ProductionState,
    Station,
    STATE_DISPLAY_TEXT,
    map_node_outcome_to_state,
    map_station_from_node,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/production", tags=["production"])


# In-memory event queue for SSE (will be replaced with proper pub/sub later)
# Key: project_id, Value: list of connected client queues
_event_subscribers: dict[str, list[asyncio.Queue]] = {}


async def _subscribe_to_project(project_id: str) -> asyncio.Queue:
    """Subscribe to production events for a project."""
    if project_id not in _event_subscribers:
        _event_subscribers[project_id] = []
    queue: asyncio.Queue = asyncio.Queue()
    _event_subscribers[project_id].append(queue)
    logger.info(f"SSE client subscribed to project {project_id}")
    return queue


async def _unsubscribe_from_project(project_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from production events."""
    if project_id in _event_subscribers:
        try:
            _event_subscribers[project_id].remove(queue)
            logger.info(f"SSE client unsubscribed from project {project_id}")
        except ValueError:
            pass


async def publish_event(project_id: str, event_type: str, data: dict) -> None:
    """Publish an event to all subscribers for a project.

    Called by plan_executor when state transitions occur.

    Args:
        project_id: Project to publish to
        event_type: Event type (station_transition, line_stopped, etc.)
        data: Event payload
    """
    if project_id not in _event_subscribers:
        return

    event = {"event": event_type, "data": data}

    for queue in _event_subscribers[project_id]:
        try:
            await queue.put(event)
        except Exception as e:
            logger.warning(f"Failed to publish event to subscriber: {e}")


async def _event_generator(
    request: Request,
    project_id: str,
) -> AsyncGenerator[dict, None]:
    """Generate SSE events for a project.

    Yields events as they occur, with periodic keepalives.
    """
    queue = await _subscribe_to_project(project_id)

    try:
        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat(),
            }),
        }

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for event with timeout for keepalive
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }
            except asyncio.TimeoutError:
                # Send keepalive
                yield {
                    "event": "keepalive",
                    "data": json.dumps({"timestamp": datetime.utcnow().isoformat()}),
                }

    finally:
        await _unsubscribe_from_project(project_id, queue)


@router.get("/events")
async def production_events(
    request: Request,
    project_id: str = Query(..., description="Project to subscribe to"),
) -> EventSourceResponse:
    """SSE endpoint for real-time production line updates.

    Events emitted:
    - connected: Initial connection confirmation
    - station_transition: A track moved to a new station
    - line_stopped: A track is awaiting operator input
    - production_complete: A document reached terminal state
    - interrupt_resolved: Operator resolved an interrupt
    - keepalive: Periodic heartbeat (every 30s)

    Example:
        GET /api/v1/production/events?project_id=abc-123

    Response (SSE stream):
        event: connected
        data: {"project_id": "abc-123", "timestamp": "..."}

        event: station_transition
        data: {"execution_id": "...", "document_type": "project_discovery", ...}
    """
    return EventSourceResponse(_event_generator(request, project_id))


@router.get("/status")
async def production_status(
    project_id: str = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get current production line status for a project.

    Returns:
        Current state of all document tracks in the project.
    """
    status = await get_production_status(db, project_id)
    return JSONResponse(status)


@router.post("/start")
async def start_production(
    project_id: str = Query(..., description="Project ID"),
    document_type: Optional[str] = Query(None, description="Specific document type, or all if omitted"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Start production for a project.

    If document_type is specified, starts production for that document only.
    Otherwise, runs the full line (all documents in dependency order).

    Returns:
        Production run identifier and initial status.
    """
    # TODO: Implement project orchestrator integration
    # For now, return a placeholder

    if document_type:
        logger.info(f"Starting production for {document_type} in project {project_id}")
        return JSONResponse({
            "status": "started",
            "project_id": project_id,
            "document_type": document_type,
            "message": f"Production started for {document_type}",
        })
    else:
        logger.info(f"Starting full line production for project {project_id}")
        return JSONResponse({
            "status": "started",
            "project_id": project_id,
            "mode": "full_line",
            "message": "Full line production started",
        })

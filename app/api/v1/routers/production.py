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

# Shutdown flag for graceful SSE termination
_shutdown_event: asyncio.Event | None = None


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


async def shutdown_sse_connections() -> None:
    """Signal all SSE connections to close gracefully.

    Called during application shutdown.
    """
    get_shutdown_event().set()

    # Give connections a moment to notice the shutdown
    await asyncio.sleep(0.1)

    # Clear all subscribers
    _event_subscribers.clear()
    logger.info("SSE connections shutdown complete")


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
    shutdown_event = get_shutdown_event()

    try:
        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat(),
            }),
        }

        keepalive_counter = 0
        while True:
            # Check if server is shutting down
            if shutdown_event.is_set():
                logger.debug(f"SSE shutdown signal received for project {project_id}")
                break

            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for event with short timeout to check shutdown frequently
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }
                keepalive_counter = 0
            except asyncio.TimeoutError:
                keepalive_counter += 1
                # Send keepalive every 30 seconds
                if keepalive_counter >= 30:
                    yield {
                        "event": "keepalive",
                        "data": json.dumps({"timestamp": datetime.utcnow().isoformat()}),
                    }
                    keepalive_counter = 0

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
    from app.domain.workflow.project_orchestrator import ProjectOrchestrator
    from app.domain.workflow.plan_executor import PlanExecutor
    from app.domain.workflow.pg_state_persistence import PgStatePersistence
    from app.domain.workflow.plan_registry import get_plan_registry
    from app.domain.workflow.nodes.llm_executors import create_llm_executors

    if document_type:
        # Single document production
        logger.info(f"Starting production for {document_type} in project {project_id}")

        try:
            # Get workflow plan to check required inputs
            registry = get_plan_registry()
            plan = registry.get_by_document_type(document_type)
            if not plan:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "project_id": project_id,
                        "document_type": document_type,
                        "message": f"No workflow plan found for document type: {document_type}",
                    },
                )

            # Load required input documents from project
            from sqlalchemy import select
            from app.api.models.document import Document
            from uuid import UUID

            input_documents = {}
            if plan.requires_inputs:
                try:
                    project_uuid = UUID(project_id)
                except ValueError:
                    # project_id might not be a UUID, handle gracefully
                    project_uuid = None

                for required_type in plan.requires_inputs:
                    if project_uuid:
                        result = await db.execute(
                            select(Document)
                            .where(Document.space_type == "project")
                            .where(Document.space_id == project_uuid)
                            .where(Document.doc_type_id == required_type)
                            .where(Document.is_latest == True)
                        )
                        doc = result.scalar_one_or_none()
                        if doc:
                            input_documents[required_type] = doc.content
                            logger.info(f"Loaded required input: {required_type} (doc {doc.id})")
                        else:
                            logger.warning(f"Required input document '{required_type}' not found for project {project_id}")

            # Build initial context with input documents
            initial_context = {"input_documents": input_documents}

            # Create executor
            executors = await create_llm_executors(db)
            executor = PlanExecutor(
                persistence=PgStatePersistence(db),
                plan_registry=get_plan_registry(),
                executors=executors,
                db_session=db,
            )

            # Start execution
            state = await executor.start_execution(
                project_id=project_id,
                document_type=document_type,
                initial_context=initial_context,
            )

            # Run to first pause point (gate requiring input or completion)
            state = await executor.run_to_completion_or_pause(state.execution_id)

            # Emit event for UI
            await publish_event(
                project_id,
                "track_started",
                {
                    "document_type": document_type,
                    "execution_id": state.execution_id,
                },
            )

            return JSONResponse({
                "status": "started",
                "project_id": project_id,
                "document_type": document_type,
                "execution_id": state.execution_id,
                "message": f"Production started for {document_type}",
            })

        except Exception as e:
            logger.error(f"Failed to start production for {document_type}: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "project_id": project_id,
                    "document_type": document_type,
                    "message": str(e),
                },
            )

    else:
        # Full line production using orchestrator
        logger.info(f"Starting full line production for project {project_id}")

        try:
            orchestrator = ProjectOrchestrator(db)
            state = await orchestrator.run_full_line(project_id)

            # Build track summary
            tracks_summary = [
                {
                    "document_type": dt,
                    "state": track.state.value,
                    "execution_id": track.execution_id,
                }
                for dt, track in state.tracks.items()
            ]

            return JSONResponse({
                "status": state.status.value,
                "orchestration_id": state.orchestration_id,
                "project_id": project_id,
                "mode": "full_line",
                "tracks": tracks_summary,
                "message": f"Full line production {state.status.value}",
            })

        except Exception as e:
            logger.error(f"Failed to start full line production: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "project_id": project_id,
                    "mode": "full_line",
                    "message": str(e),
                },
            )

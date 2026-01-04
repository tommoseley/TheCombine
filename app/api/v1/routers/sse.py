"""Server-Sent Events endpoint for execution progress streaming."""

import asyncio
import json
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.v1.services.llm_execution_service import (
    LLMExecutionService,
    ProgressEvent,
    LLMExecutionNotFoundError,
)


router = APIRouter(tags=["sse"])


def _format_sse(event: ProgressEvent) -> str:
    """Format a ProgressEvent as SSE message."""
    data = {
        "event_type": event.event_type,
        "execution_id": str(event.execution_id),
        "step_id": event.step_id,
        "data": event.data,
        "timestamp": event.timestamp.isoformat(),
    }
    return f"event: {event.event_type}\ndata: {json.dumps(data)}\n\n"


def _format_sse_dict(event_type: str, data: dict) -> str:
    """Format a dict as SSE message."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _event_generator(
    execution_id: UUID,
    service: LLMExecutionService,
    request: Request,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for an execution."""
    queue = service.progress_publisher.subscribe(execution_id)
    
    try:
        # Send initial connection event
        yield _format_sse_dict("connected", {
            "execution_id": str(execution_id),
            "message": "Subscribed to execution events",
        })
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            try:
                # Wait for event with timeout for keep-alive
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield _format_sse(event)
                
                # Check for terminal events
                if event.event_type in (
                    "execution_completed",
                    "execution_cancelled",
                    "execution_failed",
                ):
                    break
                    
            except asyncio.TimeoutError:
                # Send keep-alive comment
                yield ": keepalive\n\n"
                
    finally:
        service.progress_publisher.unsubscribe(execution_id, queue)


class SSERouter:
    """Router for SSE endpoints with service injection."""
    
    def __init__(self):
        self._service: LLMExecutionService = None
        self.router = APIRouter(tags=["sse"])
        self._setup_routes()
    
    def set_service(self, service: LLMExecutionService) -> None:
        """Set the execution service."""
        self._service = service
    
    def _setup_routes(self) -> None:
        """Setup router endpoints."""
        
        @self.router.get(
            "/executions/{execution_id}/stream",
            summary="Stream execution progress",
            description="Server-Sent Events stream for real-time execution updates.",
            responses={
                200: {"description": "SSE stream of execution events"},
                404: {"description": "Execution not found"},
            },
        )
        async def stream_execution(
            execution_id: str,
            request: Request,
        ):
            """Stream execution progress via SSE."""
            if self._service is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service not configured",
                )
            
            try:
                exec_uuid = UUID(execution_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid execution ID format",
                )
            
            # Verify execution exists
            try:
                await self._service.get_execution(exec_uuid)
            except LLMExecutionNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Execution not found: {execution_id}",
                )
            
            return StreamingResponse(
                _event_generator(exec_uuid, self._service, request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )


# Global router instance
sse_router = SSERouter()

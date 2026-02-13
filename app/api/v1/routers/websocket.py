"""WebSocket endpoint for real-time execution updates."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status

from app.api.v1.services.event_broadcaster import (
    EventBroadcaster,
    ExecutionEvent,
    get_broadcaster,
)
from app.api.v1.services.execution_service import (
    ExecutionService,
    ExecutionNotFoundError,
)
from app.api.v1.routers.executions import get_execution_service


router = APIRouter(tags=["websocket"])


@router.websocket("/ws/executions/{execution_id}")
async def execution_websocket(
    websocket: WebSocket,
    execution_id: str,
):
    """WebSocket endpoint for streaming execution events.
    
    Connect to receive real-time updates for a specific execution.
    Events include: step_started, step_completed, waiting_acceptance,
    waiting_clarification, completed, failed.
    """
    # Get services
    broadcaster = get_broadcaster()
    
    # Verify execution exists before accepting connection
    try:
        execution_service = get_execution_service()
        await execution_service.get_execution(execution_id)
    except ExecutionNotFoundError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Accept connection
    await websocket.accept()
    
    # Subscribe to events
    queue = await broadcaster.subscribe(execution_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "event_type": "connected",
            "execution_id": execution_id,
            "message": "Subscribed to execution events",
        })
        
        # Stream events to client
        while True:
            try:
                # Wait for event with timeout to allow checking connection
                event: ExecutionEvent = await asyncio.wait_for(
                    queue.get(),
                    timeout=30.0  # Send ping every 30s
                )
                await websocket.send_json(event.to_dict())
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"event_type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup subscription
        await broadcaster.unsubscribe(execution_id, queue)

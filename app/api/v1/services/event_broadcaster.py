"""Event broadcaster for real-time execution updates."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class ExecutionEvent:
    """Event emitted during workflow execution."""
    event_type: str
    execution_id: str
    step_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "execution_id": self.execution_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class EventBroadcaster:
    """Broadcasts execution events to connected clients.
    
    Manages WebSocket connections and distributes events
    to all clients subscribed to a specific execution.
    """
    
    def __init__(self):
        # execution_id -> set of queues for connected clients
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
    
    async def subscribe(self, execution_id: str) -> asyncio.Queue:
        """Subscribe to events for an execution.
        
        Args:
            execution_id: Execution to subscribe to
            
        Returns:
            Queue that will receive events
        """
        async with self._lock:
            if execution_id not in self._subscribers:
                self._subscribers[execution_id] = set()
            
            queue: asyncio.Queue = asyncio.Queue()
            self._subscribers[execution_id].add(queue)
            return queue
    
    async def unsubscribe(self, execution_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from execution events.
        
        Args:
            execution_id: Execution to unsubscribe from
            queue: Queue to remove
        """
        async with self._lock:
            if execution_id in self._subscribers:
                self._subscribers[execution_id].discard(queue)
                if not self._subscribers[execution_id]:
                    del self._subscribers[execution_id]
    
    async def broadcast(self, event: ExecutionEvent) -> int:
        """Broadcast event to all subscribers.
        
        Args:
            event: Event to broadcast
            
        Returns:
            Number of clients that received the event
        """
        async with self._lock:
            subscribers = self._subscribers.get(event.execution_id, set())
            count = 0
            for queue in subscribers:
                try:
                    await queue.put(event)
                    count += 1
                except Exception:
                    pass  # Queue might be closed
            return count
    
    def subscriber_count(self, execution_id: str) -> int:
        """Get number of subscribers for an execution."""
        return len(self._subscribers.get(execution_id, set()))
    
    async def emit_step_started(
        self,
        execution_id: str,
        step_id: str,
        **kwargs,
    ) -> None:
        """Emit step started event."""
        event = ExecutionEvent(
            event_type="step_started",
            execution_id=execution_id,
            step_id=step_id,
            data=kwargs,
        )
        await self.broadcast(event)
    
    async def emit_step_completed(
        self,
        execution_id: str,
        step_id: str,
        **kwargs,
    ) -> None:
        """Emit step completed event."""
        event = ExecutionEvent(
            event_type="step_completed",
            execution_id=execution_id,
            step_id=step_id,
            data=kwargs,
        )
        await self.broadcast(event)
    
    async def emit_waiting_acceptance(
        self,
        execution_id: str,
        doc_type: str,
        **kwargs,
    ) -> None:
        """Emit waiting for acceptance event."""
        event = ExecutionEvent(
            event_type="waiting_acceptance",
            execution_id=execution_id,
            data={"doc_type": doc_type, **kwargs},
        )
        await self.broadcast(event)
    
    async def emit_waiting_clarification(
        self,
        execution_id: str,
        step_id: str,
        questions: List[Dict[str, Any]],
        **kwargs,
    ) -> None:
        """Emit waiting for clarification event."""
        event = ExecutionEvent(
            event_type="waiting_clarification",
            execution_id=execution_id,
            step_id=step_id,
            data={"questions": questions, **kwargs},
        )
        await self.broadcast(event)
    
    async def emit_completed(
        self,
        execution_id: str,
        **kwargs,
    ) -> None:
        """Emit workflow completed event."""
        event = ExecutionEvent(
            event_type="completed",
            execution_id=execution_id,
            data=kwargs,
        )
        await self.broadcast(event)
    
    async def emit_failed(
        self,
        execution_id: str,
        error: str,
        **kwargs,
    ) -> None:
        """Emit workflow failed event."""
        event = ExecutionEvent(
            event_type="failed",
            execution_id=execution_id,
            data={"error": error, **kwargs},
        )
        await self.broadcast(event)


# Global broadcaster instance
_broadcaster: Optional[EventBroadcaster] = None


def get_broadcaster() -> EventBroadcaster:
    """Get the global event broadcaster."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster


def reset_broadcaster() -> None:
    """Reset the global broadcaster (for testing)."""
    global _broadcaster
    _broadcaster = None

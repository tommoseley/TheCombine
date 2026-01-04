"""Tests for SSE client integration."""

import pytest
import asyncio
from uuid import uuid4

from app.api.v1.services.llm_execution_service import (
    ProgressPublisher,
    ProgressEvent,
)
from app.api.v1.routers.sse import (
    _format_sse,
    _format_sse_dict,
)


class TestSSEClientIntegration:
    """Tests for SSE client integration with server."""
    
    def test_format_sse_includes_event_type(self):
        """SSE format includes event type line."""
        event = ProgressEvent(
            event_type="step_started",
            execution_id=uuid4(),
            step_id="discovery",
            data={},
        )
        
        result = _format_sse(event)
        
        assert "event: step_started" in result
    
    def test_format_sse_includes_data_line(self):
        """SSE format includes data line with JSON."""
        event = ProgressEvent(
            event_type="step_completed",
            execution_id=uuid4(),
            step_id="analysis",
            data={"output": "test"},
        )
        
        result = _format_sse(event)
        
        assert "data: " in result
        assert '"event_type": "step_completed"' in result
    
    def test_format_sse_ends_with_double_newline(self):
        """SSE format ends with double newline."""
        event = ProgressEvent(
            event_type="test",
            execution_id=uuid4(),
            step_id=None,
            data={},
        )
        
        result = _format_sse(event)
        
        assert result.endswith("\n\n")
    
    def test_format_sse_dict_simple(self):
        """Format simple dict as SSE."""
        result = _format_sse_dict("connected", {"message": "ok"})
        
        assert "event: connected" in result
        assert '"message": "ok"' in result


class TestProgressPublisherMultiClient:
    """Tests simulating multiple SSE clients."""
    
    @pytest.mark.asyncio
    async def test_multiple_clients_receive_events(self):
        """Multiple clients receive the same event."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        # Subscribe three clients
        q1 = publisher.subscribe(exec_id)
        q2 = publisher.subscribe(exec_id)
        q3 = publisher.subscribe(exec_id)
        
        # Publish event (await it!)
        event = ProgressEvent(
            event_type="step_started",
            execution_id=exec_id,
            step_id="test",
            data={},
        )
        await publisher.publish(event)
        
        # All clients should receive
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        e3 = await asyncio.wait_for(q3.get(), timeout=1.0)
        
        assert e1.event_type == "step_started"
        assert e2.event_type == "step_started"
        assert e3.event_type == "step_started"
    
    @pytest.mark.asyncio
    async def test_client_disconnect_doesnt_affect_others(self):
        """One client disconnecting doesn't affect others."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        q1 = publisher.subscribe(exec_id)
        q2 = publisher.subscribe(exec_id)
        
        # Client 1 disconnects
        publisher.unsubscribe(exec_id, q1)
        
        # Publish event (await it!)
        event = ProgressEvent(
            event_type="step_completed",
            execution_id=exec_id,
            step_id="test",
            data={},
        )
        await publisher.publish(event)
        
        # Client 2 still receives
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert e2.event_type == "step_completed"
        
        # Client 1 queue is empty (was unsubscribed)
        assert q1.empty()
    
    @pytest.mark.asyncio
    async def test_events_ordered_correctly(self):
        """Events arrive in order."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        queue = publisher.subscribe(exec_id)
        
        # Publish sequence (await each!)
        for i in range(5):
            event = ProgressEvent(
                event_type=f"event_{i}",
                execution_id=exec_id,
                step_id=None,
                data={"seq": i},
            )
            await publisher.publish(event)
        
        # Verify order
        for i in range(5):
            e = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert e.event_type == f"event_{i}"
            assert e.data["seq"] == i


class TestSSEEventTypes:
    """Tests for different SSE event types."""
    
    def test_step_started_event(self):
        """Step started event format."""
        event = ProgressEvent(
            event_type="step_started",
            execution_id=uuid4(),
            step_id="discovery",
            data={"role": "PM"},
        )
        
        result = _format_sse(event)
        
        assert "event: step_started" in result
        assert "discovery" in result
    
    def test_step_completed_event(self):
        """Step completed event format."""
        event = ProgressEvent(
            event_type="step_completed",
            execution_id=uuid4(),
            step_id="analysis",
            data={"output_id": "doc-123"},
        )
        
        result = _format_sse(event)
        
        assert "event: step_completed" in result
        assert "analysis" in result
    
    def test_execution_completed_event(self):
        """Execution completed event format."""
        event = ProgressEvent(
            event_type="execution_completed",
            execution_id=uuid4(),
            step_id=None,
            data={"total_cost": 0.05},
        )
        
        result = _format_sse(event)
        
        assert "event: execution_completed" in result
    
    def test_execution_failed_event(self):
        """Execution failed event format."""
        event = ProgressEvent(
            event_type="execution_failed",
            execution_id=uuid4(),
            step_id="validation",
            data={"error": "Validation failed"},
        )
        
        result = _format_sse(event)
        
        assert "event: execution_failed" in result
        assert "Validation failed" in result
    
    def test_clarification_needed_event(self):
        """Clarification needed event format."""
        event = ProgressEvent(
            event_type="clarification_needed",
            execution_id=uuid4(),
            step_id="requirements",
            data={"questions": ["What is the budget?"]},
        )
        
        result = _format_sse(event)
        
        assert "event: clarification_needed" in result
        assert "budget" in result

"""Tests for SSE streaming endpoint."""

import pytest
import asyncio
import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers.sse import SSERouter, _format_sse, _format_sse_dict
from app.api.v1.services.llm_execution_service import (
    LLMExecutionService,
    ProgressPublisher,
    ProgressEvent,
    ExecutionInfo,
    LLMExecutionNotFoundError,
)
from decimal import Decimal


class TestSSEFormatting:
    """Tests for SSE message formatting."""
    
    def test_format_sse_event(self):
        """Formats ProgressEvent as SSE."""
        event = ProgressEvent(
            event_type="step_started",
            execution_id=uuid4(),
            step_id="discovery",
            data={"role": "PM"},
        )
        
        result = _format_sse(event)
        
        assert result.startswith("event: step_started\n")
        assert "data: " in result
        assert result.endswith("\n\n")
    
    def test_format_sse_dict(self):
        """Formats dict as SSE message."""
        result = _format_sse_dict("connected", {"message": "hello"})
        
        assert "event: connected\n" in result
        assert '"message": "hello"' in result
    
    def test_format_sse_parses_as_json(self):
        """SSE data field is valid JSON."""
        event = ProgressEvent(
            event_type="test",
            execution_id=uuid4(),
            step_id="step1",
            data={"key": "value"},
        )
        
        result = _format_sse(event)
        
        # Extract data line
        lines = result.strip().split("\n")
        data_line = [line for line in lines if line.startswith("data: ")][0]
        json_str = data_line[6:]  # Remove "data: " prefix
        
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "test"
        assert parsed["step_id"] == "step1"


class TestSSERouterSetup:
    """Tests for SSE router configuration."""
    
    def test_router_creation(self):
        """Can create SSE router."""
        sse = SSERouter()
        assert sse.router is not None
    
    def test_set_service(self):
        """Can set service on router."""
        sse = SSERouter()
        service = MagicMock(spec=LLMExecutionService)
        
        sse.set_service(service)
        
        assert sse._service is service


class TestSSERouterValidation:
    """Tests for SSE endpoint validation."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service that raises not found."""
        service = MagicMock(spec=LLMExecutionService)
        service.progress_publisher = ProgressPublisher()
        service.get_execution = AsyncMock(
            side_effect=LLMExecutionNotFoundError("Not found")
        )
        return service
    
    @pytest.fixture
    def app(self, mock_service):
        """Create test app."""
        sse = SSERouter()
        sse.set_service(mock_service)
        
        app = FastAPI()
        app.include_router(sse.router, prefix="/api/v1")
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_invalid_uuid_returns_400(self, client):
        """Invalid UUID format returns 400."""
        response = client.get("/api/v1/executions/not-a-uuid/stream")
        assert response.status_code == 400
    
    def test_execution_not_found_returns_404(self, client):
        """Non-existent execution returns 404."""
        exec_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{exec_id}/stream")
        assert response.status_code == 404


class TestProgressPublisherIntegration:
    """Integration tests for progress publishing."""
    
    @pytest.mark.asyncio
    async def test_publish_and_receive(self):
        """Events published are received by subscribers."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        queue = publisher.subscribe(exec_id)
        
        event = ProgressEvent(
            event_type="step_started",
            execution_id=exec_id,
            step_id="test",
        )
        await publisher.publish(event)
        
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        
        assert received.event_type == "step_started"
        assert received.step_id == "test"
    
    @pytest.mark.asyncio
    async def test_multiple_events_in_order(self):
        """Multiple events are received in order."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        queue = publisher.subscribe(exec_id)
        
        for i in range(3):
            await publisher.publish(ProgressEvent(
                event_type=f"event_{i}",
                execution_id=exec_id,
            ))
        
        events = []
        for _ in range(3):
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            events.append(event.event_type)
        
        assert events == ["event_0", "event_1", "event_2"]
    
    @pytest.mark.asyncio
    async def test_unsubscribe_stops_events(self):
        """After unsubscribe, no more events received."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        queue = publisher.subscribe(exec_id)
        publisher.unsubscribe(exec_id, queue)
        
        await publisher.publish(ProgressEvent(
            event_type="test",
            execution_id=exec_id,
        ))
        
        assert queue.empty()
    
    @pytest.mark.asyncio
    async def test_isolated_executions(self):
        """Events only go to correct execution subscribers."""
        publisher = ProgressPublisher()
        exec_id_1 = uuid4()
        exec_id_2 = uuid4()
        
        queue_1 = publisher.subscribe(exec_id_1)
        queue_2 = publisher.subscribe(exec_id_2)
        
        await publisher.publish(ProgressEvent(
            event_type="for_exec_1",
            execution_id=exec_id_1,
        ))
        
        received = await asyncio.wait_for(queue_1.get(), timeout=1.0)
        assert received.event_type == "for_exec_1"
        assert queue_2.empty()




class TestSSEStreaming:
    """Tests for actual SSE streaming behavior."""
    
    @pytest.fixture
    def mock_service_with_events(self):
        """Create mock service that will publish events."""
        service = MagicMock(spec=LLMExecutionService)
        publisher = ProgressPublisher()
        service.progress_publisher = publisher
        
        exec_id = uuid4()
        
        async def get_exec(eid):
            return ExecutionInfo(
                execution_id=eid,
                workflow_id="test",
                scope_type="project",
                scope_id="test",
                status="running",
                current_step_id=None,
                completed_steps=[],
                step_statuses={},
                needs_clarification=False,
                clarification_questions=None,
                started_at=None,
                completed_at=None,
                error=None,
                total_cost_usd=Decimal("0"),
            )
        
        service.get_execution = AsyncMock(side_effect=get_exec)
        return service, publisher, exec_id
    
    @pytest.mark.asyncio
    async def test_stream_receives_published_events(self, mock_service_with_events):
        """SSE stream receives events published to execution."""
        service, publisher, exec_id = mock_service_with_events
        
        sse = SSERouter()
        sse.set_service(service)
        
        app = FastAPI()
        app.include_router(sse.router, prefix="/api/v1")
        
        from httpx import AsyncClient, ASGITransport
        
        events_received = []
        
        async def publish_events():
            """Publish events after short delay."""
            await asyncio.sleep(0.1)
            await publisher.publish(ProgressEvent(
                event_type="step_started",
                execution_id=exec_id,
                step_id="discovery",
            ))
            await asyncio.sleep(0.1)
            await publisher.publish(ProgressEvent(
                event_type="execution_completed",
                execution_id=exec_id,
            ))
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            pub_task = asyncio.create_task(publish_events())
            
            try:
                async with client.stream(
                    "GET",
                    f"/api/v1/executions/{exec_id}/stream",
                    timeout=5.0,
                ) as response:
                    assert response.status_code == 200
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            # Handle both formats - connected uses "message", others use "event_type"
                            event_type = data.get("event_type") or data.get("message", "unknown")
                            events_received.append(event_type)
                            if data.get("event_type") == "execution_completed":
                                break
            except asyncio.TimeoutError:
                pass
            finally:
                pub_task.cancel()
                try:
                    await pub_task
                except asyncio.CancelledError:
                    pass
        
        # Check we got events - connected message plus our published events
        assert len(events_received) >= 2
        assert "step_started" in events_received
        assert "execution_completed" in events_received

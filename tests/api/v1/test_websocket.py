"""Tests for WebSocket endpoint and event broadcasting."""

import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.api.v1.services.event_broadcaster import (
    EventBroadcaster,
    ExecutionEvent,
    get_broadcaster,
    reset_broadcaster,
)
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    WorkflowNotFoundError,
    InMemoryStatePersistence,
)


class MockWorkflowRegistry:
    """Mock registry for testing."""
    
    def __init__(self):
        self._workflows = {}
    
    def add(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow
    
    def get(self, workflow_id: str) -> Workflow:
        if workflow_id not in self._workflows:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        return self._workflows[workflow_id]
    
    def list_ids(self) -> list:
        return list(self._workflows.keys())


@pytest.fixture
def test_workflow() -> Workflow:
    """Create a test workflow."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test_workflow",
        revision="1",
        effective_date="2026-01-01",
        name="Test Workflow",
        description="A test workflow",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(name="Discovery", scope="project"),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="discovery_step",
                scope="project",
                role="PM",
                task_prompt="Discover",
                produces="discovery",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow) -> MockWorkflowRegistry:
    """Create mock registry."""
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def mock_persistence() -> InMemoryStatePersistence:
    """Create in-memory persistence."""
    return InMemoryStatePersistence()


@pytest.fixture
def app(mock_registry, mock_persistence) -> FastAPI:
    """Create test app."""
    clear_caches()
    reset_execution_service()
    reset_broadcaster()
    
    test_app = FastAPI()
    test_app.include_router(api_router)
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    reset_broadcaster()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestEventBroadcaster:
    """Tests for EventBroadcaster."""
    
    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self):
        """Subscribe returns a queue for receiving events."""
        broadcaster = EventBroadcaster()
        queue = await broadcaster.subscribe("exec_123")
        
        assert queue is not None
        assert broadcaster.subscriber_count("exec_123") == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self):
        """Unsubscribe removes the queue."""
        broadcaster = EventBroadcaster()
        queue = await broadcaster.subscribe("exec_123")
        
        await broadcaster.unsubscribe("exec_123", queue)
        
        assert broadcaster.subscriber_count("exec_123") == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_sends_to_subscribers(self):
        """Broadcast sends event to all subscribers."""
        broadcaster = EventBroadcaster()
        queue1 = await broadcaster.subscribe("exec_123")
        queue2 = await broadcaster.subscribe("exec_123")
        
        event = ExecutionEvent(
            event_type="step_started",
            execution_id="exec_123",
            step_id="step_1",
        )
        count = await broadcaster.broadcast(event)
        
        assert count == 2
        assert not queue1.empty()
        assert not queue2.empty()
    
    @pytest.mark.asyncio
    async def test_broadcast_only_to_matching_execution(self):
        """Broadcast only sends to subscribers of that execution."""
        broadcaster = EventBroadcaster()
        queue1 = await broadcaster.subscribe("exec_123")
        queue2 = await broadcaster.subscribe("exec_456")
        
        event = ExecutionEvent(
            event_type="step_started",
            execution_id="exec_123",
            step_id="step_1",
        )
        await broadcaster.broadcast(event)
        
        assert not queue1.empty()
        assert queue2.empty()
    
    @pytest.mark.asyncio
    async def test_emit_step_started(self):
        """emit_step_started creates correct event."""
        broadcaster = EventBroadcaster()
        queue = await broadcaster.subscribe("exec_123")
        
        await broadcaster.emit_step_started("exec_123", "step_1", role="PM")
        
        event = await queue.get()
        assert event.event_type == "step_started"
        assert event.step_id == "step_1"
        assert event.data["role"] == "PM"
    
    @pytest.mark.asyncio
    async def test_emit_step_completed(self):
        """emit_step_completed creates correct event."""
        broadcaster = EventBroadcaster()
        queue = await broadcaster.subscribe("exec_123")
        
        await broadcaster.emit_step_completed("exec_123", "step_1", output="result")
        
        event = await queue.get()
        assert event.event_type == "step_completed"
        assert event.data["output"] == "result"


class TestWebSocket:
    """Tests for WebSocket endpoint."""
    
    def test_websocket_connect_valid_execution(self, client: TestClient):
        """WebSocket connects for valid execution."""
        # First create an execution
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        # Connect via WebSocket
        with client.websocket_connect(f"/api/v1/ws/executions/{exec_id}") as ws:
            data = ws.receive_json()
            assert data["event_type"] == "connected"
            assert data["execution_id"] == exec_id
    
    def test_websocket_invalid_execution_closes(self, client: TestClient):
        """WebSocket closes for non-existent execution."""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws/executions/exec_nonexistent") as ws:
                ws.receive_json()


class TestMultipleClients:
    """Tests for multiple WebSocket clients."""
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Multiple clients can subscribe to same execution."""
        broadcaster = EventBroadcaster()
        
        queue1 = await broadcaster.subscribe("exec_123")
        queue2 = await broadcaster.subscribe("exec_123")
        queue3 = await broadcaster.subscribe("exec_123")
        
        assert broadcaster.subscriber_count("exec_123") == 3
        
        await broadcaster.emit_step_started("exec_123", "step_1")
        
        # All should receive
        assert not queue1.empty()
        assert not queue2.empty()
        assert not queue3.empty()

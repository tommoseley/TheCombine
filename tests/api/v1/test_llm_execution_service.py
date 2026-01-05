"""Tests for LLM Execution Service."""

import pytest
import asyncio
import json
from uuid import uuid4
from decimal import Decimal
from pathlib import Path

from app.api.v1.services.llm_execution_service import (
    LLMExecutionService,
    ProgressPublisher,
    ProgressEvent,
    ExecutionInfo,
    LLMExecutionNotFoundError,
    LLMInvalidStateError,
    WorkflowNotFoundError,
)
from app.execution import (
    LLMStepExecutor,
    WorkflowLoader,
)
from app.llm import (
    MockLLMProvider,
    PromptBuilder,
    OutputParser,
    TelemetryService,
    InMemoryTelemetryStore,
)
from app.persistence import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
)


# Sample response for mock LLM
DISCOVERY_RESPONSE = json.dumps({
    "project_name": "Test Project",
    "objectives": [{"id": "obj-1", "description": "Build MVP", "priority": "high"}],
    "stakeholders": [{"name": "Owner", "role": "Decision Maker", "influence": "high"}],
    "constraints": [{"type": "budget", "description": "Limited", "impact": "Use existing"}],
    "risks": [],
    "assumptions": ["Team ready"],
    "scope_summary": "Build MVP"
})


class TestProgressPublisher:
    """Tests for ProgressPublisher."""
    
    def test_subscribe(self):
        """Can subscribe to execution."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        queue = publisher.subscribe(exec_id)
        
        assert queue is not None
        assert publisher.subscriber_count(exec_id) == 1
    
    def test_multiple_subscribers(self):
        """Supports multiple subscribers."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        q1 = publisher.subscribe(exec_id)
        q2 = publisher.subscribe(exec_id)
        
        assert publisher.subscriber_count(exec_id) == 2
    
    def test_unsubscribe(self):
        """Can unsubscribe."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        queue = publisher.subscribe(exec_id)
        publisher.unsubscribe(exec_id, queue)
        
        assert publisher.subscriber_count(exec_id) == 0
    
    @pytest.mark.asyncio
    async def test_publish_to_subscribers(self):
        """Publishes to all subscribers."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        q1 = publisher.subscribe(exec_id)
        q2 = publisher.subscribe(exec_id)
        
        event = ProgressEvent(
            event_type="test",
            execution_id=exec_id,
        )
        await publisher.publish(event)
        
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        
        assert e1.event_type == "test"
        assert e2.event_type == "test"
    
    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self):
        """Publishing with no subscribers does not error."""
        publisher = ProgressPublisher()
        exec_id = uuid4()
        
        event = ProgressEvent(event_type="test", execution_id=exec_id)
        await publisher.publish(event)  # Should not raise


class TestLLMExecutionService:
    """Tests for LLMExecutionService."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        def response_fn(messages, system):
            return DISCOVERY_RESPONSE
        return MockLLMProvider(response_fn=response_fn)
    
    @pytest.fixture
    def telemetry_store(self):
        return InMemoryTelemetryStore()
    
    @pytest.fixture
    def executor(self, mock_provider, telemetry_store):
        return LLMStepExecutor(
            llm_provider=mock_provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            default_model="mock",
        )
    
    @pytest.fixture
    def workflow_loader(self):
        return WorkflowLoader(Path("seed/workflows"))
    
    @pytest.fixture
    def repos(self):
        return InMemoryDocumentRepository(), InMemoryExecutionRepository()
    
    @pytest.fixture
    def service(self, executor, workflow_loader, repos):
        doc_repo, exec_repo = repos
        return LLMExecutionService(
            executor=executor,
            workflow_loader=workflow_loader,
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
    
    @pytest.mark.asyncio
    async def test_start_execution(self, service):
        """Can start a new execution."""
        info = await service.start_execution(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-project",
        )
        
        assert info.execution_id is not None
        assert info.workflow_id == "strategy-document"
        assert info.scope_type == "project"
        assert info.scope_id == "test-project"
    
    @pytest.mark.asyncio
    async def test_start_execution_workflow_not_found(self, service):
        """Start with invalid workflow raises error."""
        with pytest.raises(WorkflowNotFoundError):
            await service.start_execution(
                workflow_id="nonexistent",
                scope_type="project",
                scope_id="test",
            )
    
    @pytest.mark.asyncio
    async def test_get_execution(self, service):
        """Can get execution details."""
        started = await service.start_execution(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-project",
        )
        
        info = await service.get_execution(started.execution_id)
        
        assert info.execution_id == started.execution_id
        assert info.workflow_id == "strategy-document"
    
    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, service):
        """Get non-existent execution raises error."""
        with pytest.raises(LLMExecutionNotFoundError):
            await service.get_execution(uuid4())

    
    @pytest.mark.asyncio
    async def test_execute_step(self, service):
        """Can execute a workflow step."""
        info = await service.start_execution(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-project",
        )
        
        output = await service.execute_step(info.execution_id, "discovery")
        
        assert output.success is True
        assert output.document is not None
    
    @pytest.mark.asyncio
    async def test_execute_step_publishes_events(self, service):
        """Step execution publishes progress events."""
        events = []
        
        async def collect_event():
            queue = service.progress_publisher.subscribe(info.execution_id)
            try:
                while True:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    events.append(event)
            except asyncio.TimeoutError:
                pass
        
        info = await service.start_execution(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-project",
        )
        
        # Start event collector
        collector = asyncio.create_task(collect_event())
        await asyncio.sleep(0.1)
        
        # Execute step
        await service.execute_step(info.execution_id, "discovery")
        await asyncio.sleep(0.2)
        
        collector.cancel()
        try:
            await collector
        except asyncio.CancelledError:
            pass
        
        event_types = [e.event_type for e in events]
        assert "step_started" in event_types
        assert "step_completed" in event_types
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, service, repos):
        """Can cancel a running execution."""
        doc_repo, exec_repo = repos
        
        info = await service.start_execution(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-project",
        )
        
        result = await service.cancel_execution(info.execution_id)
        
        # Verify state was updated
        state = await exec_repo.get(info.execution_id)
        assert state is not None


class TestExecutionInfo:
    """Tests for ExecutionInfo dataclass."""
    
    def test_create_execution_info(self):
        """Can create ExecutionInfo."""
        info = ExecutionInfo(
            execution_id=uuid4(),
            workflow_id="test",
            scope_type="project",
            scope_id="proj-1",
            status="pending",
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
        
        assert info.workflow_id == "test"
        assert info.status == "pending"


class TestProgressEvent:
    """Tests for ProgressEvent."""
    
    def test_create_event(self):
        """Can create ProgressEvent."""
        exec_id = uuid4()
        event = ProgressEvent(
            event_type="step_started",
            execution_id=exec_id,
            step_id="discovery",
            data={"role": "PM"},
        )
        
        assert event.event_type == "step_started"
        assert event.execution_id == exec_id
        assert event.step_id == "discovery"
        assert event.timestamp is not None

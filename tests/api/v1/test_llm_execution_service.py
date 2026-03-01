"""Tests for LLM Execution Service."""

import pytest
import asyncio
import json
from uuid import uuid4

from app.api.v1.services.llm_execution_service import (
    ProgressPublisher,
    ProgressEvent,
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
        
        publisher.subscribe(exec_id)
        publisher.subscribe(exec_id)
        
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


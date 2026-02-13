"""Tests for persistence repositories."""

import pytest
from uuid import uuid4

from app.persistence.models import (
    StoredDocument,
    StoredExecutionState,
    DocumentStatus,
    ExecutionStatus,
)
from app.persistence.repositories import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
)


class TestStoredDocument:
    """Tests for StoredDocument model."""
    
    def test_create_document(self):
        """Can create document with factory method."""
        doc = StoredDocument.create(
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            title="Test Strategy",
            content={"goals": ["goal1"]},
        )
        
        assert doc.document_id is not None
        assert doc.document_type == "strategy"
        assert doc.version == 1
        assert doc.is_latest is True
    
    def test_document_defaults(self):
        """Document has correct defaults."""
        doc = StoredDocument.create(
            document_type="test",
            scope_type="project",
            scope_id="p1",
            title="Test",
            content={},
        )
        
        assert doc.status == DocumentStatus.DRAFT
        assert doc.metadata == {}
        assert doc.created_at is not None


class TestStoredExecutionState:
    """Tests for StoredExecutionState model."""
    
    def test_create_execution(self):
        """Can create execution state."""
        state = StoredExecutionState.create(
            workflow_id="strategy-workflow",
            scope_type="project",
            scope_id="proj-123",
        )
        
        assert state.execution_id is not None
        assert state.status == ExecutionStatus.PENDING
    
    def test_start_execution(self):
        """Can start execution."""
        state = StoredExecutionState.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
        )
        
        state.start("step-1")
        
        assert state.status == ExecutionStatus.RUNNING
        assert state.current_step == "step-1"
    
    def test_complete_execution(self):
        """Can complete execution."""
        state = StoredExecutionState.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
        )
        state.start("step-1")
        
        state.complete()
        
        assert state.status == ExecutionStatus.COMPLETED
        assert state.completed_at is not None
    
    def test_fail_execution(self):
        """Can fail execution."""
        state = StoredExecutionState.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
        )
        state.start("step-1")
        
        state.fail("Something went wrong")
        
        assert state.status == ExecutionStatus.FAILED
        assert state.error_message == "Something went wrong"


class TestInMemoryDocumentRepository:
    """Tests for InMemoryDocumentRepository."""
    
    @pytest.fixture
    def repo(self):
        return InMemoryDocumentRepository()
    
    @pytest.mark.asyncio
    async def test_save_and_get(self, repo):
        """Can save and retrieve document."""
        doc = StoredDocument.create(
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            title="Test",
            content={"data": "test"},
        )
        
        saved = await repo.save(doc)
        retrieved = await repo.get(doc.document_id)
        
        assert retrieved is not None
        assert retrieved.title == "Test"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, repo):
        """Get returns None for nonexistent document."""
        result = await repo.get(uuid4())
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_scope_type_latest(self, repo):
        """Get by scope/type returns latest version."""
        # Save version 1
        doc1 = StoredDocument.create(
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            title="Version 1",
            content={},
        )
        await repo.save(doc1)
        
        # Save version 2
        doc2 = StoredDocument.create(
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            title="Version 2",
            content={},
        )
        doc2.version = 2
        await repo.save(doc2)
        
        # Get latest
        result = await repo.get_by_scope_type("project", "proj-123", "strategy")
        
        assert result is not None
        assert result.title == "Version 2"
        assert result.is_latest is True
    
    @pytest.mark.asyncio
    async def test_get_by_scope_type_specific_version(self, repo):
        """Can get specific version."""
        doc = StoredDocument.create(
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            title="Test",
            content={},
        )
        await repo.save(doc)
        
        result = await repo.get_by_scope_type(
            "project", "proj-123", "strategy", version=1
        )
        
        assert result is not None
        assert result.version == 1
    
    @pytest.mark.asyncio
    async def test_list_by_scope(self, repo):
        """Can list documents in scope."""
        for i in range(3):
            doc = StoredDocument.create(
                document_type=f"type-{i}",
                scope_type="project",
                scope_id="proj-123",
                title=f"Doc {i}",
                content={},
            )
            await repo.save(doc)
        
        results = await repo.list_by_scope("project", "proj-123")
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_list_by_scope_filtered(self, repo):
        """Can filter list by document type."""
        for doc_type in ["strategy", "backlog", "strategy"]:
            doc = StoredDocument.create(
                document_type=doc_type,
                scope_type="project",
                scope_id="proj-123",
                title=f"Doc",
                content={},
            )
            await repo.save(doc)
        
        results = await repo.list_by_scope(
            "project", "proj-123", document_type="strategy"
        )
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_delete(self, repo):
        """Can delete document."""
        doc = StoredDocument.create(
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            title="Delete Me",
            content={},
        )
        await repo.save(doc)
        
        result = await repo.delete(doc.document_id)
        
        assert result is True
        assert await repo.get(doc.document_id) is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo):
        """Delete returns False for nonexistent."""
        result = await repo.delete(uuid4())
        assert result is False


class TestInMemoryExecutionRepository:
    """Tests for InMemoryExecutionRepository."""
    
    @pytest.fixture
    def repo(self):
        return InMemoryExecutionRepository()
    
    @pytest.mark.asyncio
    async def test_save_and_get(self, repo):
        """Can save and retrieve execution."""
        state = StoredExecutionState.create(
            workflow_id="test-workflow",
            scope_type="project",
            scope_id="proj-123",
        )
        
        await repo.save(state)
        retrieved = await repo.get(state.execution_id)
        
        assert retrieved is not None
        assert retrieved.workflow_id == "test-workflow"
    
    @pytest.mark.asyncio
    async def test_list_by_scope(self, repo):
        """Can list executions in scope."""
        for i in range(3):
            state = StoredExecutionState.create(
                workflow_id=f"workflow-{i}",
                scope_type="project",
                scope_id="proj-123",
            )
            await repo.save(state)
        
        results = await repo.list_by_scope("project", "proj-123")
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_list_by_scope_filtered_by_status(self, repo):
        """Can filter by status."""
        # Create pending
        pending = StoredExecutionState.create(
            workflow_id="w1",
            scope_type="project",
            scope_id="proj-123",
        )
        await repo.save(pending)
        
        # Create running
        running = StoredExecutionState.create(
            workflow_id="w2",
            scope_type="project",
            scope_id="proj-123",
        )
        running.start("step-1")
        await repo.save(running)
        
        results = await repo.list_by_scope(
            "project", "proj-123", status=ExecutionStatus.RUNNING
        )
        
        assert len(results) == 1
        assert results[0].workflow_id == "w2"
    
    @pytest.mark.asyncio
    async def test_list_active(self, repo):
        """Can list active executions."""
        # Pending (not active)
        pending = StoredExecutionState.create(
            workflow_id="w1",
            scope_type="project",
            scope_id="p1",
        )
        await repo.save(pending)
        
        # Running (active)
        running = StoredExecutionState.create(
            workflow_id="w2",
            scope_type="project",
            scope_id="p2",
        )
        running.status = ExecutionStatus.RUNNING
        await repo.save(running)
        
        # Waiting (active)
        waiting = StoredExecutionState.create(
            workflow_id="w3",
            scope_type="project",
            scope_id="p3",
        )
        waiting.status = ExecutionStatus.WAITING_INPUT
        await repo.save(waiting)
        
        results = await repo.list_active()
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_delete(self, repo):
        """Can delete execution."""
        state = StoredExecutionState.create(
            workflow_id="test",
            scope_type="project",
            scope_id="proj-123",
        )
        await repo.save(state)
        
        result = await repo.delete(state.execution_id)
        
        assert result is True
        assert await repo.get(state.execution_id) is None

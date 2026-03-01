"""Tests for execution context."""

import pytest
from uuid import uuid4

from app.execution.context import ExecutionContext
from app.persistence import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
    ExecutionStatus,
)


class TestExecutionContext:
    """Tests for ExecutionContext."""
    
    @pytest.fixture
    def repos(self):
        return InMemoryDocumentRepository(), InMemoryExecutionRepository()
    
    @pytest.mark.asyncio
    async def test_create_context(self, repos):
        """Can create new execution context."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test-workflow",
            scope_type="project",
            scope_id="proj-123",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        assert ctx.execution_id is not None
        assert ctx.workflow_id == "test-workflow"
        assert ctx.status == ExecutionStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_load_context(self, repos):
        """Can load existing context."""
        doc_repo, exec_repo = repos
        
        # Create
        ctx = await ExecutionContext.create(
            workflow_id="test-workflow",
            scope_type="project",
            scope_id="proj-123",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        exec_id = ctx.execution_id
        
        # Load
        loaded = await ExecutionContext.load(exec_id, doc_repo, exec_repo)
        
        assert loaded is not None
        assert loaded.execution_id == exec_id
        assert loaded.workflow_id == "test-workflow"
    
    @pytest.mark.asyncio
    async def test_load_nonexistent(self, repos):
        """Load returns None for nonexistent."""
        doc_repo, exec_repo = repos
        
        result = await ExecutionContext.load(uuid4(), doc_repo, exec_repo)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_step_lifecycle(self, repos):
        """Can track step progress."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        # Start step
        ctx.start_step("step-1")
        assert ctx.step_progress["step-1"].status == "running"
        
        # Complete step
        ctx.complete_step("step-1")
        assert ctx.step_progress["step-1"].status == "completed"
    
    @pytest.mark.asyncio
    async def test_step_failure(self, repos):
        """Can track step failure."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        ctx.start_step("step-1")
        ctx.fail_step("step-1", "Something went wrong")
        
        assert ctx.step_progress["step-1"].status == "failed"
        assert ctx.step_progress["step-1"].error_message == "Something went wrong"
    
    @pytest.mark.asyncio
    async def test_wait_for_input(self, repos):
        """Can mark step waiting for input."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        ctx.start_step("step-1")
        ctx.wait_for_input("step-1")
        
        assert ctx.step_progress["step-1"].status == "waiting_input"
    
    @pytest.mark.asyncio
    async def test_save_and_get_document(self, repos):
        """Can save and retrieve documents."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        # Save
        await ctx.save_output_document(
            document_type="test-doc",
            title="Test Document",
            content={"data": "test"},
            step_id="step-1",
        )
        
        # Retrieve
        retrieved = await ctx.get_input_document("test-doc")
        
        assert retrieved is not None
        assert retrieved.content == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_save_state_persists(self, repos):
        """Save state persists to repository."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        ctx.start_step("step-1")
        ctx.complete_step("step-1")
        await ctx.save_state()
        
        # Load and verify
        loaded = await ExecutionContext.load(ctx.execution_id, doc_repo, exec_repo)
        assert loaded is not None
        assert "step-1" in loaded.step_progress

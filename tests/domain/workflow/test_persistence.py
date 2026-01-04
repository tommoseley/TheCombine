"""Tests for state persistence."""

import pytest
from pathlib import Path
import tempfile
import shutil

from app.domain.workflow.persistence import FileStatePersistence, InMemoryStatePersistence
from app.domain.workflow.workflow_state import WorkflowState, WorkflowStatus
from app.domain.workflow.context import WorkflowContext
from app.domain.workflow.models import Workflow, ScopeConfig, DocumentTypeConfig


@pytest.fixture
def workflow():
    """Create a test workflow."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test_wf",
        revision="1",
        effective_date="2026-01-01",
        name="Test",
        description="",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "doc1": DocumentTypeConfig(name="Doc1", scope="project"),
        },
        entity_types={},
        steps=[],
    )


@pytest.fixture
def temp_dir():
    """Create temporary directory for file persistence."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)


class TestFileStatePersistence:
    """Tests for FileStatePersistence."""
    
    @pytest.mark.asyncio
    async def test_save_creates_files(self, workflow, temp_dir):
        """save() creates state and context files."""
        persistence = FileStatePersistence(temp_dir)
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        context = WorkflowContext(workflow, "proj1")
        
        await persistence.save(state, context)
        
        assert (temp_dir / "wf1_proj1_state.json").exists()
        assert (temp_dir / "wf1_proj1_context.json").exists()
    
    @pytest.mark.asyncio
    async def test_load_restores_state(self, workflow, temp_dir):
        """load() restores saved state and context."""
        persistence = FileStatePersistence(temp_dir)
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.mark_step_complete("step1")
        context = WorkflowContext(workflow, "proj1")
        context.store_document("doc1", {"data": "value"})
        
        await persistence.save(state, context)
        
        loaded = await persistence.load("wf1", "proj1", workflow)
        
        assert loaded is not None
        loaded_state, loaded_context = loaded
        assert loaded_state.workflow_id == "wf1"
        assert loaded_state.status == WorkflowStatus.RUNNING
        assert "step1" in loaded_state.completed_steps
        assert loaded_context.get_document("doc1", "project") == {"data": "value"}
    
    @pytest.mark.asyncio
    async def test_load_returns_none_if_missing(self, workflow, temp_dir):
        """load() returns None if files don't exist."""
        persistence = FileStatePersistence(temp_dir)
        
        loaded = await persistence.load("missing", "proj1", workflow)
        
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_delete_removes_files(self, workflow, temp_dir):
        """delete() removes state files."""
        persistence = FileStatePersistence(temp_dir)
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        context = WorkflowContext(workflow, "proj1")
        
        await persistence.save(state, context)
        assert await persistence.exists("wf1", "proj1") is True
        
        await persistence.delete("wf1", "proj1")
        assert await persistence.exists("wf1", "proj1") is False
    
    @pytest.mark.asyncio
    async def test_exists_returns_correct_value(self, workflow, temp_dir):
        """exists() correctly checks for saved state."""
        persistence = FileStatePersistence(temp_dir)
        
        assert await persistence.exists("wf1", "proj1") is False
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        context = WorkflowContext(workflow, "proj1")
        await persistence.save(state, context)
        
        assert await persistence.exists("wf1", "proj1") is True
    
    @pytest.mark.asyncio
    async def test_roundtrip_preserves_data(self, workflow, temp_dir):
        """Full roundtrip preserves all data."""
        persistence = FileStatePersistence(temp_dir)
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.current_step_id = "current"
        state.mark_step_complete("done1")
        state.mark_step_complete("done2")
        
        context = WorkflowContext(workflow, "proj1")
        context.store_document("doc1", {"key": "value", "nested": {"a": 1}})
        
        await persistence.save(state, context)
        loaded_state, loaded_context = await persistence.load("wf1", "proj1", workflow)
        
        assert loaded_state.current_step_id == "current"
        assert loaded_state.completed_steps == ["done1", "done2"]
        assert loaded_context.get_document("doc1", "project")["nested"]["a"] == 1


class TestInMemoryStatePersistence:
    """Tests for InMemoryStatePersistence."""
    
    @pytest.mark.asyncio
    async def test_save_and_load(self, workflow):
        """In-memory persistence works correctly."""
        persistence = InMemoryStatePersistence()
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        context = WorkflowContext(workflow, "proj1")
        context.store_document("doc1", {"test": True})
        
        await persistence.save(state, context)
        loaded = await persistence.load("wf1", "proj1", workflow)
        
        assert loaded is not None
        loaded_state, loaded_context = loaded
        assert loaded_state.status == WorkflowStatus.RUNNING
        assert loaded_context.get_document("doc1", "project")["test"] is True
    
    @pytest.mark.asyncio
    async def test_delete(self, workflow):
        """delete() removes from memory."""
        persistence = InMemoryStatePersistence()
        
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        context = WorkflowContext(workflow, "proj1")
        
        await persistence.save(state, context)
        await persistence.delete("wf1", "proj1")
        
        assert await persistence.exists("wf1", "proj1") is False
        assert await persistence.load("wf1", "proj1", workflow) is None

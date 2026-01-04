"""Tests for workflow registry."""

import pytest
from pathlib import Path

from app.domain.workflow.registry import WorkflowRegistry, WorkflowNotFoundError
from app.domain.workflow.models import Workflow, ScopeConfig, WorkflowStep, DocumentTypeConfig


class TestWorkflowRegistry:
    """Tests for WorkflowRegistry."""
    
    def test_loads_from_real_directory(self):
        """Registry loads workflows from seed/workflows."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        assert registry.count() >= 1
        assert "software_product_development" in registry.list_ids()
    
    def test_get_returns_workflow(self):
        """get() returns loaded workflow."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        workflow = registry.get("software_product_development")
        
        assert isinstance(workflow, Workflow)
        assert workflow.name == "Software Product Development"
    
    def test_get_raises_for_missing(self):
        """get() raises WorkflowNotFoundError for unknown ID."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        with pytest.raises(WorkflowNotFoundError, match="not found"):
            registry.get("nonexistent_workflow")
    
    def test_get_optional_returns_none(self):
        """get_optional() returns None for unknown ID."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        result = registry.get_optional("nonexistent")
        
        assert result is None
    
    def test_list_ids_returns_all(self):
        """list_ids() returns all loaded workflow IDs."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        ids = registry.list_ids()
        
        assert isinstance(ids, list)
        assert len(ids) == registry.count()
    
    def test_list_all_returns_workflows(self):
        """list_all() returns all Workflow objects."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        workflows = registry.list_all()
        
        assert all(isinstance(w, Workflow) for w in workflows)
    
    def test_add_workflow(self):
        """add() inserts workflow into registry."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        initial_count = registry.count()
        
        test_workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="test_added",
            revision="rev_1",
            effective_date="2026-01-01",
            name="Test Added",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={},
            entity_types={},
            steps=[],
        )
        
        registry.add(test_workflow)
        
        assert registry.count() == initial_count + 1
        assert registry.get("test_added") == test_workflow
    
    def test_remove_workflow(self):
        """remove() removes workflow from registry."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        test_workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="test_remove",
            revision="rev_1",
            effective_date="2026-01-01",
            name="Test Remove",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={},
            entity_types={},
            steps=[],
        )
        registry.add(test_workflow)
        
        result = registry.remove("test_remove")
        
        assert result is True
        assert registry.get_optional("test_remove") is None
    
    def test_remove_returns_false_for_missing(self):
        """remove() returns False for unknown ID."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        
        result = registry.remove("nonexistent")
        
        assert result is False
    
    def test_handles_missing_directory(self):
        """Registry handles missing directory gracefully."""
        registry = WorkflowRegistry(Path("nonexistent/directory"))
        
        assert registry.count() == 0
        assert registry.list_ids() == []
    
    def test_reload_refreshes_from_disk(self):
        """reload() reloads all workflows from disk."""
        registry = WorkflowRegistry(Path("seed/workflows"))
        initial_count = registry.count()
        
        # Add a test workflow (not on disk)
        test_workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="test_reload",
            revision="rev_1",
            effective_date="2026-01-01",
            name="Test Reload",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={},
            entity_types={},
            steps=[],
        )
        registry.add(test_workflow)
        assert registry.count() == initial_count + 1
        
        # Reload - test workflow should be gone
        registry.reload()
        
        assert registry.count() == initial_count
        assert registry.get_optional("test_reload") is None
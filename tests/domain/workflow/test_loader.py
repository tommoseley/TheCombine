"""Tests for workflow loader."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from app.domain.workflow.loader import WorkflowLoader, WorkflowLoadError
from app.domain.workflow.models import Workflow


class TestWorkflowLoader:
    """Tests for WorkflowLoader."""
    
    @pytest.fixture
    def loader(self):
        """Create a loader instance."""
        return WorkflowLoader()
    
    @pytest.fixture
    def valid_workflow_dict(self):
        """Minimal valid workflow dict."""
        return {
            "schema_version": "workflow.v1",
            "workflow_id": "test_workflow",
            "revision": "rev_1",
            "effective_date": "2026-01-01",
            "name": "Test Workflow",
            "description": "Test",
            "scopes": {
                "project": {"parent": None}
            },
            "document_types": {
                "test_doc": {
                    "name": "Test Doc",
                    "scope": "project",
                    "may_own": []
                }
            },
            "entity_types": {},
            "steps": [
                {
                    "step_id": "test_step",
                    "role": "Technical Architect 1.0",
                    "task_prompt": "Project Discovery v1.0",
                    "produces": "test_doc",
                    "scope": "project",
                    "inputs": []
                }
            ]
        }
    
    def test_load_dict_returns_workflow(self, loader, valid_workflow_dict):
        """load_dict returns typed Workflow."""
        workflow = loader.load_dict(valid_workflow_dict)
        
        assert isinstance(workflow, Workflow)
        assert workflow.workflow_id == "test_workflow"
        assert workflow.name == "Test Workflow"
    
    def test_load_dict_parses_scopes(self, loader, valid_workflow_dict):
        """Scopes are parsed correctly."""
        workflow = loader.load_dict(valid_workflow_dict)
        
        assert "project" in workflow.scopes
        assert workflow.scopes["project"].parent is None
    
    def test_load_dict_parses_document_types(self, loader, valid_workflow_dict):
        """Document types are parsed correctly."""
        workflow = loader.load_dict(valid_workflow_dict)
        
        assert "test_doc" in workflow.document_types
        doc_type = workflow.document_types["test_doc"]
        assert doc_type.name == "Test Doc"
        assert doc_type.scope == "project"
    
    def test_load_dict_parses_steps(self, loader, valid_workflow_dict):
        """Steps are parsed correctly."""
        workflow = loader.load_dict(valid_workflow_dict)
        
        assert len(workflow.steps) == 1
        step = workflow.steps[0]
        assert step.step_id == "test_step"
        assert step.role == "Technical Architect 1.0"
        assert step.is_production
    
    def test_load_dict_parses_iteration_steps(self, loader, valid_workflow_dict):
        """Iteration steps with nested steps are parsed."""
        valid_workflow_dict["scopes"]["epic"] = {"parent": "project"}
        valid_workflow_dict["document_types"]["epic_backlog"] = {
            "name": "Epic Backlog",
            "scope": "project",
            "may_own": ["epic"],
            "collection_field": "epics"
        }
        valid_workflow_dict["document_types"]["epic_doc"] = {
            "name": "Epic Doc",
            "scope": "epic",
            "may_own": []
        }
        valid_workflow_dict["entity_types"]["epic"] = {
            "name": "Epic",
            "parent_doc_type": "epic_backlog",
            "creates_scope": "epic"
        }
        valid_workflow_dict["steps"].append({
            "step_id": "per_epic",
            "iterate_over": {
                "doc_type": "epic_backlog",
                "collection_field": "epics",
                "entity_type": "epic"
            },
            "scope": "epic",
            "steps": [
                {
                    "step_id": "epic_step",
                    "role": "Technical Architect 1.0",
                    "task_prompt": "Project Discovery v1.0",
                    "produces": "epic_doc",
                    "scope": "epic",
                    "inputs": [
                        {"entity_type": "epic", "scope": "epic", "context": True}
                    ]
                }
            ]
        })
        
        workflow = loader.load_dict(valid_workflow_dict)
        
        iter_step = workflow.steps[1]
        assert iter_step.is_iteration
        assert iter_step.iterate_over.doc_type == "epic_backlog"
        assert len(iter_step.steps) == 1
        
        nested = iter_step.steps[0]
        assert nested.step_id == "epic_step"
        assert len(nested.inputs) == 1
        assert nested.inputs[0].context is True
    
    def test_load_dict_raises_on_invalid(self, loader):
        """load_dict raises WorkflowLoadError on invalid workflow."""
        invalid = {"workflow_id": "test"}  # Missing required fields
        
        with pytest.raises(WorkflowLoadError) as exc_info:
            loader.load_dict(invalid)
        
        assert len(exc_info.value.errors) > 0
    
    def test_load_file_from_real_workflow(self, loader):
        """Load the real sample workflow file from combine-config."""
        path = Path("combine-config/workflows/software_product_development/releases/1.0.0/definition.json")
        if not path.exists():
            pytest.skip("Sample workflow not found")

        workflow = loader.load(path)

        assert workflow.workflow_id == "software_product_development"
        assert len(workflow.steps) > 0
    
    def test_load_file_not_found(self, loader):
        """load raises WorkflowLoadError for missing file."""
        with pytest.raises(WorkflowLoadError, match="not found"):
            loader.load(Path("nonexistent.json"))
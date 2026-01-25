"""Tests for workflow definition."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.execution.workflow_definition import (
    StepDefinition,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowLoader,
)


SAMPLE_WORKFLOW = {
    "workflow_id": "test-workflow",
    "name": "Test Workflow",
    "version": "1.0",
    "description": "A test workflow",
    "document_type": "test",
    "steps": [
        {
            "step_id": "step-1",
            "name": "First Step",
            "role": "PM",
            "task_prompt_id": "prompt-1",
            "inputs": [],
            "outputs": ["doc-1"],
        },
        {
            "step_id": "step-2",
            "name": "Second Step",
            "role": "BA",
            "task_prompt_id": "prompt-2",
            "inputs": ["doc-1"],
            "outputs": ["doc-2"],
            "is_final": True,
        },
    ],
    "metadata": {
        "estimated_duration_minutes": 10,
        "tags": ["test"],
    },
}


class TestStepDefinition:
    """Tests for StepDefinition."""
    
    def test_from_dict(self):
        """Can create from dictionary."""
        data = {
            "step_id": "test",
            "name": "Test Step",
            "role": "PM",
            "task_prompt_id": "prompt",
        }
        
        step = StepDefinition.from_dict(data)
        
        assert step.step_id == "test"
        assert step.role == "PM"
        assert step.allow_clarification is True  # default
    
    def test_from_dict_with_optionals(self):
        """Handles optional fields."""
        data = {
            "step_id": "test",
            "name": "Test",
            "role": "QA",
            "task_prompt_id": "prompt",
            "allow_clarification": False,
            "is_final": True,
            "model": "haiku",
        }
        
        step = StepDefinition.from_dict(data)
        
        assert step.allow_clarification is False
        assert step.is_final is True
        assert step.model == "haiku"


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition."""
    
    def test_from_dict(self):
        """Can create from dictionary."""
        workflow = WorkflowDefinition.from_dict(SAMPLE_WORKFLOW)
        
        assert workflow.workflow_id == "test-workflow"
        assert len(workflow.steps) == 2
        assert workflow.metadata.estimated_duration_minutes == 10
    
    def test_from_json(self):
        """Can create from JSON string."""
        json_str = json.dumps(SAMPLE_WORKFLOW)
        
        workflow = WorkflowDefinition.from_json(json_str)
        
        assert workflow.workflow_id == "test-workflow"
    
    def test_get_step(self):
        """Can get step by ID."""
        workflow = WorkflowDefinition.from_dict(SAMPLE_WORKFLOW)
        
        step = workflow.get_step("step-1")
        
        assert step is not None
        assert step.name == "First Step"
    
    def test_get_step_not_found(self):
        """Returns None for unknown step."""
        workflow = WorkflowDefinition.from_dict(SAMPLE_WORKFLOW)
        
        step = workflow.get_step("nonexistent")
        
        assert step is None
    
    def test_get_execution_order(self):
        """Gets correct execution order."""
        workflow = WorkflowDefinition.from_dict(SAMPLE_WORKFLOW)
        
        order = workflow.get_execution_order()
        
        assert order == ["step-1", "step-2"]
    
    def test_get_execution_order_complex(self):
        """Handles complex dependencies."""
        data = {
            "workflow_id": "complex",
            "name": "Complex",
            "version": "1.0",
            "steps": [
                {"step_id": "c", "name": "C", "role": "PM", "task_prompt_id": "p",
                 "inputs": ["doc-a", "doc-b"], "outputs": ["doc-c"], "is_final": True},
                {"step_id": "a", "name": "A", "role": "PM", "task_prompt_id": "p",
                 "inputs": [], "outputs": ["doc-a"]},
                {"step_id": "b", "name": "B", "role": "PM", "task_prompt_id": "p",
                 "inputs": [], "outputs": ["doc-b"]},
            ],
        }
        
        workflow = WorkflowDefinition.from_dict(data)
        order = workflow.get_execution_order()
        
        # a and b should come before c
        assert order.index("c") > order.index("a")
        assert order.index("c") > order.index("b")
    
    def test_validate_valid(self):
        """Validates valid workflow."""
        workflow = WorkflowDefinition.from_dict(SAMPLE_WORKFLOW)
        
        errors = workflow.validate()
        
        assert len(errors) == 0
    
    def test_validate_missing_input(self):
        """Detects missing input dependency."""
        data = {
            "workflow_id": "invalid",
            "name": "Invalid",
            "version": "1.0",
            "steps": [
                {"step_id": "s1", "name": "S1", "role": "PM", "task_prompt_id": "p",
                 "inputs": ["missing-doc"], "outputs": ["doc-1"], "is_final": True},
            ],
        }
        
        workflow = WorkflowDefinition.from_dict(data)
        errors = workflow.validate()
        
        assert any("missing-doc" in e for e in errors)
    
    def test_validate_no_final_step(self):
        """Detects missing final step."""
        data = {
            "workflow_id": "invalid",
            "name": "Invalid",
            "version": "1.0",
            "steps": [
                {"step_id": "s1", "name": "S1", "role": "PM", "task_prompt_id": "p",
                 "inputs": [], "outputs": ["doc-1"]},
            ],
        }
        
        workflow = WorkflowDefinition.from_dict(data)
        errors = workflow.validate()
        
        assert any("final" in e.lower() for e in errors)


class TestWorkflowLoader:
    """Tests for WorkflowLoader."""
    
    def test_load_from_file(self):
        """Can load workflow from file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test-workflow.json"
            with open(path, "w") as f:
                json.dump(SAMPLE_WORKFLOW, f)
            
            loader = WorkflowLoader(Path(tmpdir))
            workflow = loader.load("test-workflow")
            
            assert workflow is not None
            assert workflow.workflow_id == "test-workflow"
    
    def test_load_caches(self):
        """Caches loaded workflows."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test-workflow.json"
            with open(path, "w") as f:
                json.dump(SAMPLE_WORKFLOW, f)
            
            loader = WorkflowLoader(Path(tmpdir))
            w1 = loader.load("test-workflow")
            w2 = loader.load("test-workflow")
            
            assert w1 is w2  # Same object
    
    def test_load_not_found(self):
        """Returns None for missing workflow."""
        with TemporaryDirectory() as tmpdir:
            loader = WorkflowLoader(Path(tmpdir))
            workflow = loader.load("nonexistent")
            
            assert workflow is None
    
    def test_list_workflows(self):
        """Lists available workflows."""
        with TemporaryDirectory() as tmpdir:
            for name in ["workflow-a", "workflow-b"]:
                path = Path(tmpdir) / f"{name}.json"
                with open(path, "w") as f:
                    json.dump({**SAMPLE_WORKFLOW, "workflow_id": name}, f)
            
            loader = WorkflowLoader(Path(tmpdir))
            workflows = loader.list_workflows()
            
            assert set(workflows) == {"workflow-a", "workflow-b"}


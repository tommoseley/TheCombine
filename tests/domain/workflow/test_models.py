"""Tests for workflow models."""

import pytest

from app.domain.workflow.models import (
    DocumentTypeConfig,
    EntityTypeConfig,
    InputReference,
    IterationConfig,
    ScopeConfig,
    Workflow,
    WorkflowStep,
)


class TestWorkflowStep:
    """Tests for WorkflowStep."""
    
    def test_production_step_identification(self):
        """Production steps have role and task_prompt."""
        step = WorkflowStep(
            step_id="discovery",
            scope="project",
            role="Technical Architect 1.0",
            task_prompt="Project Discovery v1.0",
            produces="project_discovery",
        )
        
        assert step.is_production
        assert not step.is_iteration
    
    def test_iteration_step_identification(self):
        """Iteration steps have iterate_over."""
        step = WorkflowStep(
            step_id="per_epic",
            scope="epic",
            iterate_over=IterationConfig(
                doc_type="epic_backlog",
                collection_field="epics",
                entity_type="epic",
            ),
            steps=[],
        )
        
        assert step.is_iteration
        assert not step.is_production


class TestWorkflow:
    """Tests for Workflow model."""
    
    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow for testing."""
        return Workflow(
            schema_version="workflow.v1",
            workflow_id="test_workflow",
            revision="rev_1",
            effective_date="2026-01-01",
            name="Test Workflow",
            description="A test workflow",
            scopes={
                "project": ScopeConfig(parent=None),
                "epic": ScopeConfig(parent="project"),
            },
            document_types={
                "project_doc": DocumentTypeConfig(
                    name="Project Doc",
                    scope="project",
                    may_own=[],
                ),
            },
            entity_types={},
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    scope="project",
                    role="Role 1.0",
                    task_prompt="Task v1.0",
                    produces="project_doc",
                ),
                WorkflowStep(
                    step_id="iteration",
                    scope="epic",
                    iterate_over=IterationConfig(
                        doc_type="project_doc",
                        collection_field="items",
                        entity_type="epic",
                    ),
                    steps=[
                        WorkflowStep(
                            step_id="nested_step",
                            scope="epic",
                            role="Role 1.0",
                            task_prompt="Task v1.0",
                            produces="epic_doc",
                        ),
                    ],
                ),
            ],
        )
    
    def test_get_step_finds_top_level(self, sample_workflow):
        """get_step finds top-level steps."""
        step = sample_workflow.get_step("step_1")
        assert step is not None
        assert step.step_id == "step_1"
    
    def test_get_step_finds_nested(self, sample_workflow):
        """get_step finds nested steps recursively."""
        step = sample_workflow.get_step("nested_step")
        assert step is not None
        assert step.step_id == "nested_step"
    
    def test_get_step_returns_none_for_missing(self, sample_workflow):
        """get_step returns None for non-existent step."""
        step = sample_workflow.get_step("nonexistent")
        assert step is None
    
    def test_get_production_steps(self, sample_workflow):
        """get_production_steps flattens iteration."""
        steps = sample_workflow.get_production_steps()
        
        step_ids = [s.step_id for s in steps]
        assert "step_1" in step_ids
        assert "nested_step" in step_ids
        assert "iteration" not in step_ids  # Iteration step excluded


class TestInputReference:
    """Tests for InputReference."""
    
    def test_doc_type_reference(self):
        """Document type reference."""
        ref = InputReference(
            scope="project",
            doc_type="project_discovery",
        )
        
        assert ref.doc_type == "project_discovery"
        assert ref.entity_type is None
        assert ref.required is True
        assert ref.context is False
    
    def test_entity_type_reference_with_context(self):
        """Entity type reference as iteration context."""
        ref = InputReference(
            scope="epic",
            entity_type="epic",
            context=True,
        )
        
        assert ref.doc_type is None
        assert ref.entity_type == "epic"
        assert ref.context is True
"""Tests for iteration handler."""

import pytest

from app.domain.workflow.iteration import IterationHandler
from app.domain.workflow.context import WorkflowContext
from app.domain.workflow.models import (
    Workflow, WorkflowStep, ScopeConfig, DocumentTypeConfig, 
    EntityTypeConfig, IterationConfig
)


@pytest.fixture
def workflow():
    """Create a test workflow."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test",
        revision="1",
        effective_date="2026-01-01",
        name="Test",
        description="",
        scopes={
            "project": ScopeConfig(parent=None),
            "epic": ScopeConfig(parent="project"),
        },
        document_types={
            "epic_backlog": DocumentTypeConfig(name="Epic Backlog", scope="project"),
            "epic_architecture": DocumentTypeConfig(name="Architecture", scope="epic"),
        },
        entity_types={
            "epic": EntityTypeConfig(
                name="Epic",
                parent_doc_type="epic_backlog",
                creates_scope="epic",
            ),
        },
        steps=[],
    )


@pytest.fixture
def iteration_step():
    """Create an iteration step."""
    return WorkflowStep(
        step_id="epic_iteration",
        scope="epic",
        iterate_over=IterationConfig(
            doc_type="epic_backlog",
            collection_field="epics",
            entity_type="epic",
        ),
        steps=[
            WorkflowStep(
                step_id="epic_arch",
                scope="epic",
                role="Architect",
                task_prompt="Design",
                produces="epic_architecture",
                inputs=[],
            ),
        ],
    )


class TestIterationHandler:
    """Tests for IterationHandler."""
    
    def test_expand_creates_instances(self, workflow, iteration_step):
        """expand creates one instance per collection item."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {
            "epics": [
                {"id": "epic_1", "name": "Auth"},
                {"id": "epic_2", "name": "Payments"},
            ]
        })
        
        handler = IterationHandler(workflow)
        instances = handler.expand(iteration_step, ctx)
        
        assert len(instances) == 2
        assert instances[0].entity_id == "epic_1"
        assert instances[0].entity_data["name"] == "Auth"
        assert instances[1].entity_id == "epic_2"
    
    def test_expand_empty_collection(self, workflow, iteration_step):
        """expand returns empty list for empty collection."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {"epics": []})
        
        handler = IterationHandler(workflow)
        instances = handler.expand(iteration_step, ctx)
        
        assert instances == []
    
    def test_expand_missing_document(self, workflow, iteration_step):
        """expand returns empty list if source document missing."""
        ctx = WorkflowContext(workflow, "proj_1")
        # Don't store epic_backlog
        
        handler = IterationHandler(workflow)
        instances = handler.expand(iteration_step, ctx)
        
        assert instances == []
    
    def test_expand_preserves_nested_steps(self, workflow, iteration_step):
        """expand preserves steps from iteration config."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {
            "epics": [{"id": "epic_1", "name": "Auth"}]
        })
        
        handler = IterationHandler(workflow)
        instances = handler.expand(iteration_step, ctx)
        
        assert len(instances[0].steps) == 1
        assert instances[0].steps[0].step_id == "epic_arch"
    
    def test_expand_sets_scope_from_entity_type(self, workflow, iteration_step):
        """expand sets scope based on entity type's creates_scope."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {
            "epics": [{"id": "epic_1", "name": "Auth"}]
        })
        
        handler = IterationHandler(workflow)
        instances = handler.expand(iteration_step, ctx)
        
        assert instances[0].scope == "epic"
        assert instances[0].scope_id == "epic_1"
    
    def test_expand_generates_id_if_missing(self, workflow, iteration_step):
        """expand generates ID if item has no id field."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {
            "epics": [
                {"name": "Auth"},  # No id field
                {"name": "Payments"},
            ]
        })
        
        handler = IterationHandler(workflow)
        instances = handler.expand(iteration_step, ctx)
        
        assert instances[0].entity_id.startswith("epic_0_")
        assert instances[1].entity_id.startswith("epic_1_")
    
    def test_get_collection_returns_items(self, workflow):
        """get_collection extracts array from document."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {
            "epics": [{"id": "1"}, {"id": "2"}]
        })
        
        handler = IterationHandler(workflow)
        items = handler.get_collection("epic_backlog", "epics", ctx)
        
        assert len(items) == 2
    
    def test_get_collection_missing_field(self, workflow):
        """get_collection returns empty for missing field."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {"other": "data"})
        
        handler = IterationHandler(workflow)
        items = handler.get_collection("epic_backlog", "epics", ctx)
        
        assert items == []
    
    def test_count_iterations(self, workflow, iteration_step):
        """count_iterations returns correct count."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("epic_backlog", {
            "epics": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        })
        
        handler = IterationHandler(workflow)
        count = handler.count_iterations(iteration_step, ctx)
        
        assert count == 3
    
    def test_non_iteration_step_returns_empty(self, workflow):
        """expand returns empty for non-iteration step."""
        ctx = WorkflowContext(workflow, "proj_1")
        step = WorkflowStep(
            step_id="regular_step",
            scope="project",
            role="PM",
            task_prompt="Do thing",
            inputs=[],
        )
        
        handler = IterationHandler(workflow)
        instances = handler.expand(step, ctx)
        
        assert instances == []

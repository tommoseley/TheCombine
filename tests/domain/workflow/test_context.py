"""Tests for workflow context."""

import pytest

from app.domain.workflow.context import WorkflowContext, ScopeInstance
from app.domain.workflow.models import (
    Workflow, ScopeConfig, DocumentTypeConfig, EntityTypeConfig
)


@pytest.fixture
def workflow():
    """Create a test workflow with project -> epic -> story scopes."""
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
            "story": ScopeConfig(parent="epic"),
        },
        document_types={
            "project_discovery": DocumentTypeConfig(name="Discovery", scope="project"),
            "epic_backlog": DocumentTypeConfig(name="Epic Backlog", scope="project"),
            "epic_architecture": DocumentTypeConfig(name="Architecture", scope="epic"),
            "story_spec": DocumentTypeConfig(name="Story Spec", scope="story"),
        },
        entity_types={
            "epic": EntityTypeConfig(
                name="Epic",
                parent_doc_type="epic_backlog",
                creates_scope="epic",
            ),
            "story": EntityTypeConfig(
                name="Story",
                parent_doc_type="epic_architecture",
                creates_scope="story",
            ),
        },
        steps=[],
    )


class TestWorkflowContext:
    """Tests for WorkflowContext."""
    
    def test_store_and_get_root_document(self, workflow):
        """Store and retrieve document at root scope."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        ctx.store_document("project_discovery", {"goals": ["Build app"]})
        
        doc = ctx.get_document("project_discovery", "project")
        assert doc == {"goals": ["Build app"]}
    
    def test_store_and_get_scoped_document(self, workflow):
        """Store and retrieve document at non-root scope."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.push_scope("epic", "epic_1", {"name": "Auth"})
        
        ctx.store_document("epic_architecture", {"components": ["login"]})
        
        doc = ctx.get_document("epic_architecture", "epic", "epic_1")
        assert doc == {"components": ["login"]}
    
    def test_document_scope_isolation(self, workflow):
        """Documents at different scope instances are isolated."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        # Store in epic_1
        ctx.push_scope("epic", "epic_1", {"name": "Auth"})
        ctx.store_document("epic_architecture", {"for": "epic_1"})
        ctx.pop_scope()
        
        # Store in epic_2
        ctx.push_scope("epic", "epic_2", {"name": "Payments"})
        ctx.store_document("epic_architecture", {"for": "epic_2"})
        ctx.pop_scope()
        
        # Retrieve both
        doc1 = ctx.get_document("epic_architecture", "epic", "epic_1")
        doc2 = ctx.get_document("epic_architecture", "epic", "epic_2")
        
        assert doc1["for"] == "epic_1"
        assert doc2["for"] == "epic_2"
    
    def test_get_document_not_found(self, workflow):
        """Get returns None for missing document."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        doc = ctx.get_document("project_discovery", "project")
        
        assert doc is None
    
    def test_store_entity(self, workflow):
        """Store and retrieve entity."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        ctx.store_entity("epic", "epic_1", {"name": "Auth", "priority": 1})
        
        entity = ctx.get_entity("epic", "epic", "epic_1")
        assert entity == {"name": "Auth", "priority": 1}
    
    def test_push_scope_stores_entity(self, workflow):
        """push_scope automatically stores the entity."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        ctx.push_scope("epic", "epic_1", {"name": "Auth"})
        
        entity = ctx.get_entity("epic", "epic", "epic_1")
        assert entity == {"name": "Auth"}
    
    def test_scope_stack_push_pop(self, workflow):
        """Scope stack tracks nested scopes."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        assert ctx.scope_depth() == 0
        assert ctx.current_scope() is None
        
        ctx.push_scope("epic", "epic_1", {"name": "Auth"})
        assert ctx.scope_depth() == 1
        assert ctx.current_scope().scope == "epic"
        
        ctx.push_scope("story", "story_1", {"title": "Login"})
        assert ctx.scope_depth() == 2
        assert ctx.current_scope().scope == "story"
        
        popped = ctx.pop_scope()
        assert popped.scope == "story"
        assert ctx.scope_depth() == 1
    
    def test_get_scope_chain(self, workflow):
        """get_scope_chain returns all active scopes."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        ctx.push_scope("epic", "epic_1", {})
        ctx.push_scope("story", "story_1", {})
        
        chain = ctx.get_scope_chain()
        
        assert chain == {"epic": "epic_1", "story": "story_1"}
    
    def test_serialization_roundtrip(self, workflow):
        """Context survives serialization."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_document("project_discovery", {"goals": ["Build"]})
        ctx.push_scope("epic", "epic_1", {"name": "Auth"})
        ctx.store_document("epic_architecture", {"components": []})
        
        data = ctx.to_dict()
        restored = WorkflowContext.from_dict(data, workflow)
        
        assert restored.project_id == "proj_1"
        assert restored.get_document("project_discovery", "project") == {"goals": ["Build"]}
        assert restored.current_scope().scope_id == "epic_1"
    
    def test_has_document(self, workflow):
        """has_document returns correct boolean."""
        ctx = WorkflowContext(workflow, "proj_1")
        
        assert ctx.has_document("project_discovery", "project") is False
        
        ctx.store_document("project_discovery", {"data": "value"})
        
        assert ctx.has_document("project_discovery", "project") is True
    
    def test_list_entities(self, workflow):
        """list_entities returns all entity IDs."""
        ctx = WorkflowContext(workflow, "proj_1")
        ctx.store_entity("epic", "epic_1", {})
        ctx.store_entity("epic", "epic_2", {})
        ctx.store_entity("epic", "epic_3", {})
        
        ids = ctx.list_entities("epic")
        
        assert set(ids) == {"epic_1", "epic_2", "epic_3"}

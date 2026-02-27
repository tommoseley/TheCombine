"""Tests for input resolver."""

import pytest
from typing import Any, Dict, Optional

from app.domain.workflow.input_resolver import (
    InputResolver,
)
from app.domain.workflow.models import (
    DocumentTypeConfig,
    EntityTypeConfig,
    InputReference,
    ScopeConfig,
    Workflow,
    WorkflowStep,
)


class MockDocumentStore:
    """Mock document store for testing."""
    
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.entities: Dict[str, Dict[str, Any]] = {}
    
    def add_document(
        self, 
        doc_type: str, 
        scope: str, 
        scope_id: Optional[str], 
        content: Dict[str, Any]
    ):
        """Add a document to the store."""
        key = f"{doc_type}:{scope}:{scope_id or 'root'}"
        self.documents[key] = content
    
    def add_entity(
        self,
        entity_type: str,
        scope: str,
        scope_id: Optional[str],
        content: Dict[str, Any]
    ):
        """Add an entity to the store."""
        key = f"{entity_type}:{scope}:{scope_id or 'root'}"
        self.entities[key] = content
    
    def get_document(
        self,
        doc_type: str,
        scope: str,
        scope_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        key = f"{doc_type}:{scope}:{scope_id or 'root'}"
        return self.documents.get(key)
    
    def get_entity(
        self,
        entity_type: str,
        scope: str,
        scope_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        key = f"{entity_type}:{scope}:{scope_id or 'root'}"
        return self.entities.get(key)


@pytest.fixture
def simple_workflow():
    """Create a simple workflow with project -> epic scopes."""
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
            "project_doc": DocumentTypeConfig(name="Project Doc", scope="project"),
            "epic_doc": DocumentTypeConfig(name="Epic Doc", scope="epic"),
            "story_doc": DocumentTypeConfig(name="Story Doc", scope="story"),
        },
        entity_types={
            "epic": EntityTypeConfig(
                name="Epic", 
                parent_doc_type="project_doc",
                creates_scope="epic"
            ),
        },
        steps=[],
    )


@pytest.fixture
def store():
    """Create a mock document store."""
    s = MockDocumentStore()
    # Add some test documents
    s.add_document("project_doc", "project", None, {"title": "Project Discovery"})
    s.add_document("epic_doc", "epic", "epic_1", {"title": "Epic 1"})
    s.add_entity("epic", "epic", "epic_1", {"name": "First Epic"})
    return s


class TestInputResolver:
    """Tests for InputResolver."""
    
    def test_resolve_ancestor_reference(self, simple_workflow, store):
        """Ancestor reference (child -> parent) resolves."""
        resolver = InputResolver(simple_workflow, store)
        
        # Step at epic scope referencing project_doc
        step = WorkflowStep(
            step_id="epic_step",
            scope="epic",
            inputs=[
                InputReference(scope="project", doc_type="project_doc")
            ],
        )
        
        result = resolver.resolve(step, scope_id="epic_1")
        
        assert result.success
        assert result.get_value("project_doc") == {"title": "Project Discovery"}
    
    def test_resolve_same_scope_root(self, simple_workflow, store):
        """Same-scope reference at root (project) resolves."""
        resolver = InputResolver(simple_workflow, store)
        
        # Step at project scope referencing project_doc
        step = WorkflowStep(
            step_id="project_step",
            scope="project",
            inputs=[
                InputReference(scope="project", doc_type="project_doc")
            ],
        )
        
        result = resolver.resolve(step)
        
        assert result.success
        assert result.get_value("project_doc") is not None
    
    def test_resolve_same_scope_context(self, simple_workflow, store):
        """Same-scope reference with context=True resolves."""
        resolver = InputResolver(simple_workflow, store)
        
        # Step at epic scope referencing epic entity as context
        step = WorkflowStep(
            step_id="epic_step",
            scope="epic",
            inputs=[
                InputReference(scope="epic", entity_type="epic", context=True)
            ],
        )
        
        result = resolver.resolve(step, scope_id="epic_1")
        
        assert result.success
        assert result.get_value("epic") == {"name": "First Epic"}
    
    def test_reject_same_scope_non_root_no_context(self, simple_workflow, store):
        """Same-scope reference at non-root without context fails."""
        resolver = InputResolver(simple_workflow, store)
        
        # Step at epic scope referencing epic_doc (same scope, no context)
        step = WorkflowStep(
            step_id="epic_step",
            scope="epic",
            inputs=[
                InputReference(scope="epic", doc_type="epic_doc")  # No context!
            ],
        )
        
        result = resolver.resolve(step, scope_id="epic_1")
        
        assert not result.success
        assert any("forbidden" in e.lower() for e in result.errors)
    
    def test_reject_descendant_reference(self, simple_workflow, store):
        """Descendant reference (parent -> child) fails."""
        resolver = InputResolver(simple_workflow, store)
        
        # Step at project scope trying to reference epic_doc
        step = WorkflowStep(
            step_id="project_step",
            scope="project",
            inputs=[
                InputReference(scope="epic", doc_type="epic_doc")
            ],
        )
        
        result = resolver.resolve(step)
        
        assert not result.success
        assert any("descendant" in e.lower() for e in result.errors)
    
    def test_reject_cross_branch_reference(self, simple_workflow, store):
        """Cross-branch reference fails."""
        # Add a sibling branch
        simple_workflow.scopes["feature"] = ScopeConfig(parent="project")
        simple_workflow.document_types["feature_doc"] = DocumentTypeConfig(
            name="Feature Doc", scope="feature"
        )
        
        resolver = InputResolver(simple_workflow, store)
        
        # Step at epic scope trying to reference feature_doc (sibling branch)
        step = WorkflowStep(
            step_id="epic_step",
            scope="epic",
            inputs=[
                InputReference(scope="feature", doc_type="feature_doc")
            ],
        )
        
        result = resolver.resolve(step, scope_id="epic_1")
        
        assert not result.success
        assert any("cross-branch" in e.lower() for e in result.errors)
    
    def test_optional_input_not_found_ok(self, simple_workflow, store):
        """Optional input not found doesn't fail resolution."""
        resolver = InputResolver(simple_workflow, store)
        
        step = WorkflowStep(
            step_id="project_step",
            scope="project",
            inputs=[
                InputReference(
                    scope="project", 
                    doc_type="nonexistent_doc",
                    required=False  # Optional!
                )
            ],
        )
        
        result = resolver.resolve(step)
        
        assert result.success  # Still succeeds
        assert result.get_value("nonexistent_doc") is None
    
    def test_required_input_not_found_fails(self, simple_workflow, store):
        """Required input not found fails resolution."""
        resolver = InputResolver(simple_workflow, store)
        
        step = WorkflowStep(
            step_id="project_step",
            scope="project",
            inputs=[
                InputReference(
                    scope="project",
                    doc_type="nonexistent_doc",
                    required=True  # Required!
                )
            ],
        )
        
        result = resolver.resolve(step)
        
        assert not result.success
        assert any("not found" in e.lower() for e in result.errors)
    
    def test_to_dict_conversion(self, simple_workflow, store):
        """to_dict returns simple dict of resolved values."""
        resolver = InputResolver(simple_workflow, store)
        
        step = WorkflowStep(
            step_id="epic_step",
            scope="epic",
            inputs=[
                InputReference(scope="project", doc_type="project_doc"),
                InputReference(scope="epic", entity_type="epic", context=True),
            ],
        )
        
        result = resolver.resolve(step, scope_id="epic_1")
        
        d = result.to_dict()
        assert "project_doc" in d
        assert "epic" in d
        assert d["project_doc"] == {"title": "Project Discovery"}
    
    def test_resolve_with_parent_scope_ids(self, simple_workflow, store):
        """Parent scope IDs are used for ancestor lookups."""
        # Add a story-level document
        store.add_document("story_doc", "story", "story_1", {"title": "Story 1"})
        
        resolver = InputResolver(simple_workflow, store)
        
        # Step at story scope referencing epic_doc (ancestor)
        step = WorkflowStep(
            step_id="story_step",
            scope="story",
            inputs=[
                InputReference(scope="epic", doc_type="epic_doc")
            ],
        )
        
        # Provide parent scope IDs
        result = resolver.resolve(
            step, 
            scope_id="story_1",
            parent_scope_ids={"epic": "epic_1", "project": None}
        )
        
        assert result.success
        assert result.get_value("epic_doc") == {"title": "Epic 1"}
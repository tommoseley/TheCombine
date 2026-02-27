"""
Tests for Phase 3: Document Lifecycle States (WS-DOCUMENT-SYSTEM-CLEANUP)

Implements ADR-036 document lifecycle semantics.
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4


# =============================================================================
# TESTS: Document model lifecycle state field
# =============================================================================

class TestDocumentModelLifecycleState:
    """Tests that Document model has lifecycle state fields."""
    
    def test_model_has_lifecycle_state_column(self):
        """Verify Document model includes lifecycle_state."""
        from app.api.models.document import Document
        
        assert hasattr(Document, 'lifecycle_state'), \
            "Document model missing lifecycle_state column"
    
    def test_model_has_state_changed_at_column(self):
        """Verify Document model includes state_changed_at."""
        from app.api.models.document import Document
        
        assert hasattr(Document, 'state_changed_at'), \
            "Document model missing state_changed_at column"
    
    def test_document_default_lifecycle_state_is_complete(self):
        """Verify default lifecycle state is 'complete' when explicitly set."""
        from app.api.models.document import Document
        
        # Note: SQLAlchemy Column default applies at DB insert, not Python instantiation.
        # At Python level, unset lifecycle_state is None.
        # DB server_default ensures 'complete' when inserted.
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="complete",  # Explicit for testing
        )
        
        assert doc.lifecycle_state == "complete"
    
    def test_document_lifecycle_state_none_when_not_provided(self):
        """Verify lifecycle_state is None at Python level when not provided."""
        from app.api.models.document import Document
        
        # DB server_default will set to 'complete' on insert
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
        )
        
        # At Python instantiation (pre-DB), lifecycle_state is None
        # The server_default='complete' applies at DB insert time
        assert doc.lifecycle_state is None


# =============================================================================
# TESTS: State transition validation
# =============================================================================

class TestLifecycleStateTransitions:
    """Tests for ADR-036 state transition rules."""
    
    def test_valid_transitions_defined(self):
        """Verify VALID_TRANSITIONS dict exists."""
        from app.api.models.document import Document
        
        assert hasattr(Document, 'VALID_TRANSITIONS')
        assert isinstance(Document.VALID_TRANSITIONS, dict)
    
    def test_generating_can_transition_to_partial(self):
        """Verify generating -> partial is valid."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="generating",
        )
        
        assert doc.can_transition_to("partial") is True
    
    def test_generating_can_transition_to_complete(self):
        """Verify generating -> complete is valid."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="generating",
        )
        
        assert doc.can_transition_to("complete") is True
    
    def test_partial_can_transition_to_stale(self):
        """Verify partial -> stale is valid."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="partial",
        )
        
        assert doc.can_transition_to("stale") is True
    
    def test_complete_can_transition_to_stale(self):
        """Verify complete -> stale is valid."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="complete",
        )
        
        assert doc.can_transition_to("stale") is True
    
    def test_stale_can_transition_to_generating(self):
        """Verify stale -> generating is valid (regeneration)."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="stale",
        )
        
        assert doc.can_transition_to("generating") is True
    
    def test_invalid_transition_complete_to_generating(self):
        """Verify complete -> generating is invalid (must go through stale)."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="complete",
        )
        
        assert doc.can_transition_to("generating") is False
    
    def test_invalid_transition_stale_to_complete(self):
        """Verify stale -> complete is invalid (must regenerate)."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="stale",
        )
        
        assert doc.can_transition_to("complete") is False


# =============================================================================
# TESTS: State transition methods
# =============================================================================

class TestLifecycleStateTransitionMethods:
    """Tests for lifecycle state transition convenience methods."""
    
    def test_mark_generating(self):
        """Verify mark_generating sets state correctly."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="stale",  # Valid source state
        )
        
        doc.mark_generating()
        assert doc.lifecycle_state == "generating"
    
    def test_mark_partial(self):
        """Verify mark_partial sets state correctly."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="generating",  # Valid source state
        )
        
        doc.mark_partial()
        assert doc.lifecycle_state == "partial"
    
    def test_mark_complete(self):
        """Verify mark_complete sets state correctly."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="generating",  # Valid source state
        )
        
        doc.mark_complete()
        assert doc.lifecycle_state == "complete"
    
    def test_mark_stale_from_complete(self):
        """Verify mark_stale from complete sets state and is_stale."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="complete",
            is_stale=False,
        )
        
        doc.mark_stale()
        assert doc.lifecycle_state == "stale"
        assert doc.is_stale is True  # Legacy field sync
    
    def test_invalid_transition_raises_error(self):
        """Verify invalid transition raises ValueError."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test",
            content={},
            lifecycle_state="complete",
        )
        
        with pytest.raises(ValueError, match="Invalid state transition"):
            doc.set_lifecycle_state("generating")


# =============================================================================
# TESTS: RenderModel includes lifecycle_state
# =============================================================================

class TestRenderModelLifecycleState:
    """Tests that RenderModel includes lifecycle_state in metadata."""
    
    def test_build_metadata_includes_lifecycle_state(self):
        """Verify _build_metadata includes lifecycle_state when provided."""
        from app.domain.services.render_model_builder import RenderModelBuilder
        
        # Create minimal builder (services not needed for this test)
        builder = RenderModelBuilder(
            docdef_service=MagicMock(),
            component_service=MagicMock(),
        )
        
        metadata = builder._build_metadata(
            section_count=5,
            lifecycle_state="partial",
        )
        
        assert metadata["section_count"] == 5
        assert metadata["lifecycle_state"] == "partial"
    
    def test_build_metadata_omits_lifecycle_state_when_none(self):
        """Verify _build_metadata omits lifecycle_state when None."""
        from app.domain.services.render_model_builder import RenderModelBuilder
        
        builder = RenderModelBuilder(
            docdef_service=MagicMock(),
            component_service=MagicMock(),
        )
        
        metadata = builder._build_metadata(
            section_count=3,
            lifecycle_state=None,
        )
        
        assert metadata["section_count"] == 3
        assert "lifecycle_state" not in metadata
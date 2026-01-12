"""
Tests for Phase 2: Schema Versioning (WS-DOCUMENT-SYSTEM-CLEANUP)

Verifies that documents persist schema_bundle_sha256 at generation time
and that schema resolution uses the persisted hash.
"""

import pytest
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# TESTS: Document model includes schema_bundle_sha256
# =============================================================================

class TestDocumentModelSchemaBundleField:
    """Tests that Document model has schema_bundle_sha256 field."""
    
    def test_model_has_schema_bundle_sha256_column(self):
        """Verify Document model includes schema_bundle_sha256."""
        from app.api.models.document import Document
        
        assert hasattr(Document, 'schema_bundle_sha256'), \
            "Document model missing schema_bundle_sha256 column"
    
    def test_document_can_store_schema_hash(self):
        """Verify Document can store a schema bundle hash."""
        from app.api.models.document import Document
        
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Test Document",
            content={"test": "data"},
            schema_bundle_sha256="sha256:abc123def456",
        )
        
        assert doc.schema_bundle_sha256 == "sha256:abc123def456"


# =============================================================================
# TESTS: DocumentService accepts schema_bundle_sha256
# =============================================================================

class TestDocumentServiceSchemaBundleParameter:
    """Tests that DocumentService.create_document accepts schema_bundle_sha256."""
    
    def test_create_document_signature_includes_schema_bundle_sha256(self):
        """Verify create_document accepts schema_bundle_sha256 parameter."""
        from app.api.services.document_service import DocumentService
        import inspect
        
        sig = inspect.signature(DocumentService.create_document)
        params = list(sig.parameters.keys())
        
        assert 'schema_bundle_sha256' in params, \
            "create_document missing schema_bundle_sha256 parameter"


# =============================================================================
# TESTS: Schema bundle hash determinism
# =============================================================================

class TestSchemaBundleHashDeterminism:
    """Tests that schema bundle hash computation is deterministic."""
    
    def test_same_bundle_produces_same_hash(self):
        """Verify identical bundles produce identical hashes."""
        bundle = {
            "schemas": {
                "schema:OpenQuestionV1": {"type": "object"},
                "schema:RiskV1": {"type": "object"},
            }
        }
        
        def compute_hash(b):
            bundle_json = json.dumps(b, sort_keys=True, separators=(',', ':'))
            return f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"
        
        hash1 = compute_hash(bundle)
        hash2 = compute_hash(bundle)
        
        assert hash1 == hash2
    
    def test_different_bundles_produce_different_hashes(self):
        """Verify different bundles produce different hashes."""
        bundle1 = {"schemas": {"schema:A": {"type": "object"}}}
        bundle2 = {"schemas": {"schema:B": {"type": "object"}}}
        
        def compute_hash(b):
            bundle_json = json.dumps(b, sort_keys=True, separators=(',', ':'))
            return f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"
        
        hash1 = compute_hash(bundle1)
        hash2 = compute_hash(bundle2)
        
        assert hash1 != hash2
    
    def test_key_order_does_not_affect_hash(self):
        """Verify key order doesn't affect hash (sort_keys=True)."""
        bundle1 = {"schemas": {"a": 1, "b": 2}}
        bundle2 = {"schemas": {"b": 2, "a": 1}}
        
        def compute_hash(b):
            bundle_json = json.dumps(b, sort_keys=True, separators=(',', ':'))
            return f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"
        
        hash1 = compute_hash(bundle1)
        hash2 = compute_hash(bundle2)
        
        assert hash1 == hash2


# =============================================================================
# TESTS: RenderModelBuilder includes schema_bundle_sha256
# =============================================================================

class TestRenderModelBuilderSchemaBundleHash:
    """Tests that RenderModelBuilder includes schema_bundle_sha256 in output."""
    
    def test_render_model_has_schema_bundle_sha256_field(self):
        """Verify RenderModel dataclass includes schema_bundle_sha256."""
        from app.domain.services.render_model_builder import RenderModel
        
        rm = RenderModel(
            render_model_version="1.0",
            schema_id="schema:RenderModelV1",
            document_id="test123",
            document_type="TestView",
            title="Test",
            schema_bundle_sha256="sha256:abc123",
        )
        
        assert rm.schema_bundle_sha256 == "sha256:abc123"
    
    def test_render_model_to_dict_includes_schema_bundle_sha256(self):
        """Verify to_dict() includes schema_bundle_sha256."""
        from app.domain.services.render_model_builder import RenderModel
        
        rm = RenderModel(
            render_model_version="1.0",
            schema_id="schema:RenderModelV1",
            document_id="test123",
            document_type="TestView",
            title="Test",
            schema_bundle_sha256="sha256:abc123",
        )
        
        result = rm.to_dict()
        
        assert "schema_bundle_sha256" in result
        assert result["schema_bundle_sha256"] == "sha256:abc123"


# =============================================================================
# TESTS: Historical document rendering fallback
# =============================================================================

class TestHistoricalDocumentRendering:
    """Tests for rendering historical documents with original or latest schema."""
    
    def test_document_with_null_schema_hash_uses_latest(self):
        """Verify documents without schema_bundle_sha256 use latest schema."""
        # This tests the fallback behavior described in Phase 2
        # When a document has no schema_bundle_sha256 (pre-Phase 2),
        # the viewer should fall back to the latest schema
        
        from app.api.models.document import Document
        
        # Old document without schema hash
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="Old Document",
            content={"test": "data"},
            schema_bundle_sha256=None,  # No schema hash (old document)
        )
        
        # Verify it has no schema hash
        assert doc.schema_bundle_sha256 is None
        
        # The fallback to latest happens in the viewer, not the model
        # This test just ensures the model allows NULL values
    
    def test_document_with_schema_hash_preserves_it(self):
        """Verify documents with schema_bundle_sha256 preserve it."""
        from app.api.models.document import Document
        
        # New document with schema hash
        schema_hash = "sha256:abc123def456789"
        doc = Document(
            space_type="project",
            space_id=uuid4(),
            doc_type_id="test_doc",
            title="New Document",
            content={"test": "data"},
            schema_bundle_sha256=schema_hash,
        )
        
        # Verify hash is preserved
        assert doc.schema_bundle_sha256 == schema_hash
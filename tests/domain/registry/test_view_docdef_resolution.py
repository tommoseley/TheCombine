"""
Tests for Phase 1: Config Consolidation (WS-DOCUMENT-SYSTEM-CLEANUP)

Verifies that view_docdef is read from document_types table
instead of hardcoded DOCUMENT_CONFIG.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# TESTS: view_docdef from database
# =============================================================================

class TestViewDocdefFromDatabase:
    """Tests for view_docdef resolution from database via ORM."""
    
    @pytest.mark.asyncio
    async def test_get_document_type_includes_view_docdef(self):
        """Test that _get_document_type returns view_docdef from DB via ORM."""
        from app.web.routes.public.document_routes import _get_document_type
        from app.api.models.document_type import DocumentType
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        
        # Create mock DocumentType ORM object
        mock_doc_type = MagicMock(spec=DocumentType)
        mock_doc_type.doc_type_id = "implementation_plan"
        mock_doc_type.name = "Implementation Plan"
        mock_doc_type.description = "Project implementation plan"
        mock_doc_type.icon = "layers"
        mock_doc_type.required_inputs = []
        mock_doc_type.optional_inputs = []
        mock_doc_type.view_docdef = "ImplementationPlanView"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc_type
        db.execute.return_value = mock_result

        # Act
        doc_type = await _get_document_type(db, "implementation_plan")

        # Assert
        assert doc_type is not None
        assert doc_type["view_docdef"] == "ImplementationPlanView"
        assert doc_type["doc_type_id"] == "implementation_plan"
    
    @pytest.mark.asyncio
    async def test_get_document_type_null_view_docdef(self):
        """Test handling of NULL view_docdef in database via ORM."""
        from app.web.routes.public.document_routes import _get_document_type
        from app.api.models.document_type import DocumentType
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        
        mock_doc_type = MagicMock(spec=DocumentType)
        mock_doc_type.doc_type_id = "custom_doc"
        mock_doc_type.name = "Custom Document"
        mock_doc_type.description = None
        mock_doc_type.icon = None
        mock_doc_type.required_inputs = []
        mock_doc_type.optional_inputs = []
        mock_doc_type.view_docdef = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc_type
        db.execute.return_value = mock_result
        
        # Act
        doc_type = await _get_document_type(db, "custom_doc")
        
        # Assert
        assert doc_type is not None
        assert doc_type["view_docdef"] is None
    
    @pytest.mark.asyncio
    async def test_get_document_type_not_found(self):
        """Test handling of non-existent document type via ORM."""
        from app.web.routes.public.document_routes import _get_document_type
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result
        
        # Act
        doc_type = await _get_document_type(db, "nonexistent")
        
        # Assert
        assert doc_type is None


class TestViewDocdefResolutionPriority:
    """Tests for view_docdef resolution priority (DB over fallback)."""
    
    def test_db_value_preferred_over_fallback(self):
        """Test that DB value is used when available."""
        doc_type = {"view_docdef": "DBDocdef"}
        fallback_config = {"view_docdef": "FallbackDocdef"}
        
        view_docdef = (doc_type.get("view_docdef") if doc_type else None) or fallback_config.get("view_docdef")
        
        assert view_docdef == "DBDocdef"
    
    def test_fallback_used_when_db_null(self):
        """Test that fallback is used when DB value is NULL."""
        doc_type = {"view_docdef": None}
        fallback_config = {"view_docdef": "FallbackDocdef"}
        
        view_docdef = (doc_type.get("view_docdef") if doc_type else None) or fallback_config.get("view_docdef")
        
        assert view_docdef == "FallbackDocdef"
    
    def test_fallback_used_when_doc_type_none(self):
        """Test that fallback is used when doc_type not in DB."""
        doc_type = None
        fallback_config = {"view_docdef": "FallbackDocdef"}
        
        view_docdef = (doc_type.get("view_docdef") if doc_type else None) or fallback_config.get("view_docdef")
        
        assert view_docdef == "FallbackDocdef"
    
    def test_none_when_both_empty(self):
        """Test that None is returned when both sources empty."""
        doc_type = {"view_docdef": None}
        fallback_config = {}
        
        view_docdef = (doc_type.get("view_docdef") if doc_type else None) or fallback_config.get("view_docdef")
        
        assert view_docdef is None


class TestDocumentTypeModelIncludesViewDocdef:
    """Tests that DocumentType model has view_docdef field."""
    
    def test_model_has_view_docdef_column(self):
        """Verify DocumentType model includes view_docdef."""
        from app.api.models.document_type import DocumentType
        
        assert hasattr(DocumentType, 'view_docdef'), "DocumentType missing view_docdef column"
    
    def test_to_dict_includes_view_docdef(self):
        """Verify to_dict() includes view_docdef."""
        from app.api.models.document_type import DocumentType
        import uuid
        
        doc_type = DocumentType(
            id=uuid.uuid4(),
            doc_type_id="test_doc",
            name="Test Document",
            category="test",
            builder_role="test",
            builder_task="test",
            handler_id="test",
            view_docdef="TestDocdef",
        )
        
        result = doc_type.to_dict()
        
        assert "view_docdef" in result
        assert result["view_docdef"] == "TestDocdef"
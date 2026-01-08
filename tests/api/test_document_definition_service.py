"""
Tests for DocumentDefinitionService.

Per WS-ADR-034-POC Phase 8.1: Service unit tests for document definition service.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.services.document_definition_service import (
    DocumentDefinitionService,
    InvalidDocDefIdError,
    DocDefNotFoundError,
    DocDefAlreadyAcceptedError,
    DOCDEF_ID_PATTERN,
)
from app.api.models.document_definition import DocumentDefinition


class TestDocDefIdValidation:
    """Tests for document_def_id format validation."""
    
    def test_valid_docdef_id_patterns(self):
        """Valid document definition IDs should match the pattern."""
        valid_ids = [
            "docdef:EpicBacklog:1.0.0",
            "docdef:ProjectDiscovery:2.1.3",
            "docdef:My_Document:0.0.1",
            "docdef:Test-Doc:10.20.30",
            "docdef:some.doc:1.0.0",
        ]
        for docdef_id in valid_ids:
            assert DOCDEF_ID_PATTERN.match(docdef_id), f"Should match: {docdef_id}"
    
    def test_invalid_docdef_id_patterns(self):
        """Invalid document definition IDs should not match the pattern."""
        invalid_ids = [
            "EpicBacklog:1.0.0",  # missing prefix
            "docdef:EpicBacklog",  # missing version
            "docdef::1.0.0",  # empty name
            "docdef:EpicBacklog:1.0",  # incomplete version
            "docdef:Epic Backlog:1.0.0",  # space in name
        ]
        for docdef_id in invalid_ids:
            assert not DOCDEF_ID_PATTERN.match(docdef_id), f"Should not match: {docdef_id}"


class TestDocumentDefinitionService:
    """Tests for DocumentDefinitionService methods."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        # db.add() is not async - make it a regular mock
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock db."""
        return DocumentDefinitionService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_document_definition(self, service, mock_db):
        """Test creating a new document definition."""
        # Create definition
        docdef = await service.create(
            document_def_id="docdef:TestDoc:1.0.0",
            prompt_header={"role": "Test role", "constraints": []},
            sections=[],
            created_by="test",
        )
        
        # Verify db.add was called
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_with_null_document_schema_id(self, service, mock_db):
        """Test creating definition without document_schema_id (MVP case)."""
        # Create without document_schema_id
        await service.create(
            document_def_id="docdef:TestDoc:1.0.0",
            prompt_header={"role": "Test"},
            sections=[],
            document_schema_id=None,  # Explicitly null for MVP
        )
        
        # Should succeed - document_schema_id is nullable
        mock_db.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_docdef_by_exact_id(self, service, mock_db):
        """Test getting a document definition by exact ID."""
        expected = DocumentDefinition(
            id=uuid4(),
            document_def_id="docdef:EpicBacklog:1.0.0",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_db.execute.return_value = mock_result
        
        result = await service.get("docdef:EpicBacklog:1.0.0")
        
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_get_accepted_returns_latest_by_accepted_at(self, service, mock_db):
        """Test that get_accepted orders by accepted_at DESC (D7)."""
        expected = DocumentDefinition(
            id=uuid4(),
            document_def_id="docdef:EpicBacklog:1.0.0",
            status="accepted",
            accepted_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_db.execute.return_value = mock_result
        
        result = await service.get_accepted("docdef:EpicBacklog:")
        
        assert result == expected
        assert result.status == "accepted"
    
    @pytest.mark.asyncio
    async def test_accept_transitions_status(self, service, mock_db):
        """Test that accept() transitions status from draft to accepted."""
        docdef = DocumentDefinition(
            id=uuid4(),
            document_def_id="docdef:TestDoc:1.0.0",
            status="draft",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = docdef
        mock_db.execute.return_value = mock_result
        
        result = await service.accept("docdef:TestDoc:1.0.0")
        
        assert result.status == "accepted"
        assert result.accepted_at is not None
    
    @pytest.mark.asyncio
    async def test_list_all_docdefs(self, service, mock_db):
        """Test listing all document definitions."""
        docdefs = [
            DocumentDefinition(document_def_id="docdef:Doc1:1.0.0"),
            DocumentDefinition(document_def_id="docdef:Doc2:1.0.0"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = docdefs
        mock_db.execute.return_value = mock_result
        
        result = await service.list_all()
        
        assert len(result) == 2


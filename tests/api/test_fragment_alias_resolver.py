"""
Tests for FragmentRegistryService alias resolver.

Per WS-ADR-034-POC Phase 8.1: Tests for fragment alias resolution (D3).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.services.fragment_registry_service import (
    FragmentRegistryService,
    FRAGMENT_ALIASES,
)
from app.api.models.fragment_artifact import FragmentArtifact


class TestFragmentAliasResolver:
    """Tests for fragment alias resolution per ADR-034 D3."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock db."""
        return FragmentRegistryService(mock_db)
    
    def test_fragment_aliases_contains_open_question_mapping(self):
        """Verify FRAGMENT_ALIASES contains the OpenQuestion mapping."""
        assert "fragment:OpenQuestionV1:web:1.0.0" in FRAGMENT_ALIASES
        assert FRAGMENT_ALIASES["fragment:OpenQuestionV1:web:1.0.0"] == "OpenQuestionV1Fragment"
    
    @pytest.mark.asyncio
    async def test_resolve_canonical_id_via_alias(self, service, mock_db):
        """Test resolving a canonical fragment ID through alias mapping."""
        expected_fragment = FragmentArtifact(
            id=uuid4(),
            fragment_id="OpenQuestionV1Fragment",
            schema_type_id="OpenQuestionV1",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_fragment
        mock_db.execute.return_value = mock_result
        
        # Resolve canonical ID - should look up by legacy ID
        result = await service.resolve_fragment_id("fragment:OpenQuestionV1:web:1.0.0")
        
        assert result == expected_fragment
    
    @pytest.mark.asyncio
    async def test_resolve_legacy_id_directly(self, service, mock_db):
        """Test resolving a legacy fragment ID directly (no alias)."""
        expected_fragment = FragmentArtifact(
            id=uuid4(),
            fragment_id="SomeLegacyFragment",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_fragment
        mock_db.execute.return_value = mock_result
        
        # Legacy ID not in aliases - should look up directly
        result = await service.resolve_fragment_id("SomeLegacyFragment")
        
        assert result == expected_fragment
    
    @pytest.mark.asyncio
    async def test_resolve_unknown_returns_none(self, service, mock_db):
        """Test resolving an unknown fragment ID returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.resolve_fragment_id("fragment:Unknown:web:1.0.0")
        
        assert result is None

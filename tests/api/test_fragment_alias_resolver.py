"""
Tests for FragmentRegistryService canonical ID resolution.

Per WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS: Aliases removed.
Fragment IDs are now stored and looked up canonically.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.services.fragment_registry_service import FragmentRegistryService
from app.api.models.fragment_artifact import FragmentArtifact


class TestFragmentCanonicalResolver:
    """Tests for fragment canonical ID resolution."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock db."""
        return FragmentRegistryService(mock_db)
    
    @pytest.mark.asyncio
    async def test_resolve_canonical_id_directly(self, service, mock_db):
        """Test resolving a canonical fragment ID directly (no alias translation)."""
        canonical_id = "fragment:OpenQuestionV1:web:1.0.0"
        expected_fragment = FragmentArtifact(
            id=uuid4(),
            fragment_id=canonical_id,
            schema_type_id="OpenQuestionV1",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_fragment
        mock_db.execute.return_value = mock_result
        
        result = await service.resolve_fragment_id(canonical_id)
        
        assert result == expected_fragment
        assert result.fragment_id == canonical_id
    
    @pytest.mark.asyncio
    async def test_resolve_unknown_returns_none(self, service, mock_db):
        """Test resolving an unknown fragment ID returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.resolve_fragment_id("fragment:Unknown:web:1.0.0")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_all_component_fragment_ids_use_canonical_format(self, service, mock_db):
        """INVARIANT: All component fragment IDs follow canonical format."""
        from seed.registry.component_artifacts import INITIAL_COMPONENT_ARTIFACTS
        
        for component in INITIAL_COMPONENT_ARTIFACTS:
            bindings = component.get("view_bindings", {})
            web_binding = bindings.get("web", {})
            fragment_id = web_binding.get("fragment_id")
            
            if fragment_id:
                # Must be canonical format: fragment:XxxV1:web:1.0.0
                assert fragment_id.startswith("fragment:"), f"{component['component_id']}: {fragment_id}"
                assert ":web:" in fragment_id, f"{component['component_id']}: {fragment_id}"

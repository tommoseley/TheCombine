"""
Tests for Phase 4: Staleness Propagation (WS-DOCUMENT-SYSTEM-CLEANUP)

Tests the StalenessService and DOCUMENT_TYPE_DEPENDENCIES graph.
"""

import pytest
from unittest.mock import MagicMock


# =============================================================================
# TESTS: Dependency graph
# =============================================================================

class TestDocumentTypeDependencies:
    """Tests for DOCUMENT_TYPE_DEPENDENCIES configuration."""
    
    def test_dependency_graph_exists(self):
        """Verify DOCUMENT_TYPE_DEPENDENCIES dict exists."""
        from app.domain.services.staleness_service import DOCUMENT_TYPE_DEPENDENCIES
        
        assert isinstance(DOCUMENT_TYPE_DEPENDENCIES, dict)
    
    def test_project_discovery_has_dependents(self):
        """Verify project_discovery has downstream dependents."""
        from app.domain.services.staleness_service import DOCUMENT_TYPE_DEPENDENCIES
        
        assert "project_discovery" in DOCUMENT_TYPE_DEPENDENCIES
        assert len(DOCUMENT_TYPE_DEPENDENCIES["project_discovery"]) > 0
    
    def test_technical_architecture_depends_on_project_discovery(self):
        """Verify technical_architecture is a dependent of project_discovery."""
        from app.domain.services.staleness_service import DOCUMENT_TYPE_DEPENDENCIES

        assert "technical_architecture" in DOCUMENT_TYPE_DEPENDENCIES["project_discovery"]


# =============================================================================
# TESTS: get_downstream_types helper
# =============================================================================

class TestGetDownstreamTypes:
    """Tests for get_downstream_types function."""
    
    def test_returns_dependents_for_known_type(self):
        """Verify returns list of dependents for known type."""
        from app.domain.services.staleness_service import get_downstream_types
        
        result = get_downstream_types("project_discovery")
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_returns_empty_list_for_unknown_type(self):
        """Verify returns empty list for unknown type."""
        from app.domain.services.staleness_service import get_downstream_types
        
        result = get_downstream_types("nonexistent_type")
        
        assert result == []
    
    def test_leaf_type_has_no_dependents(self):
        """Verify leaf node type has no dependents."""
        from app.domain.services.staleness_service import get_downstream_types

        result = get_downstream_types("technical_architecture")

        assert result == []


# =============================================================================
# TESTS: StalenessService class
# =============================================================================

class TestStalenessServiceInit:
    """Tests for StalenessService initialization."""
    
    def test_service_can_be_instantiated(self):
        """Verify StalenessService can be created with db session."""
        from app.domain.services.staleness_service import StalenessService
        
        mock_db = MagicMock()
        service = StalenessService(mock_db)
        
        assert service.db == mock_db


class TestStalenessServiceGetUpstreamDependencies:
    """Tests for get_upstream_dependencies method."""
    
    @pytest.mark.asyncio
    async def test_technical_architecture_depends_on_project_discovery(self):
        """Verify technical_architecture upstream includes project_discovery."""
        from app.domain.services.staleness_service import StalenessService

        mock_db = MagicMock()
        service = StalenessService(mock_db)

        result = await service.get_upstream_dependencies("technical_architecture")

        assert "project_discovery" in result
    
    @pytest.mark.asyncio
    async def test_project_discovery_has_no_upstream(self):
        """Verify project_discovery (root) has no upstream dependencies."""
        from app.domain.services.staleness_service import StalenessService
        
        mock_db = MagicMock()
        service = StalenessService(mock_db)
        
        result = await service.get_upstream_dependencies("project_discovery")
        
        assert result == []
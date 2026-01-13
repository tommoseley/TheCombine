"""
Tests for Phase 7: Command Route Normalization (WS-DOCUMENT-SYSTEM-CLEANUP)

Tests canonical command routes and deprecation of old routes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# TESTS: Canonical command routes exist
# =============================================================================

class TestCanonicalCommandRoutesExist:
    """Tests that canonical command routes are defined."""
    
    def test_build_command_route_exists(self):
        """Verify POST /api/commands/documents/{doc_type_id}/build route exists."""
        from app.api.routers.commands import router
        
        routes = [r.path for r in router.routes]
        # Router has prefix /api/commands, so full path is included
        assert "/api/commands/documents/{doc_type_id}/build" in routes
    
    def test_mark_stale_command_route_exists(self):
        """Verify POST /api/commands/documents/{doc_type_id}/mark-stale route exists."""
        from app.api.routers.commands import router
        
        routes = [r.path for r in router.routes]
        # Router has prefix /api/commands, so full path is included
        assert "/api/commands/documents/{doc_type_id}/mark-stale" in routes


# =============================================================================
# TESTS: Command response models
# =============================================================================

class TestCommandResponseModels:
    """Tests for command response models."""
    
    def test_document_build_response_has_task_id(self):
        """Verify DocumentBuildResponse includes task_id."""
        from app.api.routers.commands import DocumentBuildResponse
        
        response = DocumentBuildResponse(
            status="completed",
            task_id="abc-123",
            doc_type_id="project_discovery",
            document_id="doc-456",
        )
        
        assert response.task_id == "abc-123"
        assert response.status == "completed"
    
    def test_mark_stale_response_has_task_id(self):
        """Verify MarkStaleResponse includes task_id."""
        from app.api.routers.commands import MarkStaleResponse
        
        response = MarkStaleResponse(
            status="marked",
            task_id="abc-123",
            doc_type_id="epic_backlog",
            document_id="doc-456",
            downstream_marked=2,
        )
        
        assert response.task_id == "abc-123"
        assert response.downstream_marked == 2


# =============================================================================
# TESTS: Old routes are deprecated
# =============================================================================

class TestOldRoutesDeprecated:
    """Tests that old routes are marked as deprecated."""
    
    def test_old_build_route_is_deprecated(self):
        """Verify POST /api/documents/build/{doc_type_id} is deprecated."""
        from app.api.routers.documents import router
        
        # Router has prefix /api/documents, so check for full path
        for route in router.routes:
            if hasattr(route, 'methods') and "POST" in route.methods:
                if "build" in route.path and "doc_type_id" in route.path:
                    assert route.deprecated is True, f"Route {route.path} should be deprecated"
                    return
        pytest.fail("Build route not found")
    
    def test_old_mark_stale_route_is_deprecated(self):
        """Verify POST /api/documents/{document_id}/mark-stale is deprecated."""
        from app.api.routers.documents import router
        
        # Router has prefix /api/documents, so check for full path
        for route in router.routes:
            if hasattr(route, 'methods') and "POST" in route.methods:
                if "mark-stale" in route.path:
                    assert route.deprecated is True, f"Route {route.path} should be deprecated"
                    return
        pytest.fail("Mark-stale route not found")


# =============================================================================
# TESTS: Deprecation registry updated
# =============================================================================

class TestDeprecationRegistryUpdated:
    """Tests that DEPRECATED_ROUTES includes API routes."""
    
    def test_api_build_route_in_deprecated_registry(self):
        """Verify /api/documents/build/ is in DEPRECATED_ROUTES."""
        from app.core.middleware.deprecation import DEPRECATED_ROUTES
        
        assert "/api/documents/build/" in DEPRECATED_ROUTES
    
    def test_deprecated_route_has_redirect_info(self):
        """Verify deprecated route has redirect_to and message."""
        from app.core.middleware.deprecation import DEPRECATED_ROUTES
        
        info = DEPRECATED_ROUTES["/api/documents/build/"]
        assert "redirect_to" in info
        assert "message" in info
        assert "commands" in info["redirect_to"]


# =============================================================================
# TESTS: Request/Response model fields
# =============================================================================

class TestRequestResponseModels:
    """Tests for request model fields."""
    
    def test_document_build_request_has_project_id(self):
        """Verify DocumentBuildRequest has project_id field."""
        from app.api.routers.commands import DocumentBuildRequest
        
        req = DocumentBuildRequest(project_id="proj-123")
        assert req.project_id == "proj-123"
    
    def test_mark_stale_request_has_project_id(self):
        """Verify MarkStaleRequest has project_id field."""
        from app.api.routers.commands import MarkStaleRequest
        
        req = MarkStaleRequest(project_id="proj-123")
        assert req.project_id == "proj-123"
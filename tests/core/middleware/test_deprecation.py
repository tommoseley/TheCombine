"""
Tests for Phase 5: Route Deprecation with Warning Headers (WS-DOCUMENT-SYSTEM-CLEANUP)

Tests deprecation middleware, warning headers, and redirect helpers.
"""

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.routing import Route


# =============================================================================
# TESTS: Deprecation info lookup
# =============================================================================

class TestDeprecationInfoLookup:
    """Tests for get_deprecation_info function."""
    
    def test_exact_match_returns_info(self):
        """Verify exact path match returns deprecation info."""
        from app.core.middleware.deprecation import get_deprecation_info

        info = get_deprecation_info("/view/ArchitecturalSummaryView")

        assert info is not None
        assert "redirect_to" in info
        assert "message" in info
    
    def test_unknown_path_returns_none(self):
        """Verify unknown path returns None."""
        from app.core.middleware.deprecation import get_deprecation_info
        
        info = get_deprecation_info("/api/health")
        
        assert info is None
    
    def test_deprecated_routes_registry_exists(self):
        """Verify DEPRECATED_ROUTES dict exists and is populated."""
        from app.core.middleware.deprecation import DEPRECATED_ROUTES
        
        assert isinstance(DEPRECATED_ROUTES, dict)
        assert len(DEPRECATED_ROUTES) > 0


# =============================================================================
# TESTS: Warning header helpers
# =============================================================================

class TestWarningHeaderHelpers:
    """Tests for deprecation warning helper functions."""
    
    def test_add_deprecation_warning_sets_headers(self):
        """Verify add_deprecation_warning adds correct headers."""
        from app.core.middleware.deprecation import add_deprecation_warning
        
        response = Response(content="test")
        result = add_deprecation_warning(response, "Use /new/path instead")
        
        assert "Warning" in result.headers
        assert "299" in result.headers["Warning"]
        assert "Deprecated" in result.headers["Warning"]
        assert result.headers["Deprecation"] == "true"
    
    def test_create_deprecated_redirect_returns_redirect(self):
        """Verify create_deprecated_redirect creates RedirectResponse."""
        from app.core.middleware.deprecation import create_deprecated_redirect
        
        response = create_deprecated_redirect(
            redirect_to="/new/path",
            message="Old endpoint deprecated",
        )
        
        assert response.status_code == 307  # Temporary redirect
        assert "Warning" in response.headers
        assert "299" in response.headers["Warning"]
    
    def test_create_deprecated_redirect_custom_status(self):
        """Verify create_deprecated_redirect accepts custom status code."""
        from app.core.middleware.deprecation import create_deprecated_redirect
        
        response = create_deprecated_redirect(
            redirect_to="/new/path",
            message="Old endpoint deprecated",
            status_code=308,  # Permanent redirect
        )
        
        assert response.status_code == 308


# =============================================================================
# TESTS: Deprecation middleware
# =============================================================================

class TestDeprecationMiddleware:
    """Tests for DeprecationMiddleware."""
    
    def test_middleware_adds_warning_to_deprecated_route(self):
        """Verify middleware adds Warning header to deprecated routes."""
        from app.core.middleware.deprecation import DeprecationMiddleware
        
        # Create a simple test app
        async def homepage(request):
            return JSONResponse({"status": "ok"})
        
        app = Starlette(
            routes=[Route("/view/ArchitecturalSummaryView", homepage)],
        )
        app.add_middleware(DeprecationMiddleware)

        client = TestClient(app)
        response = client.get("/view/ArchitecturalSummaryView")

        assert response.status_code == 200
        assert "Warning" in response.headers
        assert "299" in response.headers["Warning"]
        assert "Deprecated" in response.headers["Warning"]
    
    def test_middleware_does_not_add_warning_to_normal_route(self):
        """Verify middleware does not add Warning header to non-deprecated routes."""
        from app.core.middleware.deprecation import DeprecationMiddleware
        
        async def homepage(request):
            return JSONResponse({"status": "ok"})
        
        app = Starlette(
            routes=[Route("/api/health", homepage)],
        )
        app.add_middleware(DeprecationMiddleware)
        
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert response.status_code == 200
        assert "Warning" not in response.headers
    
    def test_middleware_sets_deprecation_header(self):
        """Verify middleware sets Deprecation: true header."""
        from app.core.middleware.deprecation import DeprecationMiddleware
        
        async def homepage(request):
            return JSONResponse({"status": "ok"})
        
        app = Starlette(
            routes=[Route("/view/ArchitecturalSummaryView", homepage)],
        )
        app.add_middleware(DeprecationMiddleware)

        client = TestClient(app)
        response = client.get("/view/ArchitecturalSummaryView")

        assert response.headers.get("Deprecation") == "true"


# =============================================================================
# TESTS: Warning header format
# =============================================================================

class TestWarningHeaderFormat:
    """Tests for RFC 7234 compliant Warning header format."""
    
    def test_warning_header_format_is_rfc_compliant(self):
        """Verify Warning header follows RFC 7234 format."""
        from app.core.middleware.deprecation import add_deprecation_warning
        
        response = Response(content="test")
        result = add_deprecation_warning(response, "Test message")
        
        warning = result.headers["Warning"]
        
        # RFC 7234 format: warn-code warn-agent "warn-text"
        # We use: 299 - "Deprecated: message"
        assert warning.startswith("299 ")
        assert '"' in warning  # Text should be quoted
    
    def test_warning_code_is_299(self):
        """Verify warning code is 299 (miscellaneous persistent warning)."""
        from app.core.middleware.deprecation import add_deprecation_warning
        
        response = Response(content="test")
        result = add_deprecation_warning(response, "Test message")
        
        warning = result.headers["Warning"]
        assert warning.startswith("299")
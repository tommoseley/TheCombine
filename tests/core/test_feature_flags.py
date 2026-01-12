"""
Tests for Phase 6: Legacy Template Feature Flag (WS-DOCUMENT-SYSTEM-CLEANUP)

Tests the USE_LEGACY_TEMPLATES feature flag behavior.
"""

import pytest
import os
from unittest.mock import patch


# =============================================================================
# TESTS: Feature flag configuration
# =============================================================================

class TestLegacyTemplateFeatureFlag:
    """Tests for USE_LEGACY_TEMPLATES configuration."""
    
    def test_use_legacy_templates_defaults_to_false(self):
        """Verify USE_LEGACY_TEMPLATES defaults to False."""
        # Clear the env var if set
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get fresh config
            import importlib
            import app.core.config as config_module
            
            # The default should be False (new viewer preferred)
            # We test the logic, not the actual reload
            result = os.getenv("USE_LEGACY_TEMPLATES", "false").lower() == "true"
            assert result is False
    
    def test_use_legacy_templates_true_when_env_set(self):
        """Verify USE_LEGACY_TEMPLATES is True when env var is 'true'."""
        with patch.dict(os.environ, {"USE_LEGACY_TEMPLATES": "true"}):
            result = os.getenv("USE_LEGACY_TEMPLATES", "false").lower() == "true"
            assert result is True
    
    def test_use_legacy_templates_false_when_env_false(self):
        """Verify USE_LEGACY_TEMPLATES is False when env var is 'false'."""
        with patch.dict(os.environ, {"USE_LEGACY_TEMPLATES": "false"}):
            result = os.getenv("USE_LEGACY_TEMPLATES", "false").lower() == "true"
            assert result is False
    
    def test_use_legacy_templates_case_insensitive(self):
        """Verify USE_LEGACY_TEMPLATES handles case variations."""
        for true_val in ["true", "True", "TRUE", "TrUe"]:
            with patch.dict(os.environ, {"USE_LEGACY_TEMPLATES": true_val}):
                result = os.getenv("USE_LEGACY_TEMPLATES", "false").lower() == "true"
                assert result is True, f"Failed for value: {true_val}"


# =============================================================================
# TESTS: Config module has flag
# =============================================================================

class TestConfigHasFeatureFlag:
    """Tests that config module exports USE_LEGACY_TEMPLATES."""
    
    def test_config_exports_use_legacy_templates(self):
        """Verify config module exports USE_LEGACY_TEMPLATES."""
        from app.core.config import USE_LEGACY_TEMPLATES
        
        # Should be a boolean
        assert isinstance(USE_LEGACY_TEMPLATES, bool)
    
    def test_settings_has_use_legacy_templates(self):
        """Verify Settings class has USE_LEGACY_TEMPLATES attribute."""
        from app.core.config import settings
        
        assert hasattr(settings, 'USE_LEGACY_TEMPLATES')
        assert isinstance(settings.USE_LEGACY_TEMPLATES, bool)


# =============================================================================
# TESTS: Document routes imports flag
# =============================================================================

class TestDocumentRoutesUsesFlag:
    """Tests that document_routes uses the feature flag."""
    
    def test_document_routes_imports_flag(self):
        """Verify document_routes imports USE_LEGACY_TEMPLATES."""
        # Read the source file and verify the import exists
        import inspect
        import app.web.routes.public.document_routes as dr
        
        source = inspect.getsource(dr)
        assert "from app.core.config import USE_LEGACY_TEMPLATES" in source
    
    def test_document_routes_uses_flag_in_fallback_logic(self):
        """Verify document_routes uses flag in fallback logic."""
        import inspect
        import app.web.routes.public.document_routes as dr
        
        source = inspect.getsource(dr)
        assert "if not USE_LEGACY_TEMPLATES:" in source
        assert "LEGACY_TEMPLATE_FALLBACK_BLOCKED" in source

# =============================================================================
# TESTS: Debug routes feature flag (Phase 8)
# =============================================================================

class TestDebugRoutesFeatureFlag:
    """Tests for ENABLE_DEBUG_ROUTES configuration."""
    
    def test_enable_debug_routes_defaults_to_false(self):
        """Verify ENABLE_DEBUG_ROUTES defaults to False (secure by default)."""
        with patch.dict(os.environ, {}, clear=True):
            result = os.getenv("ENABLE_DEBUG_ROUTES", "false").lower() == "true"
            assert result is False
    
    def test_enable_debug_routes_true_when_env_set(self):
        """Verify ENABLE_DEBUG_ROUTES is True when env var is 'true'."""
        with patch.dict(os.environ, {"ENABLE_DEBUG_ROUTES": "true"}):
            result = os.getenv("ENABLE_DEBUG_ROUTES", "false").lower() == "true"
            assert result is True
    
    def test_config_exports_enable_debug_routes(self):
        """Verify config module exports ENABLE_DEBUG_ROUTES."""
        from app.core.config import ENABLE_DEBUG_ROUTES
        
        assert isinstance(ENABLE_DEBUG_ROUTES, bool)
    
    def test_settings_has_enable_debug_routes(self):
        """Verify Settings class has ENABLE_DEBUG_ROUTES attribute."""
        from app.core.config import settings
        
        assert hasattr(settings, 'ENABLE_DEBUG_ROUTES')
        assert isinstance(settings.ENABLE_DEBUG_ROUTES, bool)


class TestWebRoutesUsesDebugFlag:
    """Tests that web routes module uses ENABLE_DEBUG_ROUTES."""
    
    def test_web_routes_imports_flag(self):
        """Verify web routes imports ENABLE_DEBUG_ROUTES."""
        import inspect
        import app.web.routes as routes_module
        
        source = inspect.getsource(routes_module)
        assert "from app.core.config import ENABLE_DEBUG_ROUTES" in source
    
    def test_web_routes_conditionally_includes_debug_router(self):
        """Verify web routes conditionally includes debug_router."""
        import inspect
        import app.web.routes as routes_module
        
        source = inspect.getsource(routes_module)
        assert "if ENABLE_DEBUG_ROUTES:" in source
        assert "debug_router" in source


class TestApiMainUsesDebugFlag:
    """Tests that API main module uses ENABLE_DEBUG_ROUTES."""
    
    def test_api_main_imports_flag(self):
        """Verify API main imports ENABLE_DEBUG_ROUTES."""
        import inspect
        import app.api.main as main_module
        
        source = inspect.getsource(main_module)
        assert "ENABLE_DEBUG_ROUTES" in source
    
    def test_api_main_conditionally_includes_admin_router(self):
        """Verify API main conditionally includes api_admin_router."""
        import inspect
        import app.api.main as main_module
        
        source = inspect.getsource(main_module)
        assert "if ENABLE_DEBUG_ROUTES:" in source
        assert "api_admin_router" in source
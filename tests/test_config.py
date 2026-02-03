"""Tests for application configuration."""

import pytest
import os
from unittest.mock import patch

from app.settings import (
    Settings,
    load_settings_from_env,
    get_settings,
    clear_settings_cache,
)


class TestSettings:
    """Tests for Settings dataclass."""
    
    def test_default_settings(self):
        """Default settings are valid."""
        settings = Settings()
        assert settings.app_name == "The Combine"
        assert settings.debug is False
        assert settings.environment == "development"
    
    def test_is_production(self):
        """is_production property works correctly."""
        dev = Settings(environment="development")
        assert dev.is_production is False
        assert dev.is_development is True
        
        prod = Settings(environment="production", secret_key="x" * 32)
        assert prod.is_production is True
        assert prod.is_development is False
    
    def test_production_requires_secret_key(self):
        """Production environment requires secret key."""
        with pytest.raises(ValueError, match="SECRET_KEY is required"):
            Settings(environment="production", secret_key="")
    
    def test_production_requires_long_secret_key(self):
        """Production requires at least 32 char secret key."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            Settings(environment="production", secret_key="short")
    
    def test_production_enables_secure_cookies(self):
        """Production automatically enables secure cookies."""
        settings = Settings(
            environment="production",
            secret_key="x" * 32,
            session_secure_cookies=False,
        )
        assert settings.session_secure_cookies is True
    
    def test_allowed_origins_default(self):
        """Default allowed origins includes localhost."""
        settings = Settings()
        assert "http://localhost:8000" in settings.allowed_origins


class TestLoadSettingsFromEnv:
    """Tests for loading settings from environment."""
    
    def test_loads_defaults_without_env(self):
        """Loads default values when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            clear_settings_cache()
            settings = load_settings_from_env()
            assert settings.app_name == "The Combine"
            assert settings.debug is False
    
    def test_loads_string_from_env(self):
        """Loads string values from environment."""
        with patch.dict(os.environ, {"APP_NAME": "Custom App"}, clear=True):
            settings = load_settings_from_env()
            assert settings.app_name == "Custom App"
    
    def test_loads_bool_from_env(self):
        """Loads boolean values from environment."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=True):
            settings = load_settings_from_env()
            assert settings.debug is True
        
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=True):
            settings = load_settings_from_env()
            assert settings.debug is False
    
    def test_loads_int_from_env(self):
        """Loads integer values from environment."""
        with patch.dict(os.environ, {"PORT": "9000"}, clear=True):
            settings = load_settings_from_env()
            assert settings.port == 9000
    
    def test_loads_list_from_env(self):
        """Loads comma-separated list from environment."""
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://a.com,http://b.com"}, clear=True):
            settings = load_settings_from_env()
            assert settings.allowed_origins == ["http://a.com", "http://b.com"]
    
    def test_loads_optional_oauth_settings(self):
        """OAuth settings are optional."""
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings_from_env()
            assert settings.google_client_id is None
            assert settings.microsoft_client_id is None
    
    def test_loads_oauth_when_present(self):
        """OAuth settings loaded when present."""
        env = {
            "GOOGLE_CLIENT_ID": "google_123",
            "GOOGLE_CLIENT_SECRET": "google_secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings_from_env()
            assert settings.google_client_id == "google_123"
            assert settings.google_client_secret == "google_secret"


class TestGetSettings:
    """Tests for cached settings getter."""
    
    def test_get_settings_returns_settings(self):
        """get_settings returns Settings instance."""
        clear_settings_cache()
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_get_settings_is_cached(self):
        """get_settings returns cached instance."""
        clear_settings_cache()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
    
    def test_clear_cache_allows_reload(self):
        """clear_settings_cache allows reloading settings."""
        clear_settings_cache()
        settings1 = get_settings()
        
        clear_settings_cache()
        settings2 = get_settings()
        
        # Different instances after cache clear
        assert settings1 is not settings2

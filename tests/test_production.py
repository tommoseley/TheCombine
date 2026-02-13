"""Tests for production readiness."""

import pytest
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.settings import Settings, load_settings_from_env, clear_settings_cache
from app.health import HealthChecker, HealthStatus, ComponentHealth


class TestProductionSettings:
    """Tests for production environment settings."""
    
    def test_production_enforces_security(self):
        """Production environment enforces security settings."""
        settings = Settings(
            environment="production",
            secret_key="a" * 32,
        )
        assert settings.session_secure_cookies is True
        assert settings.is_production is True
    
    def test_production_rejects_weak_secret(self):
        """Production rejects weak secret keys."""
        with pytest.raises(ValueError):
            Settings(environment="production", secret_key="weak")
    
    def test_staging_environment(self):
        """Staging environment is recognized."""
        settings = Settings(environment="staging")
        assert settings.is_production is False
        assert settings.is_development is False
    
    def test_database_pool_settings(self):
        """Database pool settings are configurable."""
        settings = Settings(
            database_pool_size=10,
            database_max_overflow=20,
        )
        assert settings.database_pool_size == 10
        assert settings.database_max_overflow == 20


class TestEnvironmentVariables:
    """Tests for environment variable configuration."""
    
    def test_full_production_config(self):
        """Full production configuration from environment."""
        env = {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "production-secret-key-that-is-long-enough",
            "DATABASE_URL": "postgresql://user:pass@host/db",
            "SESSION_SECURE_COOKIES": "true",
            "LOG_LEVEL": "WARNING",
            "LOG_FORMAT": "json",
            "GOOGLE_CLIENT_ID": "google-id",
            "GOOGLE_CLIENT_SECRET": "google-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            clear_settings_cache()
            settings = load_settings_from_env()
            
            assert settings.environment == "production"
            assert settings.database_url == "postgresql://user:pass@host/db"
            assert settings.log_level == "WARNING"
            assert settings.google_client_id == "google-id"
    
    def test_port_configuration(self):
        """Port can be configured via environment."""
        with patch.dict(os.environ, {"PORT": "9000"}, clear=True):
            settings = load_settings_from_env()
            assert settings.port == 9000
    
    def test_pat_expiry_configuration(self):
        """PAT expiry can be configured."""
        with patch.dict(os.environ, {"PAT_DEFAULT_EXPIRY_DAYS": "30"}, clear=True):
            settings = load_settings_from_env()
            assert settings.pat_default_expiry_days == 30


class TestHealthCheckIntegration:
    """Tests for health check integration with config."""
    
    @pytest.mark.asyncio
    async def test_health_checker_with_config(self):
        """Health checker uses config values."""
        settings = Settings(app_version="2.0.0", environment="staging")
        checker = HealthChecker(
            version=settings.app_version,
            environment=settings.environment,
        )
        
        result = await checker.check_health()
        assert result.version == "2.0.0"
        assert result.environment == "staging"
    
    @pytest.mark.asyncio
    async def test_multiple_health_checks(self):
        """Multiple health checks are aggregated correctly."""
        checker = HealthChecker(version="1.0.0", environment="test")
        
        async def db_check():
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=5.0,
            )
        
        async def cache_check():
            return ComponentHealth(
                name="cache",
                status=HealthStatus.HEALTHY,
                latency_ms=1.0,
            )
        
        checker.register_check("database", db_check)
        checker.register_check("cache", cache_check)
        
        result = await checker.check_health()
        
        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 2
        assert "database" in result.components
        assert "cache" in result.components
    
    @pytest.mark.asyncio
    async def test_health_check_latency_tracking(self):
        """Health check tracks latency."""
        import asyncio
        
        checker = HealthChecker(version="1.0.0", environment="test")
        
        async def slow_check():
            await asyncio.sleep(0.01)  # 10ms
            return True
        
        checker.register_check("slow", slow_check)
        result = await checker.check_health()
        
        assert result.components["slow"].latency_ms >= 10


class TestGracefulShutdown:
    """Tests for graceful shutdown behavior."""
    
    def test_settings_for_graceful_shutdown(self):
        """Settings support graceful shutdown configuration."""
        # The Settings class should be usable for shutdown config
        settings = Settings()
        # These would be used by the shutdown handler
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'session_expire_hours')


class TestSecuritySettings:
    """Tests for security-related settings."""
    
    def test_cors_origins_parsing(self):
        """CORS origins are parsed correctly."""
        with patch.dict(os.environ, {
            "ALLOWED_ORIGINS": "https://app.example.com,https://admin.example.com"
        }, clear=True):
            settings = load_settings_from_env()
            assert len(settings.allowed_origins) == 2
            assert "https://app.example.com" in settings.allowed_origins
    
    def test_session_cookie_name(self):
        """Session cookie name is configurable."""
        with patch.dict(os.environ, {
            "SESSION_COOKIE_NAME": "__Host-session"
        }, clear=True):
            settings = load_settings_from_env()
            assert settings.session_cookie_name == "__Host-session"
    
    def test_session_duration(self):
        """Session duration is configurable."""
        with patch.dict(os.environ, {"SESSION_EXPIRE_HOURS": "48"}, clear=True):
            settings = load_settings_from_env()
            assert settings.session_expire_hours == 48

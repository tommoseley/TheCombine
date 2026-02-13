"""Tests for environment configuration and validation."""

import pytest
import os
from unittest.mock import patch

from app.core.environment import (
    Environment,
    EnvironmentType,
    ValidationResult,
    REQUIRED_VARS,
    SENSITIVE_VARS,
)


class TestEnvironmentType:
    """Tests for environment type enum."""
    
    def test_environment_types_exist(self):
        """All expected environment types exist."""
        assert EnvironmentType.DEVELOPMENT.value == "development"
        assert EnvironmentType.STAGING.value == "staging"
        assert EnvironmentType.PRODUCTION.value == "production"
        assert EnvironmentType.TEST.value == "test"


class TestEnvironmentDetection:
    """Tests for environment detection."""
    
    def test_detects_from_env_var(self):
        """Detects environment from ENVIRONMENT var."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            assert Environment.current() == EnvironmentType.STAGING
    
    def test_detects_production(self):
        """Detects production environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert Environment.current() == EnvironmentType.PRODUCTION
    
    def test_is_development(self):
        """is_development helper works."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert Environment.is_development() is True
            assert Environment.is_production() is False
    
    def test_is_staging(self):
        """is_staging helper works."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            assert Environment.is_staging() is True
            assert Environment.is_development() is False
    
    def test_is_production(self):
        """is_production helper works."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert Environment.is_production() is True
            assert Environment.is_staging() is False


class TestValidationResult:
    """Tests for ValidationResult."""
    
    def test_valid_result(self):
        """Valid result has no missing vars."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.missing_vars == []
    
    def test_invalid_result(self):
        """Invalid result has missing vars."""
        result = ValidationResult(
            valid=False,
            missing_vars=["DATABASE_URL", "SECRET_KEY"]
        )
        assert result.valid is False
        assert "DATABASE_URL" in result.missing_vars
    
    def test_raise_if_invalid(self):
        """raise_if_invalid raises for invalid result."""
        result = ValidationResult(
            valid=False,
            missing_vars=["MISSING_VAR"]
        )
        
        with pytest.raises(EnvironmentError) as exc_info:
            result.raise_if_invalid()
        
        assert "MISSING_VAR" in str(exc_info.value)
    
    def test_raise_if_invalid_noop_when_valid(self):
        """raise_if_invalid does nothing when valid."""
        result = ValidationResult(valid=True)
        result.raise_if_invalid()  # Should not raise


class TestEnvironmentValidation:
    """Tests for environment validation."""
    
    def test_validate_with_all_vars_set(self):
        """Validation passes when all required vars set."""
        env_vars = {
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "test-secret-key",
            "ENVIRONMENT": "development",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            result = Environment.validate(EnvironmentType.DEVELOPMENT)
            assert result.valid is True
    
    def test_validate_missing_database_url(self):
        """Validation fails without DATABASE_URL."""
        env_vars = {
            "SECRET_KEY": "test-key",
            "ENVIRONMENT": "development",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            result = Environment.validate(EnvironmentType.DEVELOPMENT)
            assert result.valid is False
            assert "DATABASE_URL" in result.missing_vars
    
    def test_validate_staging_requires_anthropic_key(self):
        """Staging requires ANTHROPIC_API_KEY."""
        env_vars = {
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "test-key",
            "ENVIRONMENT": "staging",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            result = Environment.validate(EnvironmentType.STAGING)
            assert "ANTHROPIC_API_KEY" in result.missing_vars
    
    def test_validate_warnings_for_debug_in_staging(self):
        """Warning when DEBUG=true in staging."""
        env_vars = {
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "test-key",
            "ANTHROPIC_API_KEY": "sk-test",
            "DEBUG": "true",
            "ENVIRONMENT": "staging",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            result = Environment.validate(EnvironmentType.STAGING)
            assert any("DEBUG" in w for w in result.warnings)


class TestConfigSummary:
    """Tests for configuration summary."""
    
    def test_get_config_summary(self):
        """Config summary includes expected fields."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "LOG_LEVEL": "DEBUG",
            "API_PORT": "9000",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = Environment.get_config_summary()
            
            assert config["environment"] == "staging"
            assert config["log_level"] == "DEBUG"
            assert config["api_port"] == "9000"
    
    def test_config_summary_sanitizes_secrets(self):
        """Config summary masks sensitive values."""
        env_vars = {
            "SECRET_KEY": "this-is-a-very-long-secret-key",
            "DATABASE_URL": "postgresql://user:password@host/db",
            "ENVIRONMENT": "development",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = Environment.get_config_summary(sanitize=True)
            
            # Should be masked
            assert config["secret_key"] == "this...-key"
            assert "password" not in str(config["database_url"])
    
    def test_config_summary_unsanitized(self):
        """Config summary can return raw values."""
        env_vars = {
            "SECRET_KEY": "my-secret",
            "ENVIRONMENT": "development",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = Environment.get_config_summary(sanitize=False)
            
            assert config["secret_key"] == "my-secret"


class TestRequiredVars:
    """Tests for required variables configuration."""
    
    def test_all_environments_require_database_url(self):
        """DATABASE_URL required for all environments."""
        assert "DATABASE_URL" in REQUIRED_VARS["all"]
    
    def test_all_environments_require_secret_key(self):
        """SECRET_KEY required for all environments."""
        assert "SECRET_KEY" in REQUIRED_VARS["all"]
    
    def test_staging_requires_anthropic_key(self):
        """Staging requires ANTHROPIC_API_KEY."""
        assert "ANTHROPIC_API_KEY" in REQUIRED_VARS["staging"]


class TestSensitiveVars:
    """Tests for sensitive variables list."""
    
    def test_secrets_are_marked_sensitive(self):
        """Secret keys are in SENSITIVE_VARS."""
        assert "SECRET_KEY" in SENSITIVE_VARS
        assert "DATABASE_URL" in SENSITIVE_VARS
        assert "ANTHROPIC_API_KEY" in SENSITIVE_VARS
        assert "GOOGLE_CLIENT_SECRET" in SENSITIVE_VARS


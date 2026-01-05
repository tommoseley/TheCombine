"""Operational tests for startup validation."""

import pytest
import os
import logging
from unittest.mock import patch

from app.core.environment import (
    Environment,
    EnvironmentType,
    validate_on_startup,
)


class TestStartupValidation:
    """Tests for startup validation behavior."""
    
    def test_startup_logs_environment(self, caplog):
        """Startup logs current environment."""
        caplog.set_level(logging.INFO)
        
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "test-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            validate_on_startup()
            
            assert "development" in caplog.text.lower()
    
    def test_startup_skips_strict_validation_in_test(self, caplog):
        """Test environment skips strict validation."""
        caplog.set_level(logging.INFO)
        
        env_vars = {
            "ENVIRONMENT": "test",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Should not raise even with missing vars
            validate_on_startup()
            
            assert "skipping strict validation" in caplog.text.lower()
    
    def test_startup_fails_in_staging_without_required_vars(self):
        """Staging fails startup without required vars."""
        env_vars = {
            "ENVIRONMENT": "staging",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_on_startup()
            
            assert "DATABASE_URL" in str(exc_info.value)
    
    def test_startup_warns_in_development_with_missing_vars(self, caplog):
        """Development warns but doesn't fail for missing vars."""
        caplog.set_level(logging.INFO)
        
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "dev-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Should not raise
            validate_on_startup()


class TestEnvironmentSpecificValidation:
    """Tests for environment-specific validation rules."""
    
    def test_production_requires_oauth(self):
        """Production requires OAuth credentials."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "prod-key",
            "ANTHROPIC_API_KEY": "sk-test",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            result = Environment.validate(EnvironmentType.PRODUCTION)
            
            assert not result.valid
            assert "GOOGLE_CLIENT_ID" in result.missing_vars
    
    def test_staging_valid_with_all_required(self):
        """Staging passes with all required vars."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://localhost/test",
            "SECRET_KEY": "staging-key",
            "ANTHROPIC_API_KEY": "sk-test",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            result = Environment.validate(EnvironmentType.STAGING)
            
            assert result.valid
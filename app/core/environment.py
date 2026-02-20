"""
Environment configuration and validation for The Combine.

Provides environment detection, required variable validation,
and sanitized configuration logging.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class EnvironmentType(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    DEV_AWS = "dev_aws"
    TEST_AWS = "test_aws"


# Required environment variables by environment
REQUIRED_VARS = {
    "all": [
        "DATABASE_URL",
        "SECRET_KEY",
    ],
    "staging": [
        "ANTHROPIC_API_KEY",
    ],
    "production": [
        "ANTHROPIC_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ],
}

# Variables that should never be logged
SENSITIVE_VARS = {
    "SECRET_KEY",
    "DATABASE_URL",
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_SECRET",
    "MICROSOFT_CLIENT_SECRET",
    "POSTGRES_PASSWORD",
}


@dataclass
class ValidationResult:
    """Result of environment validation."""
    valid: bool
    missing_vars: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def raise_if_invalid(self) -> None:
        """Raise exception if validation failed."""
        if not self.valid:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(self.missing_vars)}"
            )


class Environment:
    """Environment detection and configuration."""
    
    @classmethod
    def current(cls) -> EnvironmentType:
        """
        Get current environment type.
        
        Detection order:
        1. ENVIRONMENT env var
        2. pytest detection
        3. Default to development
        """
        env_str = os.getenv("ENVIRONMENT", "").lower()

        if env_str:
            try:
                return EnvironmentType(env_str)
            except ValueError:
                valid = ", ".join(e.value for e in EnvironmentType)
                raise ValueError(
                    f"Invalid ENVIRONMENT value: '{env_str}'. "
                    f"Must be one of: {valid}"
                )

        # Detect test environment
        if "pytest" in os.environ.get("_", "") or "pytest" in __import__("sys").modules:
            return EnvironmentType.TEST

        return EnvironmentType.DEVELOPMENT
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development."""
        return cls.current() == EnvironmentType.DEVELOPMENT
    
    @classmethod
    def is_staging(cls) -> bool:
        """Check if running in staging."""
        return cls.current() == EnvironmentType.STAGING
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production."""
        return cls.current() == EnvironmentType.PRODUCTION
    
    @classmethod
    def is_test(cls) -> bool:
        """Check if running in test."""
        return cls.current() == EnvironmentType.TEST
    
    @classmethod
    def validate(cls, environment: Optional[EnvironmentType] = None) -> ValidationResult:
        """
        Validate required environment variables are set.
        
        Args:
            environment: Environment to validate for. Defaults to current.
            
        Returns:
            ValidationResult with missing variables and warnings.
        """
        if environment is None:
            environment = cls.current()
        
        missing = []
        warnings = []
        
        # Check vars required for all environments
        for var in REQUIRED_VARS.get("all", []):
            if not os.getenv(var):
                missing.append(var)
        
        # Check vars required for specific environment
        env_key = environment.value
        for var in REQUIRED_VARS.get(env_key, []):
            if not os.getenv(var):
                missing.append(var)
        
        # Warnings for recommended but not required
        if not os.getenv("LOG_LEVEL"):
            warnings.append("LOG_LEVEL not set, defaulting to INFO")
        
        if environment in (EnvironmentType.STAGING, EnvironmentType.PRODUCTION):
            if os.getenv("DEBUG", "").lower() == "true":
                warnings.append("DEBUG=true in non-development environment")
        
        return ValidationResult(
            valid=len(missing) == 0,
            missing_vars=missing,
            warnings=warnings,
        )
    
    @classmethod
    def get_config_summary(cls, sanitize: bool = True) -> Dict[str, Any]:
        """
        Get configuration summary for logging.
        
        Args:
            sanitize: If True, mask sensitive values.
            
        Returns:
            Dictionary of configuration values.
        """
        config = {
            "environment": cls.current().value,
            "debug": os.getenv("DEBUG", "false"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_format": os.getenv("LOG_FORMAT", "text"),
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": os.getenv("API_PORT", "8000"),
        }
        
        # Add sensitive vars (masked if sanitize=True)
        sensitive_config = [
            "DATABASE_URL",
            "SECRET_KEY", 
            "ANTHROPIC_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "MICROSOFT_CLIENT_ID",
            "MICROSOFT_CLIENT_SECRET",
        ]
        
        for var in sensitive_config:
            value = os.getenv(var)
            if value:
                if sanitize and var in SENSITIVE_VARS:
                    # Show first 4 and last 4 chars only
                    if len(value) > 12:
                        config[var.lower()] = f"{value[:4]}...{value[-4:]}"
                    else:
                        config[var.lower()] = "****"
                else:
                    config[var.lower()] = value
            else:
                config[var.lower()] = None
        
        return config


def validate_on_startup() -> None:
    """
    Validate environment on application startup.
    
    Call this in application lifespan/startup.
    Raises EnvironmentError if validation fails.
    """
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    env = Environment.current()
    logger.info(f"Starting in {env.value} environment")
    
    # Skip strict validation in test environment
    if env == EnvironmentType.TEST:
        logger.info("Test environment - skipping strict validation")
        return
    
    result = Environment.validate()
    
    # Log warnings
    for warning in result.warnings:
        logger.warning(warning)
    
    # Log sanitized config
    config = Environment.get_config_summary(sanitize=True)
    logger.info(f"Configuration: {config}")
    
    # Fail if invalid (except in development where we're more lenient)
    if not result.valid:
        if env == EnvironmentType.DEVELOPMENT:
            logger.warning(f"Missing recommended vars: {result.missing_vars}")
        else:
            result.raise_if_invalid()

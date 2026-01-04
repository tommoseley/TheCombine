"""Application configuration management."""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from functools import lru_cache


@dataclass
class Settings:
    """Application settings loaded from environment."""
    
    # App
    app_name: str = "The Combine"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    secret_key: str = ""  # Required in production
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:8000"])
    
    # Database
    database_url: str = "sqlite:///./combine.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Session
    session_cookie_name: str = "session"
    session_expire_hours: int = 24
    session_secure_cookies: bool = False  # True in production (HTTPS)
    
    # OAuth - Google
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None
    
    # OAuth - Microsoft
    microsoft_client_id: Optional[str] = None
    microsoft_client_secret: Optional[str] = None
    microsoft_tenant_id: Optional[str] = None
    microsoft_redirect_uri: Optional[str] = None
    
    # PAT
    pat_default_expiry_days: int = 90
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    def __post_init__(self):
        """Validate settings after initialization."""
        if self.environment == "production":
            if not self.secret_key:
                raise ValueError("SECRET_KEY is required in production")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters")
            self.session_secure_cookies = True
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


def load_settings_from_env() -> Settings:
    """Load settings from environment variables."""
    
    def get_bool(key: str, default: bool = False) -> bool:
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes")
    
    def get_int(key: str, default: int) -> int:
        return int(os.getenv(key, str(default)))
    
    def get_list(key: str, default: List[str]) -> List[str]:
        value = os.getenv(key)
        if value:
            return [item.strip() for item in value.split(",")]
        return default
    
    return Settings(
        # App
        app_name=os.getenv("APP_NAME", "The Combine"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        debug=get_bool("DEBUG", False),
        environment=os.getenv("ENVIRONMENT", "development"),
        
        # Server
        host=os.getenv("HOST", "0.0.0.0"),
        port=get_int("PORT", 8000),
        
        # Security
        secret_key=os.getenv("SECRET_KEY", ""),
        allowed_origins=get_list("ALLOWED_ORIGINS", ["http://localhost:8000"]),
        
        # Database
        database_url=os.getenv("DATABASE_URL", "sqlite:///./combine.db"),
        database_pool_size=get_int("DATABASE_POOL_SIZE", 5),
        database_max_overflow=get_int("DATABASE_MAX_OVERFLOW", 10),
        
        # Session
        session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "session"),
        session_expire_hours=get_int("SESSION_EXPIRE_HOURS", 24),
        session_secure_cookies=get_bool("SESSION_SECURE_COOKIES", False),
        
        # OAuth - Google
        google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
        
        # OAuth - Microsoft
        microsoft_client_id=os.getenv("MICROSOFT_CLIENT_ID"),
        microsoft_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
        microsoft_tenant_id=os.getenv("MICROSOFT_TENANT_ID"),
        microsoft_redirect_uri=os.getenv("MICROSOFT_REDIRECT_URI"),
        
        # PAT
        pat_default_expiry_days=get_int("PAT_DEFAULT_EXPIRY_DAYS", 90),
        
        # Logging
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "json"),
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return load_settings_from_env()


def clear_settings_cache() -> None:
    """Clear settings cache (for testing)."""
    get_settings.cache_clear()

"""
Authentication data models.

ADR-008: Multi-Provider OAuth Authentication
Defines core domain models for auth system:
- User: Core user identity
- UserSession: Web session with CSRF token
- PersonalAccessToken: API authentication
- AuthContext: Current authenticated user context
- Enums: OIDCProvider, AuthEventType
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class OIDCProvider(str, Enum):
    """Supported OIDC providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"


class AuthEventType(str, Enum):
    """Authentication audit log event types."""
    
    # Login events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_BLOCKED_EMAIL_EXISTS = "login_blocked_email_exists"
    LOGOUT = "logout"
    
    # Session events
    SESSION_EXPIRED = "session_expired"
    
    # Account linking events
    ACCOUNT_LINKED = "account_linked"
    LINK_CSRF_BLOCKED = "link_csrf_blocked"
    LINK_NONCE_INVALID = "link_nonce_invalid"
    
    # PAT events
    PAT_CREATED = "pat_created"
    PAT_REVOKED = "pat_revoked"
    PAT_AUTH_FAILURE = "pat_auth_failure"
    
    # Security violations
    CSRF_VIOLATION = "csrf_violation"
    ORIGIN_VIOLATION = "origin_violation"


@dataclass
class User:
    """
    Core user identity.
    
    Represents a single user in the system, regardless of how many
    OAuth providers they have linked.
    """
    user_id: UUID
    email: str
    email_verified: bool
    name: str
    avatar_url: Optional[str]
    is_active: bool
    user_created_at: datetime
    user_updated_at: datetime
    last_login_at: Optional[datetime]


@dataclass
class UserSession:
    """
    Web session with CSRF token.
    
    Used for cookie-based authentication with synchronizer token
    CSRF protection pattern.
    """
    session_id: UUID
    user_id: UUID
    session_token: str  # 43-char URL-safe base64
    csrf_token: str     # 43-char URL-safe base64
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_created_at: datetime
    last_activity_at: datetime
    expires_at: datetime


@dataclass
class PersonalAccessToken:
    """
    Personal Access Token for API authentication.
    
    Versioned format: combine_pat_v1_<key_id>_<token_id>_<secret>
    Supports multi-key HMAC verification for zero-downtime rotation.
    """
    token_id: UUID
    user_id: UUID
    token_name: str
    token_display: str  # First ~20 chars for UI display
    key_id: str         # Which server key was used for HMAC
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    token_created_at: datetime
    is_active: bool


@dataclass
class AuthContext:
    """
    Current authenticated user context.
    
    Passed to all authenticated endpoints via get_current_user() dependency.
    Contains either session info (web) or token info (API), never both.
    """
    user: User
    session_id: Optional[UUID]  # Present for web auth
    token_id: Optional[UUID]    # Present for API auth
    csrf_token: Optional[str]   # Present for web auth only
    
    @property
    def user_id(self) -> UUID:
        """Convenience accessor for user_id."""
        return self.user.user_id
    
    @property
    def is_session_auth(self) -> bool:
        """True if authenticated via session cookie."""
        return self.session_id is not None
    
    @property
    def is_token_auth(self) -> bool:
        """True if authenticated via PAT."""
        return self.token_id is not None
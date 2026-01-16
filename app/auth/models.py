"""Authentication domain models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum
from uuid import UUID


class AuthProvider(str, Enum):
    """Supported authentication providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    LOCAL = "local"  # For testing/development


class AuthEventType(str, Enum):
    """Types of authentication events for audit logging."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"
    ACCOUNT_LINKED = "account_linked"
    ACCOUNT_UNLINKED = "account_unlinked"
    LINK_BLOCKED_IDENTITY_EXISTS = "link_blocked_identity_exists"
    LOGIN_BLOCKED_EMAIL_EXISTS = "login_blocked_email_exists"
    CSRF_VIOLATION = "csrf_violation"


@dataclass
class User:
    """User domain model."""
    user_id: str
    email: str
    name: str
    is_active: bool = True
    email_verified: bool = False
    avatar_url: Optional[str] = None
    user_created_at: Optional[datetime] = None
    user_updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    provider: Optional[AuthProvider] = None
    provider_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    is_admin: bool = False
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles or "admin" in self.roles
    
    def add_role(self, role: str) -> None:
        """Add a role to the user."""
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        if role in self.roles:
            self.roles.remove(role)


@dataclass
class UserSession:
    """User session for tracking authenticated sessions."""
    session_id: UUID
    user_id: UUID
    session_token: str
    csrf_token: str
    session_created_at: datetime
    expires_at: datetime
    last_activity_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid (not expired)."""
        return not self.is_expired()


@dataclass
class Session:
    """User session model (legacy compatibility)."""
    session_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid (not expired)."""
        return not self.is_expired()


@dataclass
class AuthContext:
    """Authentication context for request processing."""
    user: User
    session_id: Optional[UUID] = None
    token_id: Optional[UUID] = None  # For PAT auth
    csrf_token: Optional[str] = None
    
    @property
    def is_session_auth(self) -> bool:
        """Check if authenticated via session."""
        return self.session_id is not None
    
    @property
    def is_token_auth(self) -> bool:
        """Check if authenticated via PAT."""
        return self.token_id is not None




@dataclass
class PersonalAccessToken:
    """Personal Access Token for API authentication."""
    token_id: str
    user_id: str
    name: str
    token_hash: str
    token_display: str  # First/last chars for display (e.g., "pat_abc...xyz")
    key_id: str  # Short identifier for the token
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid (active and not expired)."""
        return self.is_active and not self.is_expired()
@dataclass 
class OAuthTokens:
    """OAuth tokens from provider."""
    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


@dataclass
class OAuthUserInfo:
    """User info from OAuth provider."""
    provider_id: str
    email: str
    name: str
    picture_url: Optional[str] = None
    email_verified: bool = False

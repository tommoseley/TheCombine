"""Authentication services."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from .models import User, Session, AuthProvider, OAuthUserInfo
from .repositories import (
    UserRepository, 
    SessionRepository,
    UserNotFoundError,
)


def generate_user_id() -> str:
    """Generate a unique user ID."""
    return f"user_{secrets.token_hex(12)}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess_{secrets.token_hex(16)}"


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class SessionService:
    """Service for managing user sessions."""
    
    def __init__(
        self,
        session_repo: SessionRepository,
        user_repo: UserRepository,
        session_duration: timedelta = timedelta(hours=24),
    ):
        self._session_repo = session_repo
        self._user_repo = user_repo
        self._session_duration = session_duration
    
    async def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, Session]:
        """
        Create a new session for a user.
        
        Returns:
            Tuple of (raw_token, session)
            The raw_token should be sent to the client (only returned once).
        """
        token = generate_session_token()
        token_hash = hash_token(token)
        now = datetime.now(timezone.utc)
        
        session = Session(
            session_id=generate_session_id(),
            user_id=user.user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + self._session_duration,
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        await self._session_repo.create(session)
        
        return token, session
    
    async def validate_session(self, token: str) -> Optional[Tuple[User, Session]]:
        """
        Validate a session token.
        
        Returns:
            Tuple of (user, session) if valid, None otherwise.
        """
        token_hash = hash_token(token)
        session = await self._session_repo.get_by_token_hash(token_hash)
        
        if not session:
            return None
        
        if session.is_expired():
            await self._session_repo.delete(session.session_id)
            return None
        
        user = await self._user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            await self._session_repo.delete(session.session_id)
            return None
        
        # Update last activity
        session.last_activity = datetime.now(timezone.utc)
        await self._session_repo.update(session)
        
        return user, session
    
    async def invalidate_session(self, token: str) -> bool:
        """
        Invalidate a session by token.
        
        Returns:
            True if session was found and deleted, False otherwise.
        """
        token_hash = hash_token(token)
        session = await self._session_repo.get_by_token_hash(token_hash)
        
        if session:
            await self._session_repo.delete(session.session_id)
            return True
        
        return False
    
    async def invalidate_all_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user.
        
        Returns:
            Number of sessions invalidated.
        """
        return await self._session_repo.delete_by_user_id(user_id)
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed.
        """
        return await self._session_repo.delete_expired()
    
    async def refresh_session(self, token: str) -> Optional[Session]:
        """
        Refresh a session's expiration time.
        
        Returns:
            Updated session if valid, None otherwise.
        """
        token_hash = hash_token(token)
        session = await self._session_repo.get_by_token_hash(token_hash)
        
        if not session or session.is_expired():
            return None
        
        now = datetime.now(timezone.utc)
        session.expires_at = now + self._session_duration
        session.last_activity = now
        
        await self._session_repo.update(session)
        return session


class UserService:
    """Service for managing users."""
    
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
    
    async def get_or_create_from_oauth(
        self, 
        provider: AuthProvider,
        user_info: OAuthUserInfo,
    ) -> Tuple[User, bool]:
        """
        Get existing user or create new one from OAuth info.
        
        Returns:
            Tuple of (user, is_new_user)
        """
        # Try to find by provider first
        existing = await self._user_repo.get_by_provider(
            provider, user_info.provider_id
        )
        if existing:
            # Update last login
            existing.last_login = datetime.now(timezone.utc)
            await self._user_repo.update(existing)
            return existing, False
        
        # Try to find by email (for account linking)
        existing = await self._user_repo.get_by_email(user_info.email)
        if existing:
            # Could implement account linking here
            # For now, update last login
            existing.last_login = datetime.now(timezone.utc)
            await self._user_repo.update(existing)
            return existing, False
        
        # Create new user
        now = datetime.now(timezone.utc)
        user = User(
            user_id=generate_user_id(),
            email=user_info.email,
            name=user_info.name,
            provider=provider,
            provider_id=user_info.provider_id,
            created_at=now,
            last_login=now,
            is_active=True,
            roles=["operator"],  # Default role for new users
        )
        
        await self._user_repo.create(user)
        return user, True
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await self._user_repo.get_by_id(user_id)
    
    async def deactivate_user(self, user_id: str) -> User:
        """Deactivate a user account."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        
        user.is_active = False
        await self._user_repo.update(user)
        return user
    
    async def update_roles(self, user_id: str, roles: list[str]) -> User:
        """Update user roles."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        
        user.roles = roles
        await self._user_repo.update(user)
        return user

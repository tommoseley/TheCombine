"""Authentication repositories."""

from typing import Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime, timezone

from .models import User, Session, AuthProvider


class UserNotFoundError(Exception):
    """Raised when user is not found."""
    pass


class UserAlreadyExistsError(Exception):
    """Raised when user already exists."""
    pass


class SessionNotFoundError(Exception):
    """Raised when session is not found."""
    pass


@runtime_checkable
class UserRepository(Protocol):
    """Protocol for user storage."""
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        ...
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        ...
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        ...
    
    async def get_by_provider(
        self, provider: AuthProvider, provider_id: str
    ) -> Optional[User]:
        """Get user by OAuth provider and provider ID."""
        ...
    
    async def update(self, user: User) -> User:
        """Update existing user."""
        ...
    
    async def list_all(self) -> List[User]:
        """List all users."""
        ...


@runtime_checkable
class SessionRepository(Protocol):
    """Protocol for session storage."""
    
    async def create(self, session: Session) -> Session:
        """Create a new session."""
        ...
    
    async def get_by_token_hash(self, token_hash: str) -> Optional[Session]:
        """Get session by token hash."""
        ...
    
    async def get_by_user_id(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        ...
    
    async def update(self, session: Session) -> Session:
        """Update session (e.g., last activity)."""
        ...
    
    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        ...
    
    async def delete_expired(self) -> int:
        """Delete all expired sessions. Returns count deleted."""
        ...
    
    async def delete_by_user_id(self, user_id: str) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        ...


class InMemoryUserRepository:
    """In-memory implementation of UserRepository."""
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._by_email: Dict[str, str] = {}  # email -> user_id
        self._by_provider: Dict[str, str] = {}  # "provider:provider_id" -> user_id
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        if user.user_id in self._users:
            raise UserAlreadyExistsError(f"User {user.user_id} already exists")
        
        if user.email in self._by_email:
            raise UserAlreadyExistsError(f"Email {user.email} already registered")
        
        provider_key = f"{user.provider.value}:{user.provider_id}"
        if provider_key in self._by_provider:
            raise UserAlreadyExistsError(
                f"Provider {user.provider.value} ID {user.provider_id} already registered"
            )
        
        self._users[user.user_id] = user
        self._by_email[user.email] = user.user_id
        self._by_provider[provider_key] = user.user_id
        
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = self._by_email.get(email)
        if user_id:
            return self._users.get(user_id)
        return None
    
    async def get_by_provider(
        self, provider: AuthProvider, provider_id: str
    ) -> Optional[User]:
        """Get user by OAuth provider and provider ID."""
        provider_key = f"{provider.value}:{provider_id}"
        user_id = self._by_provider.get(provider_key)
        if user_id:
            return self._users.get(user_id)
        return None
    
    async def update(self, user: User) -> User:
        """Update existing user."""
        if user.user_id not in self._users:
            raise UserNotFoundError(f"User {user.user_id} not found")
        
        old_user = self._users[user.user_id]
        
        # Update email index if changed
        if old_user.email != user.email:
            del self._by_email[old_user.email]
            self._by_email[user.email] = user.user_id
        
        self._users[user.user_id] = user
        return user
    
    async def list_all(self) -> List[User]:
        """List all users."""
        return list(self._users.values())
    
    def clear(self) -> None:
        """Clear all users (for testing)."""
        self._users.clear()
        self._by_email.clear()
        self._by_provider.clear()


class InMemorySessionRepository:
    """In-memory implementation of SessionRepository."""
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._by_token_hash: Dict[str, str] = {}  # token_hash -> session_id
        self._by_user_id: Dict[str, List[str]] = {}  # user_id -> [session_ids]
    
    async def create(self, session: Session) -> Session:
        """Create a new session."""
        self._sessions[session.session_id] = session
        self._by_token_hash[session.token_hash] = session.session_id
        
        if session.user_id not in self._by_user_id:
            self._by_user_id[session.user_id] = []
        self._by_user_id[session.user_id].append(session.session_id)
        
        return session
    
    async def get_by_token_hash(self, token_hash: str) -> Optional[Session]:
        """Get session by token hash."""
        session_id = self._by_token_hash.get(token_hash)
        if session_id:
            return self._sessions.get(session_id)
        return None
    
    async def get_by_user_id(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        session_ids = self._by_user_id.get(user_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    async def update(self, session: Session) -> Session:
        """Update session."""
        if session.session_id not in self._sessions:
            raise SessionNotFoundError(f"Session {session.session_id} not found")
        
        self._sessions[session.session_id] = session
        return session
    
    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            del self._sessions[session_id]
            
            if session.token_hash in self._by_token_hash:
                del self._by_token_hash[session.token_hash]
            
            if session.user_id in self._by_user_id:
                self._by_user_id[session.user_id] = [
                    sid for sid in self._by_user_id[session.user_id] 
                    if sid != session_id
                ]
    
    async def delete_expired(self) -> int:
        """Delete all expired sessions."""
        now = datetime.now(timezone.utc)
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.expires_at < now
        ]
        
        for session_id in expired_ids:
            await self.delete(session_id)
        
        return len(expired_ids)
    
    async def delete_by_user_id(self, user_id: str) -> int:
        """Delete all sessions for a user."""
        session_ids = self._by_user_id.get(user_id, []).copy()
        
        for session_id in session_ids:
            await self.delete(session_id)
        
        return len(session_ids)
    
    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        self._sessions.clear()
        self._by_token_hash.clear()
        self._by_user_id.clear()

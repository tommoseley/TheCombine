"""Tests for session management."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from app.auth import (
    User,
    Session,
    AuthProvider,
    InMemoryUserRepository,
    InMemorySessionRepository,
    SessionService,
)


@pytest.fixture
def user_repo():
    """Create fresh user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def session_repo():
    """Create fresh session repository."""
    return InMemorySessionRepository()


@pytest.fixture
def session_service(session_repo, user_repo):
    """Create session service with 1 hour duration for testing."""
    return SessionService(
        session_repo=session_repo,
        user_repo=user_repo,
        session_duration=timedelta(hours=1),
    )


@pytest_asyncio.fixture
async def sample_user(user_repo):
    """Create and store sample user."""
    user = User(
        user_id="user_test123",
        email="test@example.com",
        name="Test User",
        provider=AuthProvider.GOOGLE,
        provider_id="google_123",
        user_created_at=datetime.now(timezone.utc),
        last_login_at=datetime.now(timezone.utc),
        is_active=True,
        roles=["operator"],
    )
    await user_repo.create(user)
    return user


class TestSessionModel:
    """Tests for Session model."""
    
    def test_session_is_expired(self):
        """Session correctly reports expiration."""
        expired = Session(
            session_id="sess_expired",
            user_id="user_123",
            token_hash="hash123",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            last_activity=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert expired.is_expired() is True
        assert expired.is_valid() is False
    
    def test_session_is_valid(self):
        """Session correctly reports validity."""
        valid = Session(
            session_id="sess_valid",
            user_id="user_123",
            token_hash="hash123",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            last_activity=datetime.now(timezone.utc),
        )
        assert valid.is_expired() is False
        assert valid.is_valid() is True


class TestSessionRepository:
    """Tests for InMemorySessionRepository."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_repo):
        """Can create a session."""
        session = Session(
            session_id="sess_test",
            user_id="user_123",
            token_hash="hash123",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            last_activity=datetime.now(timezone.utc),
        )
        created = await session_repo.create(session)
        assert created.session_id == "sess_test"
    
    @pytest.mark.asyncio
    async def test_get_by_token_hash(self, session_repo):
        """Can retrieve session by token hash."""
        session = Session(
            session_id="sess_test",
            user_id="user_123",
            token_hash="unique_hash",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            last_activity=datetime.now(timezone.utc),
        )
        await session_repo.create(session)
        
        found = await session_repo.get_by_token_hash("unique_hash")
        assert found is not None
        assert found.session_id == "sess_test"
    
    @pytest.mark.asyncio
    async def test_get_by_user_id(self, session_repo):
        """Can retrieve all sessions for a user."""
        for i in range(3):
            session = Session(
                session_id=f"sess_{i}",
                user_id="user_123",
                token_hash=f"hash_{i}",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                last_activity=datetime.now(timezone.utc),
            )
            await session_repo.create(session)
        
        sessions = await session_repo.get_by_user_id("user_123")
        assert len(sessions) == 3
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_repo):
        """Can delete a session."""
        session = Session(
            session_id="sess_delete",
            user_id="user_123",
            token_hash="hash_delete",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            last_activity=datetime.now(timezone.utc),
        )
        await session_repo.create(session)
        
        await session_repo.delete("sess_delete")
        
        found = await session_repo.get_by_token_hash("hash_delete")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_delete_expired(self, session_repo):
        """Can delete all expired sessions."""
        # Create expired session
        expired = Session(
            session_id="sess_expired",
            user_id="user_123",
            token_hash="hash_expired",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            last_activity=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        await session_repo.create(expired)
        
        # Create valid session
        valid = Session(
            session_id="sess_valid",
            user_id="user_123",
            token_hash="hash_valid",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            last_activity=datetime.now(timezone.utc),
        )
        await session_repo.create(valid)
        
        count = await session_repo.delete_expired()
        assert count == 1
        
        # Expired should be gone
        assert await session_repo.get_by_token_hash("hash_expired") is None
        # Valid should remain
        assert await session_repo.get_by_token_hash("hash_valid") is not None


class TestSessionService:
    """Tests for SessionService."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_service, sample_user):
        """Can create session for user."""
        token, session = await session_service.create_session(sample_user)
        
        assert token is not None
        assert len(token) > 20  # Token should be substantial
        assert session.user_id == sample_user.user_id
        assert session.is_valid()
    
    @pytest.mark.asyncio
    async def test_validate_session(self, session_service, sample_user):
        """Can validate a session token."""
        token, _ = await session_service.create_session(sample_user)
        
        result = await session_service.validate_session(token)
        assert result is not None
        user, session = result
        assert user.user_id == sample_user.user_id
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, session_service):
        """Invalid token returns None."""
        result = await session_service.validate_session("invalid_token")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_invalidate_session(self, session_service, sample_user):
        """Can invalidate a session."""
        token, _ = await session_service.create_session(sample_user)
        
        # Should be valid initially
        assert await session_service.validate_session(token) is not None
        
        # Invalidate
        result = await session_service.invalidate_session(token)
        assert result is True
        
        # Should be invalid now
        assert await session_service.validate_session(token) is None
    
    @pytest.mark.asyncio
    async def test_invalidate_all_user_sessions(self, session_service, sample_user):
        """Can invalidate all sessions for a user."""
        # Create multiple sessions
        tokens = []
        for _ in range(3):
            token, _ = await session_service.create_session(sample_user)
            tokens.append(token)
        
        # Invalidate all
        count = await session_service.invalidate_all_user_sessions(sample_user.user_id)
        assert count == 3
        
        # All should be invalid
        for token in tokens:
            assert await session_service.validate_session(token) is None
    
    @pytest.mark.asyncio
    async def test_session_updates_last_activity(self, session_service, sample_user):
        """Validating session updates last activity."""
        token, session = await session_service.create_session(sample_user)
        original_activity = session.last_activity
        
        # Small delay
        import asyncio
        await asyncio.sleep(0.01)
        
        # Validate should update last activity
        result = await session_service.validate_session(token)
        _, updated_session = result
        
        assert updated_session.last_activity > original_activity
    
    @pytest.mark.asyncio
    async def test_inactive_user_session_invalid(self, session_service, sample_user, user_repo):
        """Session for inactive user is invalid."""
        token, _ = await session_service.create_session(sample_user)
        
        # Deactivate user
        sample_user.is_active = False
        await user_repo.update(sample_user)
        
        # Session should now be invalid
        result = await session_service.validate_session(token)
        assert result is None

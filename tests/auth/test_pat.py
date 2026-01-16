"""Tests for Personal Access Token service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from app.auth.models import User, PersonalAccessToken, AuthProvider
from app.auth.pat_service import (
    PATService,
    InMemoryPATRepository,
    generate_pat_token,
    hash_pat,
    get_token_display,
    get_key_id,
)


@pytest.fixture
def pat_repo():
    """Create fresh PAT repository."""
    return InMemoryPATRepository()


@pytest.fixture
def pat_service(pat_repo):
    """Create PAT service with 30-day default expiry."""
    return PATService(pat_repo, default_expiry=timedelta(days=30))


@pytest.fixture
def sample_user():
    """Create sample user."""
    return User(
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


class TestPATHelpers:
    """Tests for PAT helper functions."""
    
    def test_generate_pat_token_format(self):
        """Generated token has correct format."""
        token = generate_pat_token()
        assert token.startswith("pat_")
        assert len(token) > 20
    
    def test_hash_pat_deterministic(self):
        """Hashing same token gives same result."""
        token = "pat_test123"
        hash1 = hash_pat(token)
        hash2 = hash_pat(token)
        assert hash1 == hash2
    
    def test_hash_pat_different_tokens(self):
        """Different tokens give different hashes."""
        hash1 = hash_pat("pat_token1")
        hash2 = hash_pat("pat_token2")
        assert hash1 != hash2
    
    def test_get_token_display(self):
        """Token display shows first and last chars."""
        display = get_token_display("pat_abcdefghijk")
        assert "pat_abc" in display
        assert "..." in display
    
    def test_get_key_id(self):
        """Key ID is short identifier."""
        key_id = get_key_id("pat_abcdefghijk")
        assert len(key_id) == 12


class TestPATRepository:
    """Tests for InMemoryPATRepository."""
    
    @pytest.mark.asyncio
    async def test_create_pat(self, pat_repo):
        """Can create a PAT."""
        pat = PersonalAccessToken(
            token_id="pat_test",
            user_id="user_123",
            name="Test Token",
            token_hash="unique_hash",
            token_display="pat_abc...xyz",
            key_id="abc12345",
            created_at=datetime.now(timezone.utc),
        )
        created = await pat_repo.create(pat)
        assert created.token_id == "pat_test"
    
    @pytest.mark.asyncio
    async def test_get_by_hash(self, pat_repo):
        """Can retrieve PAT by hash."""
        pat = PersonalAccessToken(
            token_id="pat_test",
            user_id="user_123",
            name="Test Token",
            token_hash="unique_hash",
            token_display="pat_abc...xyz",
            key_id="abc12345",
            created_at=datetime.now(timezone.utc),
        )
        await pat_repo.create(pat)
        
        found = await pat_repo.get_by_hash("unique_hash")
        assert found is not None
        assert found.token_id == "pat_test"
    
    @pytest.mark.asyncio
    async def test_list_by_user(self, pat_repo):
        """Can list all PATs for a user."""
        for i in range(3):
            pat = PersonalAccessToken(
                token_id=f"pat_test_{i}",
                user_id="user_123",
                name=f"Token {i}",
                token_hash=f"hash_{i}",
                token_display=f"pat_...{i}",
                key_id=f"key_{i}",
                created_at=datetime.now(timezone.utc),
            )
            await pat_repo.create(pat)
        
        tokens = await pat_repo.list_by_user("user_123")
        assert len(tokens) == 3
    
    @pytest.mark.asyncio
    async def test_delete_pat(self, pat_repo):
        """Can delete a PAT."""
        pat = PersonalAccessToken(
            token_id="pat_delete",
            user_id="user_123",
            name="Delete Token",
            token_hash="hash_delete",
            token_display="pat_...del",
            key_id="del12345",
            created_at=datetime.now(timezone.utc),
        )
        await pat_repo.create(pat)
        
        result = await pat_repo.delete("pat_delete")
        assert result is True
        
        found = await pat_repo.get_by_hash("hash_delete")
        assert found is None


class TestPATService:
    """Tests for PATService."""
    
    @pytest.mark.asyncio
    async def test_create_token(self, pat_service, sample_user):
        """Can create a PAT for user."""
        token, pat = await pat_service.create_token(sample_user, "My API Key")
        
        assert token.startswith("pat_")
        assert pat.user_id == sample_user.user_id
        assert pat.name == "My API Key"
        assert pat.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_validate_token(self, pat_service, sample_user):
        """Can validate a created token."""
        token, pat = await pat_service.create_token(sample_user, "Test Key")
        
        validated = await pat_service.validate_token(token)
        assert validated is not None
        assert validated.token_id == pat.token_id
    
    @pytest.mark.asyncio
    async def test_validate_updates_last_used(self, pat_service, sample_user):
        """Validation updates last_used_at timestamp."""
        token, pat = await pat_service.create_token(sample_user, "Test Key")
        assert pat.last_used_at is None
        
        validated = await pat_service.validate_token(token)
        assert validated.last_used_at is not None
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, pat_service, sample_user):
        """Can revoke a token."""
        token, pat = await pat_service.create_token(sample_user, "Revoke Key")
        
        result = await pat_service.revoke_token(pat.token_id, sample_user.user_id)
        assert result is True
        
        validated = await pat_service.validate_token(token)
        assert validated is None
    
    @pytest.mark.asyncio
    async def test_revoke_wrong_user(self, pat_service, sample_user):
        """Cannot revoke another user's token."""
        token, pat = await pat_service.create_token(sample_user, "Test Key")
        
        result = await pat_service.revoke_token(pat.token_id, "different_user")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_user_tokens(self, pat_service, sample_user):
        """Can list user's tokens."""
        await pat_service.create_token(sample_user, "Key 1")
        await pat_service.create_token(sample_user, "Key 2")
        
        tokens = await pat_service.list_user_tokens(sample_user.user_id)
        assert len(tokens) == 2
    
    @pytest.mark.asyncio
    async def test_expired_token_invalid(self, pat_service, sample_user):
        """Expired token is not valid."""
        # Create with already-expired date
        token, pat = await pat_service.create_token(
            sample_user, 
            "Expired Key",
            expires_in=timedelta(seconds=-1)
        )
        
        validated = await pat_service.validate_token(token)
        assert validated is None
    
    @pytest.mark.asyncio
    async def test_delete_token(self, pat_service, sample_user):
        """Can delete a token."""
        token, pat = await pat_service.create_token(sample_user, "Delete Key")
        
        result = await pat_service.delete_token(pat.token_id, sample_user.user_id)
        assert result is True
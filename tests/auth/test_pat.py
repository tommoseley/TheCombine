"""Tests for Personal Access Token service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC

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
        created_at=datetime.now(UTC),
        last_login=datetime.now(UTC),
        is_active=True,
        roles=["operator"],
    )


class TestPATHelpers:
    """Tests for PAT helper functions."""
    
    def test_generate_pat_token_format(self):
        """Generated token has correct format."""
        token = generate_pat_token()
        assert token.startswith("pat_")
        assert len(token) > 40  # pat_ + base64 encoded bytes
    
    def test_generate_pat_token_unique(self):
        """Each generated token is unique."""
        tokens = [generate_pat_token() for _ in range(100)]
        assert len(set(tokens)) == 100
    
    def test_hash_pat_consistent(self):
        """Same token produces same hash."""
        token = "pat_test123"
        hash1 = hash_pat(token)
        hash2 = hash_pat(token)
        assert hash1 == hash2
    
    def test_hash_pat_different_tokens(self):
        """Different tokens produce different hashes."""
        hash1 = hash_pat("pat_token1")
        hash2 = hash_pat("pat_token2")
        assert hash1 != hash2
    
    def test_get_token_display(self):
        """Token display shows first and last chars."""
        token = "pat_abcdefghijklmnopqrstuvwxyz"
        display = get_token_display(token)
        assert display == "pat_abcd...wxyz"
    
    def test_get_key_id(self):
        """Key ID is consistent and short."""
        token = "pat_test123"
        key_id = get_key_id(token)
        assert len(key_id) == 12
        assert get_key_id(token) == key_id  # Consistent


class TestPATRepository:
    """Tests for InMemoryPATRepository."""
    
    @pytest.mark.asyncio
    async def test_create_pat(self, pat_repo):
        """Can create a PAT."""
        pat = PersonalAccessToken(
            token_id="pat_test",
            user_id="user_123",
            name="Test Token",
            token_hash="hash123",
            token_display="pat_...xyz",
            key_id="abc123",
            created_at=datetime.now(UTC),
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
            token_display="pat_...xyz",
            key_id="abc123",
            created_at=datetime.now(UTC),
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
                token_id=f"pat_{i}",
                user_id="user_123",
                name=f"Token {i}",
                token_hash=f"hash_{i}",
                token_display="pat_...xyz",
                key_id=f"key_{i}",
                created_at=datetime.now(UTC),
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
            name="Delete Me",
            token_hash="hash_delete",
            token_display="pat_...xyz",
            key_id="del123",
            created_at=datetime.now(UTC),
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
        assert pat.name == "My API Key"
        assert pat.user_id == sample_user.user_id
        assert pat.is_active is True
        assert pat.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_validate_token(self, pat_service, sample_user):
        """Can validate a created token."""
        token, _ = await pat_service.create_token(sample_user, "Test Key")
        
        validated = await pat_service.validate_token(token)
        assert validated is not None
        assert validated.name == "Test Key"
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, pat_service):
        """Invalid token returns None."""
        result = await pat_service.validate_token("pat_invalid_token")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_updates_last_used(self, pat_service, sample_user):
        """Validating token updates last_used_at."""
        token, pat = await pat_service.create_token(sample_user, "Test Key")
        assert pat.last_used_at is None
        
        validated = await pat_service.validate_token(token)
        assert validated.last_used_at is not None
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, pat_service, sample_user):
        """Can revoke a token."""
        token, pat = await pat_service.create_token(sample_user, "Revoke Me")
        
        result = await pat_service.revoke_token(pat.token_id, sample_user.user_id)
        assert result is True
        
        # Token should no longer validate
        validated = await pat_service.validate_token(token)
        assert validated is None
    
    @pytest.mark.asyncio
    async def test_revoke_wrong_user(self, pat_service, sample_user):
        """Cannot revoke another user's token."""
        _, pat = await pat_service.create_token(sample_user, "Protected")
        
        result = await pat_service.revoke_token(pat.token_id, "other_user")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_user_tokens(self, pat_service, sample_user):
        """Can list all user tokens."""
        for i in range(3):
            await pat_service.create_token(sample_user, f"Key {i}")
        
        tokens = await pat_service.list_user_tokens(sample_user.user_id)
        assert len(tokens) == 3
    
    @pytest.mark.asyncio
    async def test_expired_token_invalid(self, pat_repo, sample_user):
        """Expired token is not valid."""
        # Create service with immediate expiry
        service = PATService(pat_repo, default_expiry=timedelta(seconds=-1))
        
        token, _ = await service.create_token(sample_user, "Expired Key")
        
        validated = await service.validate_token(token)
        assert validated is None
    
    @pytest.mark.asyncio
    async def test_delete_token(self, pat_service, sample_user):
        """Can permanently delete a token."""
        token, pat = await pat_service.create_token(sample_user, "Delete Me")
        
        result = await pat_service.delete_token(pat.token_id, sample_user.user_id)
        assert result is True
        
        # Should be gone
        tokens = await pat_service.list_user_tokens(sample_user.user_id)
        assert len(tokens) == 0

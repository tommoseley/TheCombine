"""Tests for user model and repository."""

import pytest
from datetime import datetime, timezone

from app.auth import (
    User,
    AuthProvider,
    InMemoryUserRepository,
    UserAlreadyExistsError,
    UserNotFoundError,
)


@pytest.fixture
def user_repo():
    """Create fresh user repository."""
    return InMemoryUserRepository()


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


class TestUserModel:
    """Tests for User model."""
    
    def test_user_has_role(self, sample_user):
        """User can check for roles."""
        assert sample_user.has_role("operator") is True
        assert sample_user.has_role("admin") is False
    
    def test_admin_has_all_roles(self):
        """Admin role grants access to all roles."""
        user = User(
            user_id="admin_user",
            email="admin@example.com",
            name="Admin",
            provider=AuthProvider.LOCAL,
            provider_id="local_admin",
            user_created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
            roles=["admin"],
        )
        assert user.has_role("admin") is True
        assert user.has_role("operator") is True
        assert user.has_role("anything") is True
    
    def test_add_role(self, sample_user):
        """Can add roles to user."""
        sample_user.add_role("viewer")
        assert "viewer" in sample_user.roles
        assert len(sample_user.roles) == 2
    
    def test_add_duplicate_role(self, sample_user):
        """Adding duplicate role is idempotent."""
        sample_user.add_role("operator")
        assert sample_user.roles.count("operator") == 1
    
    def test_remove_role(self, sample_user):
        """Can remove roles from user."""
        sample_user.remove_role("operator")
        assert "operator" not in sample_user.roles


class TestUserRepository:
    """Tests for InMemoryUserRepository."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repo, sample_user):
        """Can create a user."""
        created = await user_repo.create(sample_user)
        assert created.user_id == sample_user.user_id
        assert created.email == sample_user.email
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user_id_fails(self, user_repo, sample_user):
        """Cannot create user with duplicate ID."""
        await user_repo.create(sample_user)
        
        duplicate = User(
            user_id=sample_user.user_id,  # Same ID
            email="other@example.com",
            name="Other",
            provider=AuthProvider.GOOGLE,
            provider_id="google_456",
            user_created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
        )
        
        with pytest.raises(UserAlreadyExistsError):
            await user_repo.create(duplicate)
    
    @pytest.mark.asyncio
    async def test_create_duplicate_email_fails(self, user_repo, sample_user):
        """Cannot create user with duplicate email."""
        await user_repo.create(sample_user)
        
        duplicate = User(
            user_id="user_different",
            email=sample_user.email,  # Same email
            name="Other",
            provider=AuthProvider.GOOGLE,
            provider_id="google_456",
            user_created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
        )
        
        with pytest.raises(UserAlreadyExistsError):
            await user_repo.create(duplicate)
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repo, sample_user):
        """Can get user by ID."""
        await user_repo.create(sample_user)
        found = await user_repo.get_by_id(sample_user.user_id)
        assert found is not None
        assert found.email == sample_user.email
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repo):
        """Returns None for unknown ID."""
        found = await user_repo.get_by_id("nonexistent")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repo, sample_user):
        """Can get user by email."""
        await user_repo.create(sample_user)
        found = await user_repo.get_by_email(sample_user.email)
        assert found is not None
        assert found.user_id == sample_user.user_id
    
    @pytest.mark.asyncio
    async def test_get_by_provider(self, user_repo, sample_user):
        """Can get user by provider."""
        await user_repo.create(sample_user)
        found = await user_repo.get_by_provider(
            AuthProvider.GOOGLE, sample_user.provider_id
        )
        assert found is not None
        assert found.user_id == sample_user.user_id
    
    @pytest.mark.asyncio
    async def test_update_user(self, user_repo, sample_user):
        """Can update user."""
        await user_repo.create(sample_user)
        sample_user.name = "Updated Name"
        updated = await user_repo.update(sample_user)
        assert updated.name == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_fails(self, user_repo, sample_user):
        """Cannot update nonexistent user."""
        with pytest.raises(UserNotFoundError):
            await user_repo.update(sample_user)
    
    @pytest.mark.asyncio
    async def test_list_all(self, user_repo, sample_user):
        """Can list all users."""
        await user_repo.create(sample_user)
        
        user2 = User(
            user_id="user_second",
            email="second@example.com",
            name="Second User",
            provider=AuthProvider.MICROSOFT,
            provider_id="ms_123",
            user_created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
        )
        await user_repo.create(user2)
        
        all_users = await user_repo.list_all()
        assert len(all_users) == 2

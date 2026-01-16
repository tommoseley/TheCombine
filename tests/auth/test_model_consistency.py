"""Tests for auth model and service consistency."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.auth.models import User, UserSession


class TestUserModelConstruction:
    """Ensure User model can be constructed with ORM field names."""
    
    def test_user_from_orm_fields(self):
        """User can be constructed with ORM-style fields."""
        # These are the exact fields the service passes from ORM
        user = User(
            user_id=str(uuid4()),
            email="test@example.com",
            email_verified=True,
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            is_active=True,
            user_created_at=datetime.now(timezone.utc),
            user_updated_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
        )
        
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.is_active is True
    
    def test_user_minimal_fields(self):
        """User can be constructed with minimal required fields."""
        user = User(
            user_id=str(uuid4()),
            email="minimal@example.com",
            name="Minimal User",
        )
        
        assert user.email == "minimal@example.com"
        assert user.is_active is True  # default
        assert user.roles == []  # default
    
    def test_user_has_role_method(self):
        """User.has_role works correctly."""
        user = User(
            user_id=str(uuid4()),
            email="test@example.com",
            name="Test",
            roles=["editor"],
        )
        
        assert user.has_role("editor") is True
        assert user.has_role("admin") is False


class TestUserSessionModelConstruction:
    """Ensure UserSession model can be constructed with ORM field names."""
    
    def test_session_from_orm_fields(self):
        """UserSession can be constructed with ORM-style fields."""
        now = datetime.now(timezone.utc)
        
        # These are the exact fields the service passes from ORM
        session = UserSession(
            session_id=uuid4(),
            user_id=uuid4(),
            session_token="test_token_abc123",
            csrf_token="csrf_token_xyz789",
            ip_address="127.0.0.1",
            user_agent="TestBrowser/1.0",
            session_created_at=now,
            last_activity_at=now,
            expires_at=now,
        )
        
        assert session.session_token == "test_token_abc123"
        assert session.csrf_token == "csrf_token_xyz789"
    
    def test_session_is_expired(self):
        """UserSession.is_expired works correctly."""
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        
        # Expired session
        expired = UserSession(
            session_id=uuid4(),
            user_id=uuid4(),
            session_token="token",
            csrf_token="csrf",
            session_created_at=now - timedelta(days=31),
            last_activity_at=now - timedelta(days=31),
            expires_at=now - timedelta(days=1),
        )
        assert expired.is_expired() is True
        
        # Valid session
        valid = UserSession(
            session_id=uuid4(),
            user_id=uuid4(),
            session_token="token",
            csrf_token="csrf",
            session_created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(days=30),
        )
        assert valid.is_expired() is False
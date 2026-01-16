"""Tests for AuthContext usage in routes."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.auth.models import AuthContext, User, AuthProvider


class TestAuthContextAccess:
    """Ensure AuthContext is accessed correctly."""
    
    def test_auth_context_user_id_access(self):
        """AuthContext.user.user_id is the correct way to get user_id."""
        user = User(
            user_id=str(uuid4()),
            email="test@example.com",
            name="Test User",
            user_created_at=datetime.now(timezone.utc),
        )
        
        auth_context = AuthContext(
            user=user,
            session_id=uuid4(),
            csrf_token="test_csrf",
        )
        
        # Correct access pattern
        assert auth_context.user.user_id == user.user_id
        assert auth_context.user.email == "test@example.com"
        assert auth_context.user.name == "Test User"
        
        # AuthContext does NOT have user_id directly
        assert not hasattr(auth_context, 'user_id')
    
    def test_auth_context_session_properties(self):
        """AuthContext session properties work correctly."""
        user = User(
            user_id=str(uuid4()),
            email="test@example.com",
            name="Test",
        )
        
        # Session auth
        session_ctx = AuthContext(
            user=user,
            session_id=uuid4(),
            csrf_token="csrf",
        )
        assert session_ctx.is_session_auth is True
        assert session_ctx.is_token_auth is False
        
        # Token auth
        token_ctx = AuthContext(
            user=user,
            token_id=uuid4(),
        )
        assert token_ctx.is_session_auth is False
        assert token_ctx.is_token_auth is True
    
    def test_auth_context_with_minimal_user(self):
        """AuthContext works with minimal user fields."""
        user = User(
            user_id="minimal_user",
            email="minimal@test.com",
            name="Minimal",
        )
        
        ctx = AuthContext(user=user)
        
        assert ctx.user.user_id == "minimal_user"
        assert ctx.session_id is None
        assert ctx.token_id is None
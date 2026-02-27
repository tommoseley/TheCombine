"""Tests for authentication middleware."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.auth.models import User, AuthContext, AuthProvider
from app.auth.permissions import Permission
from app.auth.middleware import (
    require_auth,
    require_permission,
    require_any_permission,
)


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


@pytest.fixture
def admin_user():
    """Create admin user."""
    return User(
        user_id="user_admin",
        email="admin@example.com",
        name="Admin User",
        provider=AuthProvider.LOCAL,
        provider_id="local_admin",
        user_created_at=datetime.now(timezone.utc),
        last_login_at=datetime.now(timezone.utc),
        is_active=True,
        roles=["admin"],
    )


@pytest.fixture
def viewer_user():
    """Create viewer user."""
    return User(
        user_id="user_viewer",
        email="viewer@example.com",
        name="Viewer User",
        provider=AuthProvider.LOCAL,
        provider_id="local_viewer",
        user_created_at=datetime.now(timezone.utc),
        last_login_at=datetime.now(timezone.utc),
        is_active=True,
        roles=["viewer"],
    )


class MockState:
    """Mock state object that properly handles auth_context."""
    def __init__(self, auth_context=None):
        self._auth_context = auth_context
        self._has_auth = auth_context is not None
    
    @property
    def auth_context(self):
        if not self._has_auth:
            raise AttributeError("auth_context")
        return self._auth_context


def create_mock_request(auth_context=None):
    """Create a mock request with optional auth context."""
    request = MagicMock()
    if auth_context is not None:
        request.state = MagicMock()
        request.state.auth_context = auth_context
    else:
        # Create state without auth_context attribute
        state = MagicMock(spec=[])  # Empty spec means no attributes
        del state.auth_context  # Ensure hasattr returns False
        request.state = state
    return request


class TestRequireAuth:
    """Tests for require_auth decorator."""
    
    @pytest.mark.asyncio
    async def test_authenticated_request_passes(self, sample_user):
        """Authenticated request passes through."""
        auth_context = AuthContext(user=sample_user)
        
        @require_auth
        async def protected_route(request):
            return {"status": "ok"}
        
        request = create_mock_request(auth_context)
        result = await protected_route(request)
        assert result == {"status": "ok"}
    
    @pytest.mark.asyncio
    async def test_unauthenticated_request_fails(self):
        """Unauthenticated request raises 401."""
        @require_auth
        async def protected_route(request):
            return {"status": "ok"}
        
        request = create_mock_request(None)
        
        with pytest.raises(HTTPException) as exc_info:
            await protected_route(request)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail


class TestRequirePermission:
    """Tests for require_permission decorator."""
    
    @pytest.mark.asyncio
    async def test_user_with_permission_passes(self, sample_user):
        """User with required permission passes."""
        auth_context = AuthContext(user=sample_user)
        
        @require_permission(Permission.WORKFLOW_EXECUTE)
        async def execute_route(request):
            return {"status": "executed"}
        
        request = create_mock_request(auth_context)
        result = await execute_route(request)
        assert result == {"status": "executed"}
    
    @pytest.mark.asyncio
    async def test_user_without_permission_fails(self, viewer_user):
        """User without required permission gets 403."""
        auth_context = AuthContext(user=viewer_user)
        
        @require_permission(Permission.WORKFLOW_EXECUTE)
        async def execute_route(request):
            return {"status": "executed"}
        
        request = create_mock_request(auth_context)
        
        with pytest.raises(HTTPException) as exc_info:
            await execute_route(request)
        
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self, admin_user):
        """Admin user passes all permission checks."""
        auth_context = AuthContext(user=admin_user)
        
        @require_permission(Permission.USER_MANAGE)
        async def admin_route(request):
            return {"status": "admin"}
        
        request = create_mock_request(auth_context)
        result = await admin_route(request)
        assert result == {"status": "admin"}
    
    @pytest.mark.asyncio
    async def test_unauthenticated_fails_with_401(self):
        """Unauthenticated request fails with 401 not 403."""
        @require_permission(Permission.ADMIN)
        async def admin_route(request):
            return {"status": "admin"}
        
        request = create_mock_request(None)
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_route(request)
        
        assert exc_info.value.status_code == 401


class TestRequireAnyPermission:
    """Tests for require_any_permission decorator."""
    
    @pytest.mark.asyncio
    async def test_user_with_one_permission_passes(self, sample_user):
        """User with any required permission passes."""
        auth_context = AuthContext(user=sample_user)
        
        @require_any_permission([Permission.WORKFLOW_EXECUTE, Permission.ADMIN])
        async def flex_route(request):
            return {"status": "ok"}
        
        request = create_mock_request(auth_context)
        result = await flex_route(request)
        assert result == {"status": "ok"}
    
    @pytest.mark.asyncio
    async def test_user_with_no_permissions_fails(self, viewer_user):
        """User without any required permission gets 403."""
        auth_context = AuthContext(user=viewer_user)
        
        @require_any_permission([Permission.WORKFLOW_EXECUTE, Permission.ADMIN])
        async def flex_route(request):
            return {"status": "ok"}
        
        request = create_mock_request(auth_context)
        
        with pytest.raises(HTTPException) as exc_info:
            await flex_route(request)
        
        assert exc_info.value.status_code == 403

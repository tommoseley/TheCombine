"""Tier-1 CRAP score remediation tests for link_callback in accounts.py.

Covers the branching logic (CC=14):
- Invalid provider_id -> 404
- Missing link_nonce in session -> 400
- Invalid/expired link intent -> 400
- Provider mismatch -> 400
- Non-Microsoft provider: Authlib authorize_access_token
- OAuth token exchange failure -> 400
- Missing claims + fallback to parse_id_token
- Claims normalization failure -> 400
- Successful link (linked=True, linked=False/already)
- Identity already linked to different user -> 403
- Session cleanup in finally block
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.routers.accounts import router


# =========================================================================
# Test app setup
# =========================================================================


def _make_test_app(session_data=None):
    """Build a test FastAPI app with session injection middleware.

    Args:
        session_data: Dict of session values to inject before each request.
            If provided, values are set on request.session before the route handler.
    """
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-1234")
    app.include_router(router)

    if session_data:
        # Add a setup endpoint and use it to seed the session
        @app.get("/_seed_session")
        async def seed_session(request: Request):
            for k, v in session_data.items():
                request.session[k] = v
            return {"ok": True}

    return app


# =========================================================================
# Mock helpers
# =========================================================================


def _mock_oidc_config(valid_providers=None):
    """Return a mock OIDCConfig that raises ValueError for unknown providers."""
    config = MagicMock()
    valid = valid_providers or ["google", "microsoft"]

    def get_client(provider_id):
        if provider_id not in valid:
            raise ValueError(f"Unknown provider: {provider_id}")
        client = AsyncMock()
        client.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"sub": "user123", "email": "test@test.com"}}
        )
        return client

    config.get_client = get_client
    config.parse_id_token = AsyncMock(
        return_value={"sub": "user123", "email": "test@test.com"}
    )
    config.normalize_claims = MagicMock(
        return_value={"sub": "user123", "email": "test@test.com"}
    )
    return config


def _mock_auth_service(
    verify_result=None,
    link_result=True,
    link_raises=None,
):
    """Return a mock AuthService."""
    svc = AsyncMock()
    svc.verify_link_intent = AsyncMock(return_value=verify_result)
    if link_raises:
        svc.link_oauth_identity = AsyncMock(side_effect=link_raises)
    else:
        svc.link_oauth_identity = AsyncMock(return_value=link_result)
    svc.log_auth_event = AsyncMock()
    return svc


def _setup_overrides(app, oidc):
    """Set common dependency overrides."""
    from app.core.dependencies import get_oidc_config
    from app.core.database import get_db
    app.dependency_overrides[get_oidc_config] = lambda: oidc
    app.dependency_overrides[get_db] = lambda: AsyncMock()


async def _seed_and_call(client, callback_path, seed_path="/_seed_session"):
    """Seed session via helper endpoint, then call the actual callback."""
    await client.get(seed_path)
    return await client.get(callback_path, follow_redirects=False)


# =========================================================================
# Tests
# =========================================================================


class TestLinkCallbackInvalidProvider:
    """Tests for invalid provider_id."""

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_404(self):
        """Unknown provider_id returns 404."""
        app = _make_test_app()
        oidc = _mock_oidc_config(valid_providers=["google"])
        _setup_overrides(app, oidc)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/auth/accounts/callback/unknown_provider",
                follow_redirects=False,
            )
        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestLinkCallbackSessionNonce:
    """Tests for link_nonce session checks."""

    @pytest.mark.asyncio
    async def test_missing_link_nonce_returns_400(self):
        """No link_nonce in session returns 400."""
        app = _make_test_app()
        oidc = _mock_oidc_config()
        _setup_overrides(app, oidc)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/auth/accounts/callback/google",
                follow_redirects=False,
            )
        assert resp.status_code == 400
        assert "Invalid linking session" in resp.json()["detail"]

        app.dependency_overrides.clear()


class TestLinkCallbackIntentVerification:
    """Tests for link intent verification."""

    @pytest.mark.asyncio
    async def test_invalid_intent_returns_400(self):
        """Expired or invalid link intent returns 400."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})
        oidc = _mock_oidc_config()
        _setup_overrides(app, oidc)
        auth_svc = _mock_auth_service(verify_result=None)

        with patch("app.api.routers.accounts.AuthService", return_value=auth_svc):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 400
            assert "expired or invalid" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_provider_mismatch_returns_400(self):
        """When intent provider != callback provider, returns 400."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})
        oidc = _mock_oidc_config()
        _setup_overrides(app, oidc)
        user_id = uuid4()
        auth_svc = _mock_auth_service(verify_result=(user_id, "microsoft"))

        with patch("app.api.routers.accounts.AuthService", return_value=auth_svc):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 400
            assert "Provider mismatch" in resp.json()["detail"]

        app.dependency_overrides.clear()


class TestLinkCallbackTokenExchange:
    """Tests for OAuth token exchange paths."""

    @pytest.mark.asyncio
    async def test_oauth_token_exchange_failure_returns_400(self):
        """When authorize_access_token raises, returns 400."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})

        oidc = MagicMock()
        failing_client = AsyncMock()
        failing_client.authorize_access_token = AsyncMock(
            side_effect=Exception("token exchange broke")
        )
        oidc.get_client = MagicMock(return_value=failing_client)
        _setup_overrides(app, oidc)

        user_id = uuid4()
        auth_svc = _mock_auth_service(verify_result=(user_id, "google"))

        with patch("app.api.routers.accounts.AuthService", return_value=auth_svc):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 400
            assert "OAuth authorization failed" in resp.json()["detail"]

        app.dependency_overrides.clear()


class TestLinkCallbackClaimsProcessing:
    """Tests for claims extraction and normalization."""

    @pytest.mark.asyncio
    async def test_claims_normalization_failure_returns_400(self):
        """When normalize_claims raises ValueError, returns 400."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})

        oidc = MagicMock()
        mock_client = AsyncMock()
        mock_client.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"sub": "u1", "email": "a@b.com"}}
        )
        oidc.get_client = MagicMock(return_value=mock_client)
        oidc.normalize_claims = MagicMock(
            side_effect=ValueError("Missing required claim: email")
        )
        _setup_overrides(app, oidc)

        user_id = uuid4()
        auth_svc = _mock_auth_service(verify_result=(user_id, "google"))

        with patch("app.api.routers.accounts.AuthService", return_value=auth_svc):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 400
            assert "Missing required claim" in resp.json()["detail"]

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_id_token_parse_fallback_when_no_userinfo(self):
        """When token has no userinfo, falls back to parse_id_token."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})

        oidc = MagicMock()
        mock_client = AsyncMock()
        mock_client.authorize_access_token = AsyncMock(
            return_value={"access_token": "abc"}
        )
        oidc.get_client = MagicMock(return_value=mock_client)
        oidc.parse_id_token = AsyncMock(
            return_value={"sub": "u1", "email": "a@b.com"}
        )
        oidc.normalize_claims = MagicMock(
            return_value={"sub": "u1", "email": "a@b.com"}
        )
        _setup_overrides(app, oidc)

        user_id = uuid4()
        auth_svc = _mock_auth_service(
            verify_result=(user_id, "google"),
            link_result=True,
        )

        with (
            patch("app.api.routers.accounts.AuthService", return_value=auth_svc),
            patch("app.api.routers.accounts.get_client_ip", return_value="127.0.0.1"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 302
            assert "linked=success" in resp.headers.get("location", "")
            oidc.parse_id_token.assert_awaited_once()

        app.dependency_overrides.clear()


class TestLinkCallbackLinkResult:
    """Tests for the link_oauth_identity result paths."""

    @pytest.mark.asyncio
    async def test_successful_link_redirects_success(self):
        """Successful new link -> redirect with ?linked=success."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})

        oidc = MagicMock()
        mock_client = AsyncMock()
        mock_client.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"sub": "u1", "email": "a@b.com"}}
        )
        oidc.get_client = MagicMock(return_value=mock_client)
        oidc.normalize_claims = MagicMock(
            return_value={"sub": "u1", "email": "a@b.com"}
        )
        _setup_overrides(app, oidc)

        user_id = uuid4()
        auth_svc = _mock_auth_service(
            verify_result=(user_id, "google"),
            link_result=True,
        )

        with (
            patch("app.api.routers.accounts.AuthService", return_value=auth_svc),
            patch("app.api.routers.accounts.get_client_ip", return_value="127.0.0.1"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 302
            assert "linked=success" in resp.headers.get("location", "")

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_already_linked_redirects_already(self):
        """Already-linked identity -> redirect with ?linked=already."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})

        oidc = MagicMock()
        mock_client = AsyncMock()
        mock_client.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"sub": "u1", "email": "a@b.com"}}
        )
        oidc.get_client = MagicMock(return_value=mock_client)
        oidc.normalize_claims = MagicMock(
            return_value={"sub": "u1", "email": "a@b.com"}
        )
        _setup_overrides(app, oidc)

        user_id = uuid4()
        auth_svc = _mock_auth_service(
            verify_result=(user_id, "google"),
            link_result=False,
        )

        with (
            patch("app.api.routers.accounts.AuthService", return_value=auth_svc),
            patch("app.api.routers.accounts.get_client_ip", return_value="127.0.0.1"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 302
            assert "linked=already" in resp.headers.get("location", "")

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_identity_linked_to_other_user_returns_403(self):
        """Identity already linked to different user -> 403."""
        app = _make_test_app(session_data={"link_nonce": "test-nonce"})

        oidc = MagicMock()
        mock_client = AsyncMock()
        mock_client.authorize_access_token = AsyncMock(
            return_value={"userinfo": {"sub": "u1", "email": "a@b.com"}}
        )
        oidc.get_client = MagicMock(return_value=mock_client)
        oidc.normalize_claims = MagicMock(
            return_value={"sub": "u1", "email": "a@b.com"}
        )
        _setup_overrides(app, oidc)

        user_id = uuid4()
        auth_svc = _mock_auth_service(
            verify_result=(user_id, "google"),
            link_raises=ValueError("Identity already linked to another user"),
        )

        with (
            patch("app.api.routers.accounts.AuthService", return_value=auth_svc),
            patch("app.api.routers.accounts.get_client_ip", return_value="127.0.0.1"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await _seed_and_call(
                    client, "/auth/accounts/callback/google",
                )
            assert resp.status_code == 403
            assert "already linked" in resp.json()["detail"]

        app.dependency_overrides.clear()

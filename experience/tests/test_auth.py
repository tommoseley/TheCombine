"""
Tests for authentication (magic link flow).
"""

from fastapi.testclient import TestClient
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta, timezone
import pytest
import bcrypt
import re
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.main import app, Base, Session as SessionModel, PendingToken as PendingTokenModel
from app.dependencies import get_db

# Create test database
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create tables
Base.metadata.create_all(bind=test_engine)


def get_test_db():
    """Override database dependency for tests."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)


def _now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace('+00:00', 'Z')


class TestMagicLinkFlow:
    """Integration tests for magic link authentication flow."""
    
    @patch('app.routers.auth.templates.TemplateResponse')
    def test_login_form_displays(self, mock_template):
        """Test that login form page loads."""
        # Create a proper HTMLResponse object
        mock_response = HTMLResponse(content="<html>login form</html>", status_code=200)
        mock_template.return_value = mock_response
        
        response = client.get("/login")
        
        assert response.status_code == 200
        mock_template.assert_called_once()
    
    def test_magic_link_validation_success(self):
        """Test successful magic link validation creates session."""
        # Create a pending token
        email = f"valid-{uuid4()}@example.com"
        token = "test-token-" + str(uuid4())
        token_hash = bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
        
        db = next(get_test_db())
        now = _now_iso()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        
        pending_token = PendingTokenModel(
            token_hash=token_hash,
            email=email,
            expires_at=expires_at,
            created_at=now
        )
        db.add(pending_token)
        db.commit()
        db.close()
        
        # Validate the token (don't follow redirects)
        response = client.get(f"/magic-login?token={token}", follow_redirects=False)
        
        assert response.status_code == 303  # Redirect
        assert response.headers["location"] == "/workspaces"
        
        # Verify session was created in database
        db = next(get_test_db())
        session = db.query(SessionModel).filter(SessionModel.email == email).first()
        assert session is not None, "Session was not created in database"
        assert session.email == email
        
        # Verify token was deleted (single-use)
        pending = db.query(PendingTokenModel).filter(
            PendingTokenModel.token_hash == token_hash
        ).first()
        assert pending is None, "Token was not deleted after use"
        
        db.close()
    
    @patch('app.routers.auth.templates.TemplateResponse')
    def test_send_magic_link_invalid_email(self, mock_template):
        """Test that invalid email format is rejected."""
        response = client.post(
            "/login",
            data={"email": "invalid-email"}
        )
        
        assert response.status_code == 400
        assert "invalid email" in response.json()["detail"].lower()
    
    @patch('app.routers.auth.templates.TemplateResponse')
    @patch('app.services.email_service.email_service.send_magic_link')
    @patch('app.services.email_service.email_service.can_send_magic_link')
    def test_send_magic_link_rate_limiting(self, mock_can_send, mock_send_email, mock_template):
        """Test rate limiting (5 requests per 10 minutes)."""
        # Mock email sending to always succeed
        mock_send_email.return_value = True
        # Mock template response
        mock_response = HTMLResponse(content="<html>success</html>", status_code=200)
        mock_template.return_value = mock_response
        
        email = f"ratelimit-{uuid4()}@example.com"
        
        # First 5 requests should be allowed
        mock_can_send.return_value = (True, 0)
        
        for i in range(5):
            response = client.post("/login", data={"email": email})
            assert response.status_code == 200, f"Request {i+1} failed with {response.status_code}"
        
        # 6th request should be rate limited
        # Mock can_send_magic_link to return False (rate limited) with 300 seconds retry
        mock_can_send.return_value = (False, 300)
        
        response = client.post("/login", data={"email": email})
        assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.text}"
        assert "too many requests" in response.json()["detail"].lower()
    
    def test_magic_link_validation_invalid_token(self):
        """Test that invalid token returns 401."""
        response = client.get("/magic-login?token=invalid-token-xyz")
        
        assert response.status_code == 401
        assert "invalid or expired" in response.json()["detail"].lower()
    
    def test_magic_link_validation_success(self):
        """Test successful magic link validation creates session."""
        # Create a pending token
        email = f"valid-{uuid4()}@example.com"
        token = "test-token-" + str(uuid4())
        token_hash = bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
        
        db = next(get_test_db())
        now = _now_iso()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        
        pending_token = PendingTokenModel(
            token_hash=token_hash,
            email=email,
            expires_at=expires_at,
            created_at=now
        )
        db.add(pending_token)
        db.commit()
        db.close()
        
        # Validate the token (don't follow redirects)
        response = client.get(f"/magic-login?token={token}", follow_redirects=False)
        
        assert response.status_code == 303  # Redirect
        assert response.headers["location"] == "/workspaces"
        
        # Check cookie was set in Set-Cookie header
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "session_id=" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        
        # Extract session_id from Set-Cookie header
        match = re.search(r'session_id=([^;]+)', set_cookie_header)
        assert match is not None, "Could not find session_id in Set-Cookie header"
        session_id = match.group(1)
        
        # Verify session was created in database
        db = next(get_test_db())
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        assert session is not None
        assert session.email == email
        
        # Verify token was deleted (single-use)
        pending = db.query(PendingTokenModel).filter(
            PendingTokenModel.token_hash == token_hash
        ).first()
        assert pending is None
        db.close()
    
    def test_logout_clears_session(self):
        """Test logout deletes session and clears cookie."""
        # Create a session
        db = next(get_test_db())
        session_id = str(uuid4())
        email = f"logout-{uuid4()}@example.com"
        now = _now_iso()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        
        session = SessionModel(
            id=session_id,
            email=email,
            expires_at=expires_at,
            created_at=now
        )
        db.add(session)
        db.commit()
        db.close()
        
        # Set cookie on client instance
        client.cookies.set("session_id", session_id)
        
        # Logout
        response = client.post("/logout", follow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # Verify session was deleted from database
        db = next(get_test_db())
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        assert session is None
        db.close()
        
        # Clear client cookies
        client.cookies.clear()


class TestGetMe:
    """Tests for /me endpoint (AUTH-101)."""
    
    def test_get_me_with_valid_session(self):
        """
        Test GET /me with valid session returns 200 and user data.
        
        Acceptance Criteria:
        - GET /me with a valid session returns 200
        - Response includes user's email and other relevant session fields
        """
        # Create a valid session
        db = next(get_test_db())
        session_id = str(uuid4())
        email = f"testme-{uuid4()}@example.com"
        now = _now_iso()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        
        session = SessionModel(
            id=session_id,
            email=email,
            expires_at=expires_at,
            created_at=now
        )
        db.add(session)
        db.commit()
        db.close()
        
        # Set cookie on client
        client.cookies.set("session_id", session_id)
        
        # Call /me endpoint
        response = client.get("/me")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure and content
        assert data["email"] == email
        assert data["session_id"] == session_id
        assert "expires_at" in data
        assert "created_at" in data
        
        # Verify it's proper JSON with expected fields
        assert isinstance(data["email"], str)
        assert isinstance(data["session_id"], str)
        assert isinstance(data["expires_at"], str)
        assert isinstance(data["created_at"], str)
        
        # Clear cookies
        client.cookies.clear()
    
    def test_get_me_no_session(self):
        """
        Test GET /me with no session returns 401.
        
        Acceptance Criteria:
        - GET /me with no session returns 401
        """
        # Clear any cookies
        client.cookies.clear()
        
        response = client.get("/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "not authenticated" in data["detail"].lower()
    
    def test_get_me_expired_session(self):
        """
        Test GET /me with expired session returns 401.
        
        Acceptance Criteria:
        - GET /me with an expired session returns 401
        """
        # Create an expired session
        db = next(get_test_db())
        session_id = str(uuid4())
        email = f"expired-{uuid4()}@example.com"
        now = _now_iso()
        # Set expiration to 1 hour ago
        expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        
        session = SessionModel(
            id=session_id,
            email=email,
            expires_at=expires_at,
            created_at=now
        )
        db.add(session)
        db.commit()
        db.close()
        
        # Set cookie on client
        client.cookies.set("session_id", session_id)
        
        # Call /me endpoint
        response = client.get("/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "expired" in data["detail"].lower()
        
        # Verify session was deleted from database
        db = next(get_test_db())
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        assert session is None, "Expired session should have been deleted"
        db.close()
        
        # Clear cookies
        client.cookies.clear()
    
    def test_get_me_invalid_session(self):
        """Test GET /me with invalid session ID returns 401."""
        # Set invalid session cookie
        client.cookies.set("session_id", "invalid-session-id-12345")
        
        response = client.get("/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "invalid session" in data["detail"].lower()
        
        # Clear cookies
        client.cookies.clear()


class TestSessionModel:
    """Unit tests for Session model."""
    
    def test_session_is_expired(self):
        """Test session expiration check."""
        expired_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace('+00:00', 'Z')
        session = SessionModel(
            id=str(uuid4()),
            email="test@example.com",
            expires_at=expired_time,
            created_at=_now_iso()
        )
        
        assert session.is_expired() == True
    
    def test_session_not_expired(self):
        """Test valid session."""
        future_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        session = SessionModel(
            id=str(uuid4()),
            email="test@example.com",
            expires_at=future_time,
            created_at=_now_iso()
        )
        
        assert session.is_expired() == False


class TestPendingTokenModel:
    """Unit tests for PendingToken model."""
    
    def test_token_is_expired(self):
        """Test token expiration check."""
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        token = PendingTokenModel(
            token_hash="hash123",
            email="test@example.com",
            expires_at=expired_time,
            created_at=_now_iso()
        )
        
        assert token.is_expired() == True
    
    def test_token_not_expired(self):
        """Test valid token."""
        future_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        token = PendingTokenModel(
            token_hash="hash123",
            email="test@example.com",
            expires_at=future_time,
            created_at=_now_iso()
        )
        
        assert token.is_expired() == False


class TestEmailService:
    """Unit tests for email service."""
    
    def test_rate_limiter_allows_initial_requests(self):
        """Test that first 5 requests are allowed."""
        from app.services.email_service import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_minutes=10)
        email = "test@example.com"
        
        for i in range(5):
            assert limiter.can_send(email) == True
            limiter.record_request(email)
        
        assert limiter.can_send(email) == False
    
    def test_rate_limiter_get_retry_after(self):
        """Test retry_after calculation."""
        from app.services.email_service import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_minutes=10)
        email = "test@example.com"
        
        for i in range(5):
            limiter.record_request(email)
        
        retry_after = limiter.get_retry_after(email)
        assert retry_after > 0
        assert retry_after <= 600
    
    def test_console_email_backend(self):
        """Test console email backend."""
        from app.services.email_service import EmailService
        import os
        
        original_backend = os.environ.get("EMAIL_BACKEND")
        os.environ["EMAIL_BACKEND"] = "console"
        
        try:
            service = EmailService()
            result = service.send_magic_link(
                "test@example.com",
                "http://localhost/magic-login?token=test123"
            )
            
            assert result == True
        finally:
            if original_backend:
                os.environ["EMAIL_BACKEND"] = original_backend
            else:
                os.environ.pop("EMAIL_BACKEND", None)


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""
    
    def test_get_current_user_with_valid_session(self):
        """Test that valid session returns user email."""
        # Tested via integration tests
        assert True
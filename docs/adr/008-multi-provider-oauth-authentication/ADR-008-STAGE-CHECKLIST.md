# ADR-008 Implementation Stage Checklist

**Purpose:** Track progress through authentication implementation with clear verification steps at each stage.

**How to use:** Check off items as completed. Run verification commands before marking stage complete.

---

## Stage 0: Database Foundation
**Goal:** Auth tables exist and are queryable

### Tasks
- [ ] Create Alembic migration file: `alembic revision -m "create_auth_tables"`
- [ ] Write UP migration: All 6 tables (users, user_oauth_identities, link_intent_nonces, user_sessions, personal_access_tokens, auth_audit_log)
- [ ] Write DOWN migration: Drop all tables in reverse order
- [ ] Add indexes: session_token (unique), user_id, expires_at, token_id
- [ ] Add constraints: users.email unique, (provider_id, provider_user_id) unique

### Verification
```bash
# Run migration
alembic upgrade head

# Verify tables exist
psql $DATABASE_URL -c "\dt"
# Should show: users, user_oauth_identities, link_intent_nonces, user_sessions, personal_access_tokens, auth_audit_log

# Verify indexes
psql $DATABASE_URL -c "\di"
# Should show: idx_session_token, idx_users_email, idx_pat_token_id, etc.

# Verify constraints
psql $DATABASE_URL -c "\d users"
# Should show: users_email_unique constraint

# Test rollback
alembic downgrade -1
alembic upgrade head
```

### Done Criteria
- [ ] All 6 tables exist
- [ ] All indexes created
- [ ] Unique constraints enforced (test: insert duplicate email fails)
- [ ] Rollback works (downgrade then upgrade succeeds)
- [ ] Columns are `TIMESTAMP WITH TIME ZONE` (not plain TIMESTAMP)

---

## Stage 1: Core Models & Utilities
**Goal:** Python types exist, imports work

### Tasks
- [ ] Create `src/auth/__init__.py`
- [ ] Create `src/auth/models.py`:
  - [ ] OIDCProvider enum (GOOGLE, MICROSOFT)
  - [ ] AuthEventType enum (LOGIN_SUCCESS, CSRF_VIOLATION, etc.)
  - [ ] User dataclass
  - [ ] UserSession dataclass
  - [ ] PersonalAccessToken dataclass
  - [ ] AuthContext dataclass
- [ ] Create `src/auth/utils.py`:
  - [ ] utcnow() function
- [ ] Create `src/auth/rate_limits.py`:
  - [ ] RateLimitPolicy dataclass
  - [ ] RATE_LIMITS dict
- [ ] Create `src/middleware/__init__.py`
- [ ] Create `src/middleware/rate_limit.py` (stub with get_client_ip only)

### Verification
```python
# In Python REPL or test file
from src.auth.models import User, AuthContext, OIDCProvider, AuthEventType
from src.auth.utils import utcnow
from src.auth.rate_limits import RATE_LIMITS
from src.middleware.rate_limit import get_client_ip

# Test enum
assert OIDCProvider.GOOGLE == "google"
assert AuthEventType.LOGIN_SUCCESS == "login_success"

# Test utcnow
now = utcnow()
assert now.tzinfo is not None  # Timezone-aware

# Test rate limits
assert 'auth_login_redirect' in RATE_LIMITS
assert RATE_LIMITS['auth_login_redirect'].requests == 30
```

### Done Criteria
- [ ] All imports succeed without errors
- [ ] Enums have correct string values
- [ ] utcnow() returns timezone-aware datetime
- [ ] RATE_LIMITS dict has all 8 policies
- [ ] get_client_ip() exists (implementation can be minimal)

---

## Stage 2: OIDC Configuration
**Goal:** Can create OAuth clients for Google/Microsoft

### Tasks
- [ ] Create `src/auth/oidc_config.py`:
  - [ ] OIDCConfig class
  - [ ] Register Google (server_metadata_url, PKCE S256)
  - [ ] Register Microsoft (server_metadata_url, PKCE S256)
  - [ ] parse_id_token() method (passes request to Authlib)
  - [ ] normalize_claims() method (handles Microsoft fallbacks)
- [ ] Update `src/dependencies.py`:
  - [ ] Add get_oidc_config() dependency
- [ ] Update `src/main.py`:
  - [ ] Add SessionMiddleware (REQUIRED for Authlib)

### Verification
```python
# Test OIDC config
from src.auth.oidc_config import OIDCConfig
import os

os.environ['GOOGLE_CLIENT_ID'] = 'test'
os.environ['GOOGLE_CLIENT_SECRET'] = 'test'

config = OIDCConfig()
assert 'google' in config.providers

client = config.get_client('google')
assert client is not None

# Test normalize_claims (Microsoft without email)
claims = {
    'sub': '12345',
    'name': 'Test User',
    'preferred_username': 'test@example.com'
}
normalized = config.normalize_claims('microsoft', claims)
assert normalized['email'] == 'test@example.com'
assert normalized['email_verified'] == False
```

### Done Criteria
- [ ] SessionMiddleware added to FastAPI app
- [ ] GOOGLE_CLIENT_ID/SECRET registers Google OAuth client
- [ ] MICROSOFT_CLIENT_ID/SECRET registers Microsoft OAuth client
- [ ] parse_id_token() accepts (request, token) - passes request to Authlib
- [ ] normalize_claims() handles Microsoft preferred_username fallback
- [ ] normalize_claims() raises ValueError if no email-like claim

---

## Stage 3A: Auth Service (Sessions + Audit)
**Goal:** Can create/verify sessions, log events

### Tasks
- [ ] Create `src/auth/service.py`:
  - [ ] AuthService class (takes async DB session)
  - [ ] create_session() - generates session_token + csrf_token
  - [ ] verify_session() - returns (User, session_id, csrf_token)
  - [ ] get_or_create_user_from_oidc() - handles email collisions
  - [ ] log_auth_event() - with 1000/min circuit breaker
- [ ] Add circuit breaker logic:
  - [ ] Track events in 1-minute window (in-memory or Redis)
  - [ ] Stop writing after 1000 events

### Verification
```python
# Unit test
from src.auth.service import AuthService
from src.auth.models import AuthEventType

service = AuthService(db_session)

# Create session
user = await create_test_user(email='test@example.com')
session = await service.create_session(user.user_id, '1.2.3.4', 'test-agent')

assert len(session.session_token) == 43  # URL-safe base64
assert len(session.csrf_token) == 43

# Verify session
result = await service.verify_session(session.session_token)
assert result is not None
user, session_id, csrf_token = result
assert user.email == 'test@example.com'

# Test circuit breaker (should stop at ~1000)
for i in range(1500):
    await service.log_auth_event(AuthEventType.CSRF_VIOLATION, ip_address='1.2.3.4')

count = await db_session.execute("SELECT COUNT(*) FROM auth_audit_log")
assert count <= 1100
```

### Done Criteria
- [ ] create_session() inserts row in user_sessions
- [ ] verify_session() returns correct User + csrf_token
- [ ] verify_session() does NOT update last_activity_at if <15min (write throttling)
- [ ] get_or_create_user_from_oidc() creates user on first login
- [ ] get_or_create_user_from_oidc() blocks if email exists unverified
- [ ] log_auth_event() circuit breaker stops at 1000 events/min
- [ ] All methods use utcnow() for timestamps

---

## Stage 4: Login/Logout Routes (No Linking Yet)
**Goal:** Can login with Google/Microsoft, get session cookie, logout

### Tasks
- [ ] Create `src/auth/routes.py`:
  - [ ] APIRouter with prefix="/auth"
  - [ ] GET /auth/login/{provider_id} - redirects to OAuth
  - [ ] GET /auth/callback/{provider_id} - exchanges code, creates session
  - [ ] POST /auth/logout - clears session and cookies
  - [ ] validate_origin() helper function
- [ ] Update `src/main.py`:
  - [ ] Include auth router: app.include_router(auth_routes.router)

### Verification
```bash
# Start app
uvicorn src.main:app --reload

# Test login redirect
curl -I http://localhost:8000/auth/login/google
# Should: 302 redirect to accounts.google.com

# Manual OAuth flow (or use integration test with mocked OIDC)
# After callback, should set cookies

# Test logout
curl -X POST http://localhost:8000/auth/logout \
  -H "Cookie: session=xxx" \
  -H "X-CSRF-Token: xxx"
# Should: 200, cookies cleared (max-age=0)
```

### Done Criteria
- [ ] GET /auth/login/google returns 302 to Google OAuth
- [ ] GET /auth/login/microsoft returns 302 to Microsoft OAuth
- [ ] GET /auth/callback/google sets session cookie (name: `session` in dev, `__Host-session` in prod)
- [ ] GET /auth/callback/google sets CSRF cookie (name: `csrf` in dev, `__Host-csrf` in prod)
- [ ] Session cookie: HttpOnly=true, Secure=true (prod), SameSite=lax, Path=/
- [ ] CSRF cookie: HttpOnly=false, Secure=true (prod), SameSite=lax, Path=/
- [ ] POST /auth/logout requires CSRF token (403 without it)
- [ ] POST /auth/logout requires Origin header when cookies present (403 without it)
- [ ] POST /auth/logout clears both cookies with matching Path=/

---

## Stage 5: Auth Middleware (Session Only)
**Goal:** Protected endpoints require authentication

### Tasks
- [ ] Create `src/auth/middleware.py`:
  - [ ] get_current_user() dependency
  - [ ] Try session cookie first
  - [ ] Return AuthContext(user, session_id, None, csrf_token)
  - [ ] Raise HTTPException(401) if no valid session
- [ ] Update `src/dependencies.py`:
  - [ ] Import and expose get_current_user

### Verification
```python
# Integration test
from fastapi import Depends
from src.auth.middleware import get_current_user

@app.get("/protected")
async def protected_route(auth: AuthContext = Depends(get_current_user)):
    return {"user_id": str(auth.user_id)}

# Test without auth
response = client.get("/protected")
assert response.status_code == 401

# Test with valid session
response = client.get("/protected", cookies={"session": valid_session_token})
assert response.status_code == 200
assert "user_id" in response.json()
```

### Done Criteria
- [ ] get_current_user() returns AuthContext when valid session cookie present
- [ ] get_current_user() raises 401 when no session cookie
- [ ] get_current_user() raises 401 when session expired
- [ ] AuthContext.csrf_token is populated from session
- [ ] Protected endpoint (with Depends(get_current_user)) requires auth

---

## Stage 6: Environment & Config
**Goal:** All secrets generated, environment validated

### Tasks
- [ ] Create `.env.template` with all variables
- [ ] Create `src/config.py` (Pydantic Settings)
- [ ] Add validation: PAT_SERVER_KEYS required in production
- [ ] Add validation: At least one OAuth provider required
- [ ] Create `scripts/generate_secrets.py`

### Verification
```bash
# Generate secrets
python scripts/generate_secrets.py
# Output:
# SESSION_SECRET_KEY=abc123...
# PAT_SERVER_KEYS=primary:def456...,secondary:ghi789...

# Copy to .env
cat .env.template > .env
# Edit .env with real values

# Test config loading
python -c "from src.config import Settings; s = Settings(); print(s.ENV)"

# Test validation (should fail in production without PAT_SERVER_KEYS)
ENV=production python -c "from src.config import Settings; Settings()"
# Should raise ValidationError
```

### Done Criteria
- [ ] .env.template has all required variables with comments
- [ ] generate_secrets.py outputs SESSION_SECRET_KEY (64-char hex)
- [ ] generate_secrets.py outputs PAT_SERVER_KEYS (two keys)
- [ ] Settings validates PAT_SERVER_KEYS in production
- [ ] Settings validates at least one OAuth provider set
- [ ] Settings.TRUST_PROXY defaults to False
- [ ] Settings.ALLOWED_ORIGINS is parsed as list

---

## Stage 7: Docker Compose & Nginx
**Goal:** Can deploy locally with rate limiting

### Tasks
- [ ] Create `docker-compose.yml`:
  - [ ] Service: app (FastAPI)
  - [ ] Service: postgres
  - [ ] Service: nginx
  - [ ] Service: redis (optional)
- [ ] Create `deploy/nginx/nginx.conf`
- [ ] Create `deploy/nginx/combine-rate-limits.conf`:
  - [ ] Rate limit zones (auth_login, auth_callback, auth_link, global_burst)
  - [ ] Proxy headers (X-Real-IP, X-Forwarded-For)
- [ ] Create Dockerfile (if not exists)

### Verification
```bash
# Start all services
docker-compose up -d

# Check services running
docker-compose ps
# Should show: app, postgres, nginx (all "Up")

# Test Nginx forwarding
curl -I http://localhost/auth/login/google
# Should: 302 redirect (proxied through Nginx)

# Test rate limiting (31 requests to same endpoint)
for i in {1..31}; do
  curl -I http://localhost/auth/login/google
done
# First 30: 302
# 31st: 429 Too Many Requests

# Test proxy headers
docker-compose logs app | grep "X-Real-IP"
# Should show: Real client IP in logs (not 172.x.x.x)
```

### Done Criteria
- [ ] docker-compose up starts all services without errors
- [ ] Nginx proxies to app on http://app:8000
- [ ] Nginx sets X-Real-IP header
- [ ] Nginx sets X-Forwarded-For header
- [ ] Nginx rate limit returns 429 after 30 req/min to /auth/login/*
- [ ] Health check: curl http://localhost/health returns 200
- [ ] Postgres health check passes
- [ ] App can connect to Postgres through Docker network

---

## Stage 8: Rate Limiting Implementation
**Goal:** App-level rate limiting works with Redis

### Tasks
- [ ] Complete `src/middleware/rate_limit.py`:
  - [ ] RateLimiter class with Redis sorted sets
  - [ ] make_rate_limit_dependency() factory
  - [ ] make_rate_limit_dependency_with_user() factory
  - [ ] DummyRateLimiter (fail-open)
  - [ ] get_client_ip() respects TRUST_PROXY
- [ ] Update `src/main.py`:
  - [ ] Initialize RateLimiter if REDIS_URL set
  - [ ] Initialize DummyRateLimiter if REDIS_URL unset
- [ ] Update routes to use rate limit dependencies

### Verification
```python
# Test with Redis
import os
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['TRUST_PROXY'] = 'true'

# Start app
# Make 31 requests to /auth/login/google with X-Forwarded-For header
for i in range(31):
    response = client.get(
        '/auth/login/google',
        headers={'X-Forwarded-For': '1.2.3.4, 10.0.0.1'}
    )
    if i < 30:
        assert response.status_code == 302
    else:
        assert response.status_code == 429
        assert 'Retry-After' in response.headers

# Test without Redis (fail-open)
os.environ.pop('REDIS_URL')
# Restart app
# Make 100 requests - should all succeed (no app-level limiting)

# Test TRUST_PROXY=false
os.environ['TRUST_PROXY'] = 'false'
# Spoofed X-Forwarded-For should be ignored
```

### Done Criteria
- [ ] RateLimiter uses Redis ZADD/ZREMRANGEBYSCORE (sliding window)
- [ ] DummyRateLimiter always returns (True, None)
- [ ] app.state.rate_limiter exists
- [ ] Rate limit dependencies work (return 429 after threshold)
- [ ] get_client_ip() returns X-Forwarded-For leftmost when TRUST_PROXY=true
- [ ] get_client_ip() returns request.client.host when TRUST_PROXY=false
- [ ] Rate limit includes Retry-After header

---

## Stage 9: First Milestone - End-to-End Test
**Goal:** Complete login flow works in Docker environment

### Manual Test Checklist
```bash
# 1. Start environment
docker-compose up -d

# 2. Open browser to http://localhost

# 3. Click "Login with Google"
# Expected: Redirect to Google OAuth consent screen

# 4. Approve consent
# Expected: Redirect back to http://localhost/auth/callback/google

# 5. Check cookies in browser DevTools
# Expected: Two cookies set:
#   - session (or __Host-session in prod)
#   - csrf (or __Host-csrf in prod)

# 6. Navigate to protected page
# Expected: Page loads (authenticated)

# 7. Logout
# Expected: Cookies cleared, redirect to login

# 8. Try accessing protected page
# Expected: 401 Unauthorized
```

### Verification Script
```python
# tests/integration/test_first_milestone.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_complete_login_flow(app, mock_oidc):
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Initiate login
        response = await client.get("/auth/login/google", follow_redirects=False)
        assert response.status_code == 302
        assert "accounts.google.com" in response.headers["location"]
        
        # Mock callback (in real test, mock OIDC token exchange)
        # This would normally come from Google
        mock_code = "test_auth_code"
        
        response = await client.get(
            f"/auth/callback/google?code={mock_code}&state=test_state"
        )
        assert response.status_code == 302  # Redirect to home
        assert "session" in response.cookies
        assert "csrf" in response.cookies
        
        # Access protected endpoint
        session_cookie = response.cookies["session"]
        csrf_token = response.cookies["csrf"]
        
        response = await client.get(
            "/protected",
            cookies={"session": session_cookie}
        )
        assert response.status_code == 200
        
        # Logout
        response = await client.post(
            "/auth/logout",
            cookies={"session": session_cookie, "csrf": csrf_token},
            headers={"X-CSRF-Token": csrf_token}
        )
        assert response.status_code == 200
        
        # Verify cookies cleared
        assert response.cookies["session"].value == ""
        assert response.cookies["csrf"].value == ""
```

### Done Criteria
- [ ] Can login with Google in browser (real OAuth flow)
- [ ] Can login with Microsoft in browser (real OAuth flow)
- [ ] Session cookie set with correct flags
- [ ] CSRF cookie set with HttpOnly=false
- [ ] Protected endpoint accessible after login
- [ ] Logout clears cookies correctly
- [ ] Cannot access protected endpoint after logout
- [ ] Rate limits trigger at correct thresholds (Nginx + Redis)
- [ ] Audit log shows LOGIN_SUCCESS event
- [ ] User record created in database

---

## Stage 10: Unit Tests
**Goal:** Core logic has test coverage

### Tasks
- [ ] Create `tests/unit/test_auth_service.py`:
  - [ ] test_create_session
  - [ ] test_verify_session
  - [ ] test_verify_session_write_throttling
  - [ ] test_log_auth_event_circuit_breaker
  - [ ] test_get_or_create_user_blocks_email_collision
- [ ] Create `tests/unit/test_rate_limit.py`:
  - [ ] test_get_client_ip_trust_proxy_true
  - [ ] test_get_client_ip_trust_proxy_false
  - [ ] test_rate_limiter_sliding_window
  - [ ] test_dummy_rate_limiter_fail_open
- [ ] Create `tests/unit/test_oidc_config.py`:
  - [ ] test_normalize_claims_google
  - [ ] test_normalize_claims_microsoft_fallback
  - [ ] test_normalize_claims_microsoft_blocks_no_email

### Verification
```bash
# Run unit tests
pytest tests/unit/ -v

# Check coverage
pytest tests/unit/ --cov=src.auth --cov-report=term-missing
# Target: >90% coverage for auth module
```

### Done Criteria
- [ ] All unit tests pass
- [ ] test_verify_session_write_throttling: Verify no DB write if <15min
- [ ] test_log_auth_event_circuit_breaker: Verify max 1100 rows after 1500 events
- [ ] test_get_client_ip_trust_proxy_false: Verify X-Forwarded-For ignored
- [ ] test_rate_limiter_sliding_window: Verify 31st request returns (False, retry_after)
- [ ] test_normalize_claims_microsoft_blocks_no_email: Verify ValueError raised
- [ ] Code coverage >90% for src/auth/ module

---

## Stage 11: Integration Tests - Security
**Goal:** All security mechanisms verified

### Tasks
- [ ] Create `tests/integration/test_csrf_protection.py`:
  - [ ] test_logout_requires_csrf_token
  - [ ] test_logout_requires_origin_header
  - [ ] test_origin_validated_against_allowlist
- [ ] Create `tests/integration/test_rate_limiting.py`:
  - [ ] test_login_rate_limit_30_per_min
  - [ ] test_nginx_rate_limit_enforced
- [ ] Create `tests/integration/test_proxy_detection.py`:
  - [ ] test_rate_limit_uses_real_ip_behind_proxy
  - [ ] test_audit_log_uses_real_ip
  - [ ] test_x_forwarded_for_ignored_when_trust_proxy_false

### Verification
```bash
# Run integration tests
pytest tests/integration/ -v

# Specific security tests
pytest tests/integration/test_csrf_protection.py -v
pytest tests/integration/test_rate_limiting.py -v
```

### Done Criteria
- [ ] All integration tests pass
- [ ] test_logout_requires_csrf_token: POST without X-CSRF-Token → 403
- [ ] test_logout_requires_origin_header: POST with cookies but no Origin → 403
- [ ] test_login_rate_limit_30_per_min: 31st request → 429
- [ ] test_rate_limit_uses_real_ip_behind_proxy: Separate IPs tracked separately
- [ ] test_x_forwarded_for_ignored_when_trust_proxy_false: Spoofed header ignored

---

## Stage 12: Documentation
**Goal:** Operators can deploy and troubleshoot

### Tasks
- [ ] Create `docs/AUTH_SETUP.md`:
  - [ ] Google OAuth app creation (with screenshots)
  - [ ] Microsoft OAuth app creation (with screenshots)
  - [ ] Redirect URI configuration
- [ ] Create `docs/DEPLOYMENT.md`:
  - [ ] Docker Compose setup
  - [ ] Nginx configuration
  - [ ] Environment variables
  - [ ] Verification steps
- [ ] Create `docs/TROUBLESHOOTING.md`:
  - [ ] TRUST_PROXY misconfiguration
  - [ ] Rate limit 429 errors
  - [ ] Redis unavailable
  - [ ] OAuth errors
- [ ] Update `README.md`:
  - [ ] Add "Authentication" section
  - [ ] Link to setup docs

### Verification
```bash
# Follow deployment guide from scratch
# Start with fresh VM/container
# Follow docs/DEPLOYMENT.md step-by-step
# Verify: Can login successfully at end

# Test troubleshooting guide
# Intentionally misconfigure TRUST_PROXY
# Follow docs/TROUBLESHOOTING.md
# Verify: Guide identifies and fixes issue
```

### Done Criteria
- [ ] docs/AUTH_SETUP.md has screenshots for OAuth app creation
- [ ] docs/DEPLOYMENT.md has complete setup steps
- [ ] docs/DEPLOYMENT.md has verification curl commands
- [ ] docs/TROUBLESHOOTING.md covers common issues
- [ ] README.md links to auth documentation
- [ ] New developer can follow docs and deploy successfully

---

## Stage 13: Pre-Production Checklist
**Goal:** Ready for production deployment

### Security Checklist
- [ ] No plain SQL queries (all parameterized)
- [ ] All state-changing endpoints require CSRF token
- [ ] All cookie-authenticated endpoints validate Origin
- [ ] Session cookies use __Host- prefix in production
- [ ] CSRF cookies have HttpOnly=false (readable by JS)
- [ ] Logout clears cookies with matching Path=/
- [ ] TRUST_PROXY defaults to false
- [ ] PAT_SERVER_KEYS validated at startup
- [ ] Audit log circuit breaker implemented
- [ ] Rate limits active (Nginx + Redis)

### Performance Checklist
- [ ] Session verification <10ms (benchmark test passes)
- [ ] Session write throttling reduces DB writes by 90%
- [ ] All database indexes created
- [ ] Connection pooling configured
- [ ] Background task (link nonce cleanup) runs every 5min

### Operational Checklist
- [ ] Health check endpoint returns 200
- [ ] Logs include request IDs for tracing
- [ ] Audit log captures all auth events
- [ ] Monitoring alerts configured:
  - [ ] Auth error rate >1%
  - [ ] CSRF violations >10/hour
  - [ ] Rate limit 429s >100/min
  - [ ] Redis unavailable
- [ ] Documentation complete
- [ ] Rollback plan documented

### Test Checklist
- [ ] All unit tests pass (>90% coverage)
- [ ] All integration tests pass
- [ ] Performance benchmarks meet targets
- [ ] Security tests verify all protections
- [ ] Load test: 1000 req/min for 10 minutes (no errors)

### Verification Commands
```bash
# Security
grep -r "execute\|fetchall\|fetchone" src/ | grep -v "parameterized"  # Should be empty
grep -r "f\"SELECT\|f'SELECT" src/  # Should be empty (no f-string SQL)

# Performance
pytest tests/performance/test_benchmarks.py
# Session verify: <10ms p99
# PAT verify: <1ms p99

# Health
curl http://localhost/health
# {"status":"ok","database":"connected"}

# Rate limits
for i in {1..35}; do curl -I http://localhost/auth/login/google; sleep 2; done
# Should see 429 on requests 31-35

# Audit log
psql $DATABASE_URL -c "SELECT COUNT(*) FROM auth_audit_log WHERE created_at > NOW() - INTERVAL '1 hour'"
# Should have login events from testing
```

### Done Criteria
- [ ] All security checklist items verified
- [ ] All performance benchmarks pass
- [ ] All operational items configured
- [ ] All tests pass (unit + integration + performance)
- [ ] Documentation reviewed and accurate
- [ ] Staging deployment successful
- [ ] Load test passes (1000 req/min for 10 min)
- [ ] Rollback procedure tested

---

## Stage 14: Production Deployment
**Goal:** Auth live in production

### Pre-Deployment
- [ ] Create production database backup
- [ ] Generate production secrets (not dev secrets!)
- [ ] Configure OAuth apps with production redirect URIs
- [ ] Review environment variables in production
- [ ] Verify TRUST_PROXY=true (assuming behind Nginx)
- [ ] Verify HTTPS_ONLY=true
- [ ] Verify Nginx rate limit config deployed

### Deployment Steps
```bash
# 1. Run database migration
alembic upgrade head

# 2. Deploy application
docker-compose -f docker-compose.prod.yml up -d

# 3. Deploy Nginx configuration
sudo cp deploy/nginx/combine-rate-limits.conf /etc/nginx/conf.d/
sudo nginx -t
sudo nginx -s reload

# 4. Verify services running
docker-compose ps
curl https://your-domain.com/health
```

### Smoke Tests (Production)
```bash
# 1. Health check
curl https://your-domain.com/health
# Expected: 200 {"status":"ok"}

# 2. Login redirect
curl -I https://your-domain.com/auth/login/google
# Expected: 302 to accounts.google.com

# 3. Complete login flow (manual in browser)
# Expected: Can login, get session, access protected page

# 4. Rate limit
for i in {1..35}; do curl -I https://your-domain.com/auth/login/google; sleep 2; done
# Expected: 429 after 30 requests

# 5. Logout
# Expected: Cookies cleared, can't access protected page
```

### Post-Deployment (First 4 Hours)
- [ ] Monitor error logs: `docker-compose logs -f app | grep ERROR`
- [ ] Monitor auth events: `psql -c "SELECT event_type, COUNT(*) FROM auth_audit_log WHERE created_at > NOW() - INTERVAL '1 hour' GROUP BY event_type"`
- [ ] Monitor rate limit 429s: `tail -f /var/log/nginx/access.log | grep " 429 "`
- [ ] Monitor Redis: `redis-cli INFO stats`
- [ ] Verify login works for real users
- [ ] Check for CSRF violations (should be 0)
- [ ] Check for Origin violations (should be 0)

### Success Criteria
- [ ] No ERROR or CRITICAL logs in first hour
- [ ] Auth success rate >99%
- [ ] Login response time <500ms p95
- [ ] Rate limits working (some 429s expected)
- [ ] Audit log capturing events
- [ ] Real users can login successfully
- [ ] No production incidents

---

## Rollback Procedure (If Needed)

### Triggers for Rollback
- Auth error rate >5% for >10 minutes
- Database migration fails
- Cannot login (OAuth broken)
- Rate limits causing widespread 429s for legitimate users
- Critical security issue discovered

### Rollback Steps
```bash
# 1. Rollback application
docker-compose down
git checkout <previous-commit>
docker-compose up -d

# 2. Rollback Nginx config
git checkout HEAD~1 deploy/nginx/combine-rate-limits.conf
sudo cp deploy/nginx/combine-rate-limits.conf /etc/nginx/conf.d/
sudo nginx -s reload

# 3. Rollback database (if schema changed)
alembic downgrade -1

# 4. Verify rollback successful
curl https://your-domain.com/health
# Test login flow

# 5. Post-rollback
# Incident report: What failed and why
# Plan fix for next deployment
```

---

## Monitoring Dashboard (Ongoing)

### Key Metrics to Watch

**Auth Success Rate:**
```sql
SELECT 
  DATE_TRUNC('hour', created_at) AS hour,
  event_type,
  COUNT(*) 
FROM auth_audit_log 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour, event_type
ORDER BY hour DESC;
```

**Rate Limit Violations:**
```bash
# Nginx
grep " 429 " /var/log/nginx/access.log | wc -l

# Redis
redis-cli KEYS "rate_limit:*" | wc -l
```

**Session Count:**
```sql
SELECT COUNT(*) FROM user_sessions WHERE expires_at > NOW();
```

**Active Users (last 24h):**
```sql
SELECT COUNT(DISTINCT user_id) FROM user_sessions 
WHERE last_activity_at > NOW() - INTERVAL '24 hours';
```

### Alert Thresholds
- **CRITICAL:** Auth error rate >1% for >5 minutes
- **CRITICAL:** Database unreachable
- **WARNING:** CSRF violations >10/hour
- **WARNING:** Rate limit 429s >100/min
- **WARNING:** Redis unavailable (MVP+)
- **INFO:** New user registrations

---

**End of Stage Checklist**

Use this checklist to track progress. Check off each item as completed. Run verification commands before marking stages complete. This ensures steady progress toward production-ready authentication.

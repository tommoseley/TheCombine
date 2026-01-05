# Phase 11: Shake-Down Testing

**Objective:** Local user testing before staging deployment

**Started:** 2026-01-04

---

## Issues Found

### FIXED

| # | Issue | Root Cause | Fix | Test Added |
|---|-------|-----------|-----|------------|
| 1 | `User.__init__() got unexpected keyword argument 'user_created_at'` | Domain model `User` had different field names than ORM (`created_at` vs `user_created_at`) | Updated `app/auth/models.py` to match ORM field names | `tests/auth/test_model_consistency.py` |
| 2 | `UserSession.__init__()` field mismatch | Domain model had `token_hash` instead of `session_token`/`csrf_token` | Updated `UserSession` in `app/auth/models.py` | `tests/auth/test_model_consistency.py` |
| 3 | `'AuthContext' object has no attribute 'user_id'` | Route accessed `auth_context.user_id` instead of `auth_context.user.user_id` | Fixed `app/api/routers/protected.py` | `tests/auth/test_auth_context.py` |
| 4 | Routes 404: `/workflows`, `/executions`, `/dashboard/costs` | Routers in `app/api/v1/` and `app/ui/routers/` never wired to `main.py` | Wired up in `main.py` | `tests/api/test_route_availability.py` (16 tests) |
| 5 | TemplateResponse deprecation warning | Old syntax `TemplateResponse(name, {"request": request})` | Updated all routes to `TemplateResponse(request, name, {})` | Warning eliminated |
| 6 | Dashboard nav link went to `/` | Menu link pointed to home instead of dashboard | Changed to `/dashboard`, created dashboard index page | `test_dashboard_index` |
| 7 | Garbled nav icons (encoding issue) | Emoji chars corrupted by PowerShell | Switched to Lucide icon library (project standard) | Visual verification |

### TECH DEBT (Deferred)

| # | Issue | Description | Priority |
|---|-------|-------------|----------|
| ~~1~~ | ~~TemplateResponse deprecation~~ | ~~Fixed - updated all routes~~ | ~~Done~~ |
| 2 | asyncpg coroutine warning in tests | `coroutine 'Connection._cancel' was never awaited` - test infrastructure issue | Low |

---

## Test Results

- **Starting tests:** 921
- **Current tests:** 943
- **Tests added this phase:** 6+ (model consistency, auth context, route availability)

---

## Endpoints Verified

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Home page |
| `GET /health` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Liveness |
| `GET /health/ready` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Readiness |
| `GET /health/detailed` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Full diagnostics |
| `GET /docs` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Swagger UI |
| `GET /projects` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Project list |
| `GET /api/documents/types` | ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ | Document types |
| `GET /workflows` | ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€šÃ‚Â§ | Fixing - not wired |
| `GET /executions` | ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€šÃ‚Â§ | Fixing - not wired |
| `GET /dashboard/costs` | ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€šÃ‚Â§ | Fixing - not wired |

---

## Log

### 2026-01-04

1. Started local testing with `.\run.ps1`
2. Found User model mismatch - fixed
3. Found UserSession model mismatch - fixed  
4. Found AuthContext access pattern error - fixed
5. Found missing route wiring - fixing now
## Authentication Fixes (Issue 8)

### Microsoft OAuth - Multiple Issues Fixed

**Problem:** Microsoft OAuth login returning "Missing jwks_uri in metadata" error

**Root Cause:** Authlib was trying to auto-parse ID tokens which requires OIDC metadata that Microsoft's pure OAuth2 setup doesn't provide properly.

**Solution:** Manual token exchange for Microsoft to bypass Authlib's ID token parsing:
- Added explicit `httpx` POST to Microsoft's token endpoint
- Session state key format: `_state_microsoft_{state_value}` (not `_state_microsoft_`)
- Added `redirect_uri` to token exchange request

**Files Modified:**
- `app/auth/routes.py` - Manual Microsoft token exchange in callback
- `app/auth/oidc_config.py` - Microsoft OAuth2 configuration
- `app/auth/models.py` - Added missing `AuthEventType` values:
  - `LOGIN_BLOCKED_EMAIL_EXISTS`
  - `CSRF_VIOLATION`

### Account Linking Redirect Fix

**Problem:** After linking accounts, redirect went to JSON API endpoint instead of HTML page

**Solution:** Changed redirect from `/auth/accounts?linked=success` to `/static/accounts.html?linked=success`

**File Modified:** `app/api/routers/accounts.py`

### Azure AD Configuration Required

Two redirect URIs must be registered in Azure AD:
1. `http://localhost:8000/auth/callback/microsoft` (login)
2. `http://localhost:8000/auth/accounts/callback/microsoft` (account linking)

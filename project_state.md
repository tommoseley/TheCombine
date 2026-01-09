# The Combine - Project State

**Last Updated:** 2026-01-07
**Last Session:** Production OAuth Fix

## Current Status

### Production Environment
- **URL:** https://www.thecombine.ai (ALB redirects non-www → www)
- **Status:** ✅ Fully operational
- **OAuth:** Google and Microsoft working
- **Database:** PostgreSQL on RDS
- **Deployment:** ECS Fargate via GitHub Actions

### Authentication System
- Multi-provider OAuth (Google, Microsoft) - ✅ Working
- Account linking/unlinking - ✅ Implemented
- Session management - ✅ Database-backed user sessions
- Audit logging - ✅ auth_audit_log table
- CSRF protection - ✅ Token-based

### Infrastructure
- **Task Definition:** the-combine-task:22
- **DOMAIN:** www.thecombine.ai
- **HTTPS_ONLY:** true
- **ALB:** Redirect rule for non-www → www

## Recent Changes (2026-01-07)

### Fixed
- OAuth cookie domain mismatch (www vs non-www)
- Missing AuthEventType enums
- Logout audit log missing user_id
- Account linking redirect URLs
- Duplicate accounts.py removed

### Added
- ALB redirect rule: thecombine.ai → www.thecombine.ai
- AUTH-MANUAL-TEST-PLAN.md (v1.3)
- prompt='select_account' for OAuth flows

## Architecture

### Completed ADRs
- ADR-033: Data-Only Experience Contracts - Accepted
- ADR-034: Document Composition Manifest - Accepted with Amendment A

### Database Schema
- users, user_sessions, user_oauth_identities, auth_audit_log
- link_intent_nonces (for account linking flow)
- personal_access_tokens (for API auth)

## Next Steps

### Immediate
1. Complete auth test plan in production (Phases 2-11)
2. PR development → main
3. Implement ADR-034 Document Composition Manifest

### Backlog
- Database-backed session storage (for multi-task scaling)
- User-friendly auth error pages
- Reference document management (ADR-028, ADR-029)

## Key Files

### Auth
- `app/auth/routes.py` - OAuth login/logout flows
- `app/auth/service.py` - Auth business logic
- `app/auth/models.py` - Domain models, AuthEventType enum
- `app/api/routers/accounts.py` - Account linking endpoints

### Config
- `app/api/main.py` - FastAPI app, SessionMiddleware config
- `Dockerfile` - Includes --proxy-headers for ALB

### Ops
- `ops/aws/taskdef-www.json` - Current task definition template
- `ops/testing/AUTH-MANUAL-TEST-PLAN.md` - Manual test checklist

## Branch Status
- `development` - Current working branch
- `main` - Production (needs PR from development)

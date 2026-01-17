# The Combine - Project State

**Last Updated:** 2026-01-16
**Last Session:** Seed Data Management & Environment Tooling

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

## Recent Changes (2026-01-16)

### Fixed
- Python 3.10 compatibility: `datetime.UTC` → `timezone.utc` across 34 files
- UTF-8 encoding corruption in fragment seeds (`â†'` → `&rarr;`, `âœ"` → `&check;`)
- Database UTF-8 client_encoding added to connection

### Added
- `seed/registry/` - Relocated seed files from `app/domain/registry/seed_*.py`
  - `component_artifacts.py` - Components + document definitions
  - `fragment_artifacts.py` - HTML fragment templates
  - `schema_artifacts.py` - JSON schemas
  - `document_types.py` - Document type configurations
- `ops/db/seed_data_from_backup.sql` - Extracted seed data with DELETE + COPY
- `ops/db/restore_documents.sql` - Document restoration from backup

### Developer Tooling (Shell Aliases)
Add to `~/.bashrc`:
```bash
# Database environment switching
alias use-dev-db='export DATABASE_URL="postgresql://..."'
alias use-prod-db='export DATABASE_URL="postgresql://..."'

# Start web app
alias combine-start='cd ~/dev/TheCombine && PYTHONPATH=. python3 ops/scripts/run.py'
```

### Seeding Commands
```bash
# Seed registry tables (schema_artifacts, fragment_artifacts, component_artifacts, document_definitions, document_types)
psql "$DATABASE_URL" -f ops/db/seed_data_from_backup.sql

# Or run individual Python seeders
python3 -m seed.registry.schema_artifacts
python3 -m seed.registry.fragment_artifacts
python3 -m seed.registry.component_artifacts
python3 -m seed.registry.document_types
```

## Previous Changes (2026-01-07)

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

### Seed Data
- `seed/registry/schema_artifacts.py` - JSON schema definitions
- `seed/registry/fragment_artifacts.py` - HTML fragment templates
- `seed/registry/component_artifacts.py` - Components + document definitions
- `seed/registry/document_types.py` - Document type configurations
- `ops/db/seed_data_from_backup.sql` - Combined seed data (DELETE + COPY)
- `ops/db/restore_documents.sql` - Document restoration

### Config
- `app/api/main.py` - FastAPI app, SessionMiddleware config
- `app/core/database.py` - Database connection with UTF-8 encoding
- `Dockerfile` - Includes --proxy-headers for ALB

### Ops
- `ops/scripts/run.py` - Local development server
- `ops/aws/taskdef-www.json` - Current task definition template
- `ops/testing/AUTH-MANUAL-TEST-PLAN.md` - Manual test checklist

## Branch Status
- `development` - Current working branch
- `main` - Production (needs PR from development)

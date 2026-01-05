# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**All 10 Implementation Phases Complete** - Production-ready system deployed to AWS

## Test Summary
- **Total Tests:** 943 passing
- **Phase 0-2 (Core Engine):** Validator, Step Executor, Workflow Executor
- **Phase 3-7:** HTTP API, UI Integration, LLM Integration, Authentication
- **Phase 8-10:** API Integration, E2E Testing, Production Hardening
- **Template Integrity:** Tests ensure all extends/includes resolve correctly

---

## Session: January 5, 2026

### UI Consolidation Complete

Consolidated split UI structure into unified `app/web/` with admin/public subfolders.

**New Unified Structure:**
```
app/web/
  routes/
    admin/        <- dashboard.py, pages.py, documents.py, partials.py, admin_routes.py
    public/       <- home_routes.py, project_routes.py, document_routes.py, etc.
    shared.py     <- Jinja2 templates, filters (localtime, pluralize)
  templates/
    admin/        <- Admin pages, components, partials
    public/       <- Public pages, layout, components
  static/
    admin/        <- CSS/JS (websocket.js, styles.css)
    public/       <- login.html, accounts.html
```

**Changes Made:**
- Moved `app/ui/routers/*` to `app/web/routes/admin/`
- Moved `app/ui/templates/*` to `app/web/templates/admin/`
- Moved `app/ui/static/*` to `app/web/static/admin/`
- Updated all template `{% extends %}` and `{% include %}` paths to use `public/` prefix
- Updated static URLs: `/web/static/public/login.html`
- Updated test imports: `app.ui.routers` → `app.web.routes.admin`
- Deleted `app/ui/` directory entirely

### Template Path Fixes

Fixed template extends statements that were missing `public/` prefix:
- `document_page.html`: `{% extends "layout/base.html" %}` → `{% extends "public/layout/base.html" %}`
- `document_wrapper.html`: `{% extends "pages/app_base.html" %}` → `{% extends "public/pages/app_base.html" %}`
- `project_detail.html`: `{% extends "layout/base.html" %}` → `{% extends "public/layout/base.html" %}`

### New Template Integrity Tests

Added `tests/ui/test_template_integrity.py`:
- **test_public_templates_extend_correctly** - Validates all public templates load via Jinja2
- **test_admin_templates_extend_correctly** - Validates all admin templates load via Jinja2
- **test_no_orphan_extends_in_public** - Scans source for extends/includes missing `public/` prefix

These tests will catch template path issues before deployment.

### CI/Docker Fixes

**Fixed `.env.example` tracking:**
- File was excluded by `.gitignore` pattern `.env.*`
- Added exception: `!.env.example`

**Fixed Docker build:**
- Dockerfile referenced non-existent `workflows/` (should be `seed/workflows/`)
- Fixed path: `COPY seed/workflows/ /app/seed/workflows/`
- Fixed casing: `as` → `AS` for Docker best practices
- `.dockerignore` was blocking `requirements.txt` (all `*.txt`)
- Added exceptions for requirements files
- Changed blanket `seed/` exclusion to explicit subdirectory exclusions

**Fixed login page 404:**
- Correct path: `/web/static/public/login.html`
- Updated all references in templates

### AWS Deployment

**Current State:** Site deployed and running on AWS ECS Fargate
- DNS: `thecombine.ai` pointing to Fargate task public IP
- HTTP only (no HTTPS yet - ALB blocked)

**ALB Issue:**
- Error: "This AWS account currently does not support creating load balancers"
- Not a quota issue (50 ALBs allowed, 0 used)
- Not an SCP issue (only FullAWSAccess policy)
- Support tickets filed for us-east-1 and us-east-2
- Awaiting AWS response

**Workaround:** Using `fixip.ps1` to update Route 53 after each deployment

---

## Architecture Overview

```
UI Layer (HTMX, Chart.js, SSE Client)
           |
API Layer (Workflows, Documents, Executions, Telemetry)
           |
Service Layer (LLMExecutionService, ProgressPublisher, TelemetryService)
           |
Execution Layer (LLMStepExecutor, ExecutionContext, QualityGates)
           |
LLM Layer (Anthropic Provider, PromptBuilder, ResponseParser)
           |
Persistence Layer (DocumentRepository, ExecutionRepository, TelemetryStore)
           |
PostgreSQL
```

## Web UI Structure

```
app/web/
  routes/
    admin/                <- Admin UI routes (require_admin)
      dashboard.py        <- Cost dashboard
      pages.py            <- Workflows, executions, dashboard index
      documents.py        <- Document management
      partials.py         <- HTMX partials
      admin_routes.py     <- Admin API routes
    public/               <- Public UI routes
      home_routes.py      <- Home page
      project_routes.py   <- Project CRUD
      document_routes.py  <- Document viewing
      search_routes.py    <- Global search
    shared.py             <- Templates, filters
  templates/
    admin/                <- Admin templates
    public/               <- Public templates (use public/ prefix in extends/includes)
  static/
    admin/                <- Admin CSS/JS
    public/               <- Login, accounts pages
```

## Governing ADRs

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 | Complete | Project Audit - all state changes explicit and traceable |
| ADR-010 | Complete | LLM Execution Logging - inputs, outputs, replay capability |
| ADR-011 | Accepted | Document Ownership Model - pattern defined, implementation pending |
| ADR-012 | Accepted | Interaction Model - closed-loop execution, QA as veto |
| ADR-024 | Accepted | Clarification Question Protocol |
| ADR-027 | Accepted | Workflow Definition & Governance |

## Pending Work

**ADR-011 Document Ownership** (not yet implemented):
- `parent_document_id` column on `documents` table
- Cycle detection, scope validation, deletion guard
- UI for hierarchical document navigation

**Infrastructure:**
- ALB creation (blocked, ticket pending)
- HTTPS termination (requires ALB)

## Open Threads

- `recycle/` folder needs review then deletion
- Automated seed manifest regeneration script

## Deployment

- **Compute:** AWS ECS Fargate (cluster: `the-combine-cluster`)
- **DNS:** `thecombine.ai` (HTTP only, direct to task IP)
- **Database:** RDS PostgreSQL
- **CI/CD:** GitHub Actions to ECR to ECS

**Post-Deploy Script:** `fixip.ps1` updates Route 53 with new task IP

## Run Tests

```powershell
cd "C:\Dev\The Combine"
python -m pytest tests/ -v
```

---
_Last updated: 2026-01-05_
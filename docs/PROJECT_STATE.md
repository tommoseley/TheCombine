# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**All 10 Implementation Phases Complete** - Production-ready system with comprehensive Admin UI

## Test Summary
- **Total Tests:** 940 passing
- **Phase 0-2 (Core Engine):** Validator, Step Executor, Workflow Executor
- **Phase 3-7:** HTTP API, UI Integration, LLM Integration, Authentication
- **Phase 8-10:** API Integration, E2E Testing, Production Hardening

---

## Session: January 5, 2026 (Continued)

### UI Consolidation

Consolidated split UI structure into unified `app/web/` with admin/public subfolders:

**Previous Structure (DELETED):**
```
app/ui/           <- Admin routes, templates, static (DELETED)
app/web/          <- Public routes, templates, static
```

**New Unified Structure:**
```
app/web/
  routes/
    admin/        <- dashboard.py, pages.py, documents.py, partials.py, admin_routes.py
    public/       <- home_routes.py, project_routes.py, document_routes.py, etc.
    shared.py     <- Jinja2 templates, filters (localtime, pluralize)
    __init__.py   <- Main router
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
- Updated template include paths: `"components/..."` → `"public/components/..."`
- Updated static URLs: `/web/static/public/login.html`
- Updated test imports: `app.ui.routers` → `app.web.routes.admin`
- Deleted `app/ui/` directory entirely

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
- `/static/login.html` returned 404
- Correct path: `/web/static/public/login.html`
- Updated all references in templates

---

## Previous Session Work (January 5, 2026)

### Admin UI - Unified Executions & Costs

**Unified Executions Page** (`/admin/executions`)
- Combined workflow executions and document builds in single view
- Source filter dropdown: All Sources / Workflows Only / Document Builds Only
- Status filter: All / Running / In Progress / Success / Completed / Failed / Cancelled
- Date range filtering with `date_from` and `date_to` parameters
- Source column with badges: purple "Workflow" or blue "Doc Build"

**Execution Details Page** (`/admin/executions/{id}`)
- Document build details: Project, role, model, prompt, timing, tokens, cost
- Expandable inputs/outputs sections
- Error display with severity badges

**Unified Costs Dashboard** (`/admin/dashboard/costs`)
- Combined workflow telemetry and document build costs
- Stacked bar chart: Purple for workflows, Blue for documents

**Main Dashboard Updates** (`/admin`)
- "Recent Activity" with combined executions and document builds
- "Doc Builds Today" stat

### Public UI - Document Headers
- Reusable `_document_header.html` partial
- `localtime` Jinja2 filter for UTC to local timezone

### Navigation Fixes
- Back button changed from HTMX to regular anchor tags
- HTMX partial responses check `HX-Request` header

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

## Workflow Engine Components

```
WorkflowExecutor
    +-- StepExecutor
    |   +-- PromptLoader
    |   +-- InputResolver
    |   +-- LLMService (protocol)
    |   +-- ClarificationGate
    |   +-- QAGate
    |   +-- RemediationLoop
    +-- WorkflowContext
    +-- IterationHandler
    +-- AcceptanceGate
    +-- StatePersistence
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
    public/               <- Public templates
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

## Pending Work: ADR-011 Document Ownership

Document ownership model is accepted but **not yet implemented**:

**Missing Schema:**
- `parent_document_id` column on `documents` table
- `parent`/`children` ORM relationships
- Database migration

**Missing Enforcement:**
- Cycle detection (DAG validation)
- Scope validation
- Deletion guard
- Workflow ownership validation

## Open Threads

- ADR-011 implementation
- `recycle/` folder needs review then deletion
- Automated seed manifest regeneration script

## Deployment

- **Compute:** AWS ECS Fargate (cluster: `the-combine-cluster`)
- **DNS:** `thecombine.ai` (port 8000, HTTP only)
- **Database:** RDS PostgreSQL
- **CI/CD:** GitHub Actions to ECR to ECS to Route 53

## Run Tests

```powershell
cd "C:\Dev\The Combine"
python -m pytest tests/ -v
```

---
_Last updated: 2026-01-05_
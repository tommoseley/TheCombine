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

## Session: January 5, 2026

### Admin UI - Unified Executions & Costs

**Unified Executions Page** (`/admin/executions`)
- Combined workflow executions and document builds in single view
- Source filter dropdown: All Sources / Workflows Only / Document Builds Only
- Status filter: All / Running / In Progress / Success / Completed / Failed / Cancelled
- Date range filtering with `date_from` and `date_to` parameters
- Source column with badges: purple "Workflow" or blue "Doc Build"
- All executions now clickable with "View" link to details

**Execution Details Page** (`/admin/executions/{id}`)
- Created `document_build_detail.html` template for document builds
- Shows: Project ID/Name, role, model, prompt ID/version
- Timing: Started, Ended, Elapsed seconds
- Tokens: Input/Output/Total with formatted numbers
- Cost: USD with 6 decimal precision
- Inputs section: Expandable content with kind, size, redacted status
- Outputs section: Expandable content with parse/validation status badges
- Errors section: Severity badges (FATAL/ERROR/WARN), stage, expandable details
- Metadata section: JSON display if present

**Unified Costs Dashboard** (`/admin/dashboard/costs`)
- Combined workflow telemetry and document build costs
- Source filter: All Sources / Workflows Only / Document Builds Only
- Daily breakdown table with Workflow/Documents cost columns
- Stacked bar chart (Chart.js): Purple for workflows, Blue for documents
- Aggregates from both `workflow_executions` and `llm_run` tables

**Main Dashboard Updates** (`/admin`)
- "Recent Activity" section (renamed from "Recent Executions")
- Shows combined workflow executions and document builds
- Source badges on each row
- "Doc Builds Today" stat with clickable link to filtered executions
- View links on all activity rows

**Date/Time Handling**
- All dates stored as UTC in database
- Display timezone: America/New_York (Eastern Time)
- `DISPLAY_TZ` constant in `pages.py` for consistent conversion
- Date filters: "from X to X" means 00:00 to 23:59:59 of that day

### Public UI - Document Headers

**Document Header Partial** (`_document_header.html`)
- Reusable header for all document content templates
- Breadcrumb navigation: Project Name / Document Type
- Icon, title, description
- "Prepared: [date/time]" in local timezone

**Updated Document Templates**
- `_project_discovery_content.html` - uses header partial
- `_technical_architecture_content.html` - uses header partial
- `_epic_backlog_content.html` - uses header partial
- `_story_backlog_content.html` - uses header partial

**Jinja2 Filters** (`shared.py`)
- Added `localtime` filter for UTC to local timezone conversion
- Format: "January 05, 2026 at 3:45 PM"

### Navigation Fixes

**Back Button Fix**
- Changed HTMX navigation to regular anchor tags in `project_inspector.html`
- Back button now performs full page reload with proper layout
- Prevents cached partial responses from breaking layout

**HTMX Partial Responses**
- `executions_list()` now checks `HX-Request` header
- Returns partial (`execution_list.html`) for HTMX requests
- Returns full page (`executions.html`) for browser navigation
- Prevents nested layout issue when using date filters

### Files Modified

**Backend Routes:**
- `app/ui/routers/pages.py` - Unified executions, date filtering, timezone handling
- `app/ui/routers/dashboard.py` - Unified costs from both sources
- `app/web/routes/shared.py` - Added `localtime` Jinja2 filter

**Admin Templates:**
- `app/ui/templates/pages/dashboard.html` - Recent Activity, Doc Builds Today link
- `app/ui/templates/pages/executions.html` - Source and date filters
- `app/ui/templates/partials/execution_list.html` - Source badges, View links
- `app/ui/templates/pages/dashboard/costs.html` - Source filter, stacked chart
- `app/ui/templates/pages/document_build_detail.html` - NEW: Execution details

**Public Templates:**
- `app/web/templates/pages/partials/_document_header.html` - NEW: Shared header
- `app/web/templates/pages/partials/_project_discovery_content.html` - Uses header
- `app/web/templates/pages/partials/_technical_architecture_content.html` - Uses header
- `app/web/templates/pages/partials/_epic_backlog_content.html` - Uses header
- `app/web/templates/pages/partials/_story_backlog_content.html` - Uses header
- `app/web/templates/components/project_inspector.html` - Regular links (not HTMX)

**Tests Updated:**
- `tests/ui/test_dashboard.py` - "Recent Activity" text, db mocks
- `tests/ui/test_executions.py` - db mocks
- `tests/ui/test_websocket_polish.py` - "Recent Activity" test, db mocks
- `tests/ui/test_dashboard_costs.py` - db mocks
- `tests/e2e/test_ui_integration.py` - db mocks

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

Reviewed ADR-011-Part-2. Document ownership model is accepted but **not yet implemented**:

**Missing Schema:**
- `parent_document_id` column on `documents` table
- `parent`/`children` ORM relationships
- Database migration

**Missing Enforcement:**
- Cycle detection (DAG validation)
- Scope validation (child scope ≤ parent scope)
- Deletion guard (prevent deleting parent with children)
- Workflow ownership validation

**Missing UI:**
- Child document queries
- Epic → Story ownership traversal in sidebar
- Hierarchical document navigation

**Required Tests (per ADR-011-Part-2):**
1. Hierarchy Creation
2. Cycle Prevention
3. Scope Violation
4. Workflow Ownership Violation
5. Deletion Guard

This is significant work for a future session.

## Open Threads

- ADR-011 implementation (see above)
- `recycle/` folder needs review then deletion
- Automated seed manifest regeneration script
- Anthropic API key rotation (was exposed in prior commit)

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

## Documentation

- `docs/implementation-plans/COMPLETE-IMPLEMENTATION-SUMMARY.md` - Full 10-phase summary
- `docs/adr/ADR-INVENTORY.md` - Complete ADR listing and status
- `docs/session_logs/` - Session history

---
_Last updated: 2026-01-05_
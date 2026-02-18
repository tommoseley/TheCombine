# WS-ADMIN-RECONCILE-001: Restore Admin Instrumentation and Navigation Integrity

## Status: Accepted

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- POL-WS-001 -- Standard Work Statements
- WS-ADR-050-002 -- HTMX Admin Decommission (prerequisite, complete)

## Verification Mode: A

---

## Purpose

The HTMX admin decommission (WS-ADR-050-002) removed deprecated server-rendered UI but left the system without operational visibility into executions, costs, and LLM runs. The Admin Workbench (`/admin/workbench`) is a composer/authoring tool -- it does not replace the operational monitoring capability that was removed.

This Work Statement restores that capability as SPA views backed by proper API endpoints. Deprecated HTMX code is treated as a specification source (via git history and the WS-ADR-050-002 audit), not an implementation source.

---

## Preconditions

- WS-ADR-050-002 complete (HTMX admin routes removed, Tier 0 clean)
- Tier 0 harness operational (`ops/scripts/tier0.sh`)
- The following API endpoints are mounted and functional:
  - `GET /api/v1/dashboard/summary`
  - `GET /api/v1/executions` (list, filterable)
  - `GET /api/v1/executions/{id}` (detail)
  - `GET /api/v1/executions/{id}/transcript`
  - `GET /api/v1/executions/{id}/qa-coverage`
  - `GET /api/v1/document-workflows/executions`
- The following exist as code but are NOT mounted:
  - `app/api/v1/routers/telemetry.py` -- cost dashboard endpoint backed by `cost_service` (queries `llm_runs` table)
- `/admin` is a dead link (404) in both `AccountsSidecar.jsx` and `UserSidecar.jsx`

---

## Non-Goals

- Do not restore HTMX templates, routes, or server-rendered views
- Do not recreate the `InMemoryDocumentRepository`-backed document browser (real documents are accessed via `/api/v1/projects/{id}/tree`)
- Do not alter instrumentation semantics beyond surfacing existing data
- Do not introduce new telemetry collection -- use what the system already records in `llm_runs`
- Do not duplicate Admin Workbench functionality (config browsing, prompt editing, etc.)

---

## Scope

### Includes

1. Mount the telemetry router to expose cost data via API
2. Add server route for `/admin` to serve SPA
3. Build SPA Admin Panel with operational views:
   - Execution list (workflow + document workflow executions, unified)
   - Execution detail (status, steps, transcript, QA coverage)
   - Cost dashboard (daily breakdown, totals)
4. Fix dead `/admin` link in SPA navigation sidecars
5. Intent-first tests for all Tier 1 criteria
6. Tier 0 sweep

### Excludes

- Document browser (covered by existing project tree API)
- Document type config viewer (covered by Admin Workbench)
- Acceptance/clarification forms (these are production floor interactions, not admin monitoring)
- New telemetry instrumentation or metrics collection

---

## Tier 1 Verification Criteria

### Criterion 1: Telemetry API Mounted and Returning Data

The telemetry cost endpoint must be reachable and return the expected schema.

Tests must assert:
- `GET /api/v1/telemetry/costs` returns HTTP 200
- Response contains `daily_data` (array) and `summary` (object)
- Summary includes: `total_cost`, `total_tokens`, `total_calls`
- `days` query parameter is accepted (1-90, default 7)

Implementation: Mount the existing telemetry router in `app/api/v1/__init__.py`.

### Criterion 2: Server Route for /admin Serves SPA

Navigation to `/admin` must serve the SPA `index.html`, not return 404.

Tests must assert:
- `GET /admin` returns HTTP 200
- Response content-type is `text/html`
- Response body contains SPA entry point marker (e.g., `<div id="root">`)

### Criterion 3: SPA Admin Panel Renders

The SPA must route `/admin` to an Admin Panel component (not the production floor fallthrough).

Tests must assert:
- SPA build succeeds (`npm run build` exits 0)
- An `AdminPanel` component (or equivalent) exists and is imported in `App.jsx`
- `App.jsx` routing matches `/admin` explicitly (not fallthrough to `AppContent`)

Note: SPA component rendering is verified by build success + route registration. Deep UI testing is out of scope for Tier 1.

### Criterion 4: Execution List API Contract

The execution list endpoint must return the fields needed for the admin execution browser.

Tests must assert:
- `GET /api/v1/executions` returns HTTP 200 with a list
- Each execution contains: `execution_id`, `workflow_id`, `status`, `started_at`
- `GET /api/v1/document-workflows/executions` returns HTTP 200 with a list
- Each item contains: `execution_id`, `document_type`, `status`, `created_at`

### Criterion 5: Execution Detail API Contracts (Transcript + QA Coverage)

The execution detail sub-endpoints must return structured data for the admin detail view.

Tests must assert:
- `GET /api/v1/executions/{id}/transcript` returns `total_runs`, `total_tokens`, `total_cost`, and a `transcript` array
- Each transcript entry contains: `run_number`, `role`, `model`, `status`, `tokens`, `cost`
- `GET /api/v1/executions/{id}/qa-coverage` returns `qa_nodes` and `summary`

Note: These endpoints are already mounted. Tests encode the contract the SPA will depend on, preventing silent schema drift.

### Criterion 6: No Dead Admin Navigation Links

No SPA navigation element may link to a path that returns 404.

Tests must assert:
- No `href="/admin"` exists in SPA source without a corresponding server and client route
- The `/admin` path is handled by both server (serves SPA) and client (renders AdminPanel)
- `/admin/workbench` continues to work (regression guard)

---

## Procedure

### Step 1: Write Failing Tests (Intent-First)

For each Tier 1 criterion, write tests that assert the postcondition. All tests must fail because the changes have not been made yet.

Test file: `tests/infrastructure/test_admin_reconciliation.py`

Verify: run the tests, confirm they fail for the expected reasons.

### Step 2: Mount Telemetry Router

In `app/api/v1/__init__.py`, mount the telemetry router so `GET /api/v1/telemetry/costs` is reachable.

Verify: Criterion 1 tests pass.

### Step 3: Add Server Route for /admin

Add a server-side route that serves `spa/dist/index.html` for `/admin`. Follow the same pattern used by `/admin/workbench` in `home_routes.py`.

Verify: Criterion 2 tests pass.

### Step 4: Build SPA Admin Panel

Create SPA components for the admin panel:

1. **AdminPanel.jsx** -- Top-level admin layout with navigation tabs:
   - Executions (default view)
   - Costs
   - Link to Workbench (`/admin/workbench`)

2. **ExecutionList.jsx** -- Execution browser:
   - Fetches from `GET /api/v1/executions` and `GET /api/v1/document-workflows/executions`
   - Displays: execution_id, workflow_id/document_type, status, started_at
   - Filterable by status
   - Click through to execution detail

3. **ExecutionDetail.jsx** -- Execution detail view:
   - Fetches from `GET /api/v1/executions/{id}`
   - Sub-tabs or sections for:
     - Status and step progress
     - Transcript (from `GET /api/v1/executions/{id}/transcript`): run list with role, model, tokens, cost
     - QA Coverage (from `GET /api/v1/executions/{id}/qa-coverage`): constraint pass/fail summary

4. **CostDashboard.jsx** -- Cost overview:
   - Fetches from `GET /api/v1/telemetry/costs?days=N`
   - Displays: daily_data table, summary totals
   - Period selector (7/14/30 days)

5. **Update App.jsx** -- Add `/admin` route matching to render `AdminPanel`

6. **Fix sidecar links** -- Ensure `AccountsSidecar.jsx` and `UserSidecar.jsx` `/admin` links work

Verify: Criteria 3, 6 tests pass. SPA builds successfully.

### Step 5: Verify All Tier 1 Tests Pass

Run all Tier 1 tests. All must pass. If any fail, fix the implementation, not the tests.

### Step 6: Run Tier 0 Sweep

Run `ops/scripts/tier0.sh --allow-missing typecheck --frontend`. Must return zero.

The `--frontend` flag is required because SPA files are changed.

### Step 7: Produce Demo Package

Document:
- Files changed/created
- Tier 1 test results (all pass)
- Tier 0 results (clean)
- API endpoints: which were mounted, which were created, which were consumed
- Screenshots or route listing showing admin panel is navigable

---

## Prohibited Actions

- Do not restore HTMX templates or routes from git history
- Do not copy HTMX template markup into JSX
- Do not introduce direct repository calls in route handlers (all data through API endpoints)
- Do not skip the failing-test phase
- Do not modify tests to make them pass (fix implementation instead)
- Do not bypass Tier 0

---

## Verification Checklist

- [ ] All Tier 1 tests written and verified failing
- [ ] Telemetry router mounted (Criterion 1)
- [ ] `/admin` server route serves SPA (Criterion 2)
- [ ] SPA Admin Panel renders with execution list, execution detail, cost dashboard (Criteria 3, 4, 5)
- [ ] No dead navigation links (Criterion 6)
- [ ] All Tier 1 tests pass
- [ ] Tier 0 harness returns zero (with --frontend)
- [ ] Demo package produced

## Definition of Done

- Operational visibility into executions and costs is restored via SPA admin panel
- All data flows through proper API endpoints (no direct repository access from UI layer)
- Navigation from settings menu to admin panel works end-to-end
- Admin Workbench (`/admin/workbench`) continues to function (no regression)
- One complete ADR-050 factory cycle executed with evidence

---

_End of WS-ADMIN-RECONCILE-001_

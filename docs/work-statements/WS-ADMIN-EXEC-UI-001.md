# WS-ADMIN-EXEC-UI-001: Admin Executions List UX Improvements

## Status: Complete

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- POL-WS-001 -- Standard Work Statements
- WS-ADMIN-RECONCILE-001 -- Admin Operational Visibility (prerequisite, complete)

## Verification Mode: A

---

## Purpose

The Admin Executions list was stood up in WS-ADMIN-RECONCILE-001 as a functional baseline. This Work Statement improves the list's usability: full-width ID column, human-readable project codes, sortable columns, document-type filtering, and search.

**SPA route**: `/admin` -- served by `home_routes.py` (`GET /admin` -> `spa/dist/index.html`), routed by `App.jsx:AppWithAuth` to `AdminPanel.jsx`, which renders `ExecutionList.jsx` under the "Executions" tab. This is the React SPA admin panel, not the decommissioned HTMX admin section.

---

## Preconditions

- WS-ADMIN-RECONCILE-001 complete (Admin Panel, ExecutionList, ExecutionDetail deployed)
- Tier 0 harness operational (`ops/scripts/tier0.sh`)
- Execution list component: `spa/src/components/admin/ExecutionList.jsx`
- Data endpoints:
  - `GET /api/v1/executions` (workflow executions -- returns `project_id` as UUID)
  - `GET /api/v1/document-workflows/executions` (document-workflow executions -- returns `project_id` as UUID)
  - `GET /api/v1/projects` (project list -- used to resolve UUID to human-readable `project_id` code like `LIR-001`)

---

## Non-Goals

- Do not modify backend API response schemas
- Do not add server-side sorting, filtering, or pagination (client-side only)
- Do not change ExecutionDetail or CostDashboard
- Do not add new API endpoints
- Do not add new npm dependencies

---

## Scope

| Area | Change |
|------|--------|
| `spa/src/components/admin/ExecutionList.jsx` | All UI changes (ID column, project code column, sortable headers, doc-type filter, search) |
| `spa/src/api/client.js` | No changes expected (all required endpoints already wired) |
| `tests/infrastructure/test_admin_exec_ui.py` | Intent-first tests for all Tier 1 criteria |

---

## Tier 1 Criteria

### C1: Full Execution ID Display

The execution ID column displays the full execution_id. The rendered output must not contain `...` or `\u2026` (ellipsis) for any execution_id. Column must be wide enough to render `exec-XXXXXXXXXXXX` (~20 chars) without wrapping.

### C2: Project Code Column

A "Project" column displays the human-readable project code (e.g., `LIR-001`). Values match the pattern `[A-Z]{2,5}-\d{3}` or show `--` if the project cannot be resolved.

**Resolution source**: `ExecutionList` calls `api.getProjects()` (existing `GET /api/v1/projects` endpoint) on mount and builds a `{UUID -> project_id code}` lookup map. Execution rows use this map to resolve their `projectId` (UUID) to the display code. This avoids inventing a new fetch or a new API.

### C3: Sortable Column Headers

Clicking a column header sorts rows by that column. Clicking the same header again reverses sort direction. An indicator (arrow or triangle) shows which column is sorted and in which direction.

### C4: Document Type Filter

A filter control exists for Workflow/Document Type. Selecting a value reduces the displayed rows to only matching executions. Clearing the filter (selecting "All") restores all rows.

### C5: Search

A text input filters the list by project code or execution ID substring match (case-insensitive). Clearing the input restores all rows. When the search matches nothing, an empty-state message is shown.

---

## Steps

### Step 1: Write Failing Tests

Write `tests/infrastructure/test_admin_exec_ui.py` with intent-first tests for all five Tier 1 criteria.

**Testing approach**: No React test harness (Jest / React Testing Library) is currently configured for this project. Tests use source-level structural inspection of `ExecutionList.jsx` as a bootstrap proxy for behavioral verification.

> **Mode B debt**: Source inspection validates that required structures exist in code, but cannot verify rendered behavior (sort order, filter reduction, empty-state appearance). This is an acknowledged verification gap. When a React test harness is established, these tests should be upgraded to render-level behavioral assertions.

All tests must FAIL before Step 2.

### Step 2: Implement UI Changes

Modify `spa/src/components/admin/ExecutionList.jsx` to satisfy all Tier 1 criteria:
- Show full execution_id (remove `substring(0, 8) + '...'` truncation)
- Add Project column; call `api.getProjects()` on mount to build UUID-to-code lookup
- Add sort state (`sortKey`, `sortDir`) and clickable headers with direction indicator
- Add document-type filter dropdown (values derived from loaded data)
- Add search input filtering on project code and execution ID, with empty-state

### Step 3: Rebuild SPA and Verify

- `cd spa && npm run build`
- Run `python -m pytest tests/infrastructure/test_admin_exec_ui.py -v` -- all must pass
- Run full Tier 0 sweep (`ops/scripts/tier0.sh` or equivalent)

### Step 4: Produce Demo Package

Write `docs/work-statements/WS-ADMIN-EXEC-UI-001-demo-package.md` with Tier 0 summary.

---

## Prohibited Actions

- Do not modify backend API routers or response models
- Do not add new API endpoints or new npm dependencies
- Do not change files outside the scope table above
- Do not skip the intent-first testing step

---

## Verification Checklist

- [ ] All 5 Tier 1 criteria have corresponding tests
- [ ] Tests failed before implementation (Mode B: source inspection -- acknowledged gap)
- [ ] Tests pass after implementation
- [ ] SPA builds cleanly
- [ ] Full test suite passes
- [ ] Lint clean on changed files

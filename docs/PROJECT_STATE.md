# PROJECT_STATE.md

**Last Updated:** 2026-02-19
**Updated By:** Claude (WS-ONTOLOGY-001 session)

## Current Focus

**COMPLETE:** ADR-050 -- Work Statement Verification Constitution (execution_state: complete)
- Tier 0 harness operational (ops/scripts/tier0.sh) with 11 tests
- First factory cycle proven: HTMX admin removal under Mode A with intent-first testing
- Mode B enforcement, JSON output, CI guards implemented

**ACCEPTED:** ADR-051 -- Work Package as Runtime Primitive
- Decision recorded; implementation deferred until WS volume demands it
- IP > WP > WS hierarchy replaces Epics/Features/Stories

**DRAFT:** ADR-052 -- Document Pipeline Integration for WP/WS
- Defines schema/prompt changes for IPP/IPF, new artifact types, Production Floor updates
- Accept on merge

**COMPLETE:** WS-ONTOLOGY-001 -- Register work_package as first-class document type
- Handler, state machine, seed entry, registry registration, 20 Tier 1 tests
- Commit `76d216a`, pushed to `workbench/ws-e583fd0642f5`

**COMPLETE:** WS-ADMIN-RECONCILE-001 -- Restore admin operational visibility as SPA views
**COMPLETE:** WS-ADMIN-EXEC-UI-001 -- Admin Executions list UX improvements

---

## ADR-050 Acceptance Criteria Status

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Tier 0 runnable as single command | Complete |
| 2 | At least one WS executed under Mode A with intent-first testing | Complete (HTMX removal) |
| 3 | Mode B tracking exists | Partial (visible in harness output, no metrics logging yet) |
| 4 | POL-WS-001 references ADR-050 | Pending |
| 5 | Test-First Rule documented in AI.md | Pending |

---

## Verification Debt

| Item | Reason | Mechanization Plan |
|------|--------|--------------------|
| mypy type checking | Not installed | Install mypy, configure for app/, add to Tier 0 harness |
| ExecutionList tests (WS-ADMIN-EXEC-UI-001) | No React test harness | Source inspection proxy; upgrade to Jest + RTL when harness established |

---

## Admin Panel Status

**Location:** `/admin` (SPA route, served by home_routes.py)

### Features Complete
- **Execution list** with full ID display, project code column, sortable headers, doc-type filter, search (WS-ADMIN-EXEC-UI-001)
- **Execution detail** with overview, transcript (expandable input/output content), QA coverage (WS-ADMIN-RECONCILE-001)
- **Cost dashboard** with daily breakdown, period selector, summary cards (WS-ADMIN-RECONCILE-001)
- **Deep links**: `/admin/executions/{id}` and `/admin?execution={id}` both supported
- **Dual execution API**: Handles both workflow and document-workflow (exec- prefixed) execution IDs

### Components
- `spa/src/components/admin/AdminPanel.jsx` -- Tab layout, deep-link parsing
- `spa/src/components/admin/ExecutionList.jsx` -- Unified execution browser
- `spa/src/components/admin/ExecutionDetail.jsx` -- Detail with transcript content
- `spa/src/components/admin/CostDashboard.jsx` -- Daily cost breakdown

---

## Admin Workbench Status

**Location:** `/admin/workbench` (SPA route)

### Features Complete
- All features from previous state
- **Gate Profile pattern** (2026-02-07)
- **intake_and_route POW** (2026-02-07)
- **RouterHandler** (2026-02-07)
- **Selected item highlighting** (2026-02-07)

---

## WS-STATION-DATA-001 Status (Complete)

Event-driven station display system for production floor UI. All phases complete.

---

## Workflow Architecture

### Document Creation Workflows (DCWs)
- `concierge_intake` v1.4.0
- `project_discovery` v1.8.0
- `technical_architecture` v1.0.0
- `implementation_plan_primary` v1.0.0
- `implementation_plan` v1.0.0

### Project Orchestration Workflows (POWs)
- `intake_and_route` v1.0.0
- `software_product_development` v1.0.0

---

## React SPA Status

**Location:** `spa/` directory

### Features Complete
- All previous features through 2026-02-16
- **HTMX admin removal** (2026-02-18): Deprecated HTMX admin routes, templates, and static assets removed
- **Admin Panel restored** (2026-02-18): Execution monitoring, cost dashboard, transcript inspection as SPA views
- **Admin Executions UX** (2026-02-18): Sortable columns, doc-type filter, search, project code resolution

---

## Architecture

Same as previous state. Key additions:

```
spa/src/components/admin/
+-- AdminPanel.jsx             # Tab layout, deep-link parsing
+-- ExecutionList.jsx          # Unified execution browser with sort/filter/search
+-- ExecutionDetail.jsx        # Detail with transcript content rendering
+-- CostDashboard.jsx          # Daily cost breakdown

tests/infrastructure/
+-- test_tier0_harness.py      # 11 tests for Tier 0 harness
+-- test_htmx_admin_removal.py # 10 intent-first tests for HTMX removal
+-- test_admin_reconciliation.py # 17 tests for admin restoration
+-- test_admin_exec_ui.py      # 13 tests for executions UX (Mode B debt)
```

---

## Key Technical Decisions

All previous decisions (1-29) plus:

30. **Admin Panel as SPA views** -- Execution monitoring, cost dashboard, transcript inspection rebuilt as React components backed by existing API endpoints (not restored from HTMX)
31. **Dual execution API strategy** -- ExecutionDetail tries both /api/v1/executions/{id} and /api/v1/document-workflows/executions/{id} to handle both old-style and exec-prefixed IDs
32. **Project code resolution** -- ExecutionList calls api.getProjects() on mount to build UUID-to-project-code lookup map (no new API endpoints)

---

## Quick Commands

```bash
# Run backend
cd ~/dev/TheCombine && source venv/bin/activate
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Build SPA for production
cd spa && npm run build

# Run tests
python -m pytest tests/ -x -q

# Run Tier 0 verification harness
cd ~/dev/TheCombine && ./ops/scripts/tier0.sh

# Tier 0 with frontend check
./ops/scripts/tier0.sh --frontend

# Tier 0 allowing Mode B for missing tools
./ops/scripts/tier0.sh --allow-missing typecheck
```

---

## Handoff Notes

### Recent Work (2026-02-19)
- **WS-ONTOLOGY-001** complete -- work_package document type: state machine, handler, seed entry, 20 tests (6 criteria)

### Previous Work (2026-02-18/19)
- **WS-ADMIN-RECONCILE-001** complete -- Admin Panel, ExecutionDetail, CostDashboard, telemetry router mounted, dead links fixed
- **WS-ADMIN-EXEC-UI-001** complete -- Full execution IDs, project code column, sortable headers, doc-type filter, search

### Previous Work (2026-02-18)
- ADR-050, 051, 052 written
- Tier 0 harness built
- HTMX admin removal executed under ADR-050 protocol

### Next Work
- WS-ONTOLOGY-002 through WS-ONTOLOGY-007 (remaining ontology work statements)
- Add Test-First Rule to AI.md (ADR-050 acceptance criterion 5)
- Add ADR-050 reference to POL-WS-001 (ADR-050 acceptance criterion 4)
- Project Logbook design (productized PROJECT_STATE.md for Combine-managed projects)
- WS as Combine document type (enables factory to author its own work)
- ADR-052 implementation when ready (IPP/IPF schema migration, WP/WS artifact types)
- Establish React test harness to retire Mode B debt on ExecutionList tests

### Open Threads
- Project Logbook -- productized equivalent of PROJECT_STATE.md
- TA emitting ADR candidates -- future work pinned in ADR-052
- MCP connector -- read-only document query layer as first step toward Claude Code integration
- "Send to Combine" clipboard prompt -- not yet authored
- Multi-LLM Sow tool -- explored, existing tools sufficient for now

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files
- Sync IPP task prompt field names with IPP schema
- Install mypy and resolve Verification Debt

### Known Issues
- Two copies of IPF schema must be kept in sync
- IPP task prompt field names don't match IPP schema

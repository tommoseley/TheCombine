# PROJECT_STATE.md

**Last Updated:** 2026-02-19
**Updated By:** Claude (WS-ONTOLOGY-007 session close)

## Current Focus

**COMPLETE:** ADR-050 -- Work Statement Verification Constitution (execution_state: complete)
- Tier 0 harness operational (ops/scripts/tier0.sh) with 11 tests
- First factory cycle proven: HTMX admin removal under Mode A with intent-first testing
- Mode B enforcement, JSON output, CI guards implemented

**COMPLETE:** ADR-051 -- Work Package as Runtime Primitive
- Decision recorded and fully implemented via WS-ONTOLOGY-001 through WS-ONTOLOGY-007
- IP > WP > WS hierarchy replaces Epics/Features/Stories

**COMPLETE:** ADR-052 -- Document Pipeline Integration for WP/WS
- All implementation work statements executed (WS-ONTOLOGY-001 through WS-ONTOLOGY-007)
- Schema/prompt changes for IPP/IPF, new artifact types, Production Floor updates all done

**COMPLETE:** WS-ONTOLOGY-001 -- Register work_package as first-class document type
**COMPLETE:** WS-ONTOLOGY-002 -- Register work_statement with parent WP enforcement
**COMPLETE:** WS-ONTOLOGY-003 -- Project Logbook with transactional WS acceptance
**COMPLETE:** WS-ONTOLOGY-004 -- Replace IPP epic_candidates with work_package_candidates
**COMPLETE:** WS-ONTOLOGY-005 -- Update IPF to reconcile and commit Work Packages
**COMPLETE:** WS-ONTOLOGY-006 -- Remove Epic/Feature document type pipeline entirely
**COMPLETE:** WS-ONTOLOGY-007 -- Production Floor UI renders WP/WS hierarchy

**COMPLETE:** WS-ADMIN-RECONCILE-001 -- Restore admin operational visibility as SPA views
**COMPLETE:** WS-ADMIN-EXEC-UI-001 -- Admin Executions list UX improvements

---

## Test Suite

- **2225 tests** passing as of WS-ONTOLOGY-007 completion
- Tier 1 tests cover all ontology work statements (6 criteria groups each)
- Mode B debt: SPA component tests use grep-based source inspection (no React test harness)

---

## Verification Debt

| Item | Reason | Mechanization Plan |
|------|--------|--------------------|
| mypy type checking | Not installed | Install mypy, configure for app/, add to Tier 0 harness |
| SPA component tests (WS-007) | No React test harness | Source inspection proxy; upgrade to Jest + RTL when harness established |
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
- All previous features through 2026-02-18
- **Production Floor WP/WS** (2026-02-19): DocumentNode renders Work Packages with metadata (ws_done/ws_total, Mode B count, dependency count), WSChildList replaces FeatureGrid for WS children, all Epic references removed

---

## Architecture

```
app/domain/handlers/
+-- work_package_handler.py        # WP document handler
+-- work_statement_handler.py      # WS document handler with parent WP enforcement
+-- project_logbook_handler.py     # Logbook handler (governance)

app/domain/services/
+-- work_package_state.py          # WP state machine (PLANNED->READY->IN_PROGRESS->AWAITING_GATE->DONE)
+-- work_statement_state.py        # WS state machine (DRAFT->READY->IN_PROGRESS->ACCEPTED/REJECTED/BLOCKED)
+-- work_statement_registration.py # WS-to-WP registration + rollup
+-- logbook_service.py             # Logbook CRUD + transactional WS acceptance orchestration

spa/src/components/
+-- DocumentNode.jsx               # Unified L1/L2 node (WP metadata display)
+-- WSChildList.jsx                # WS children sidecar tray
+-- Floor.jsx                      # Production floor layout

tests/tier1/handlers/
+-- test_work_package_handler.py   # 20 tests (WS-001)
+-- test_work_statement_handler.py # 21 tests (WS-002)
+-- test_project_logbook_handler.py # 24 tests (WS-003)
+-- test_ipp_wp_candidates.py      # 15 tests (WS-004)
+-- test_ipf_wp_reconcile.py       # 17 tests (WS-005)
+-- test_epic_feature_removal.py   # 21 tests (WS-006)
+-- test_production_floor_wp_ws.py # 17 tests (WS-007)
```

---

## Key Technical Decisions

All previous decisions (1-32) plus:

33. **WP/WS ontology replaces Epic/Feature** -- Full pipeline migration: handlers, state machines, seed entries, IPP/IPF schemas, Production Floor UI (WS-ONTOLOGY-001 through 007)
34. **Logbook atomicity via deepcopy** -- Transactional WS acceptance works on deep copies; originals unchanged on failure (WS-ONTOLOGY-003)
35. **Lazy logbook creation** -- Logbook created on first WS acceptance, not project bootstrap (WS-ONTOLOGY-003)
36. **BCP pipeline retains epic/feature hierarchy** -- fanout_service and schema_artifacts use these as backlog level names (not document types); intentionally preserved during WS-ONTOLOGY-006

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
- **WS-ONTOLOGY-001 through 007** all complete — full ontology migration from Epic/Feature to WP/WS
- All commits on branch `workbench/ws-e583fd0642f5`, pushed to remote
- 2225 tests passing, SPA builds clean

### Next Work
- Merge `workbench/ws-e583fd0642f5` to main (7 ontology commits + prior docs commit)
- Mark ADR-051 and ADR-052 execution_state as complete
- Add Test-First Rule to AI.md (ADR-050 acceptance criterion 5)
- Add ADR-050 reference to POL-WS-001 (ADR-050 acceptance criterion 4)
- Establish React test harness to retire Mode B debt on SPA tests
- Project Logbook as productized PROJECT_STATE.md for Combine-managed projects
- WS as Combine document type (enables factory to author its own work)

### Open Threads
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
- BCP pipeline still uses "epic"/"feature" as hierarchy level names (intentional, separate from document types)

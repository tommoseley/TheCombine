# PROJECT_STATE.md

**Last Updated:** 2026-03-01
**Updated By:** Claude (WP-CRAP-001 execution + CRAP analysis)

## Current Focus

**COMPLETE:** WP-CRAP-001 -- Testability Refactoring (7 Work Statements)
- WS-CRAP-001: Workflow Engine Batch 1 (5 targets, 108 tests)
- WS-CRAP-002: API v1 Routers Batch 1 (10 targets, 111 tests)
- WS-CRAP-003: API Services Batch 1 (10 targets, 106 tests)
- WS-CRAP-004: Document Handlers Batch 1 (7 targets, 237 tests)
- WS-CRAP-005: Domain Services Batch 1 (10 targets, 131 tests)
- WS-CRAP-006: Web Routes Batch 1 (10 targets, 156 tests)
- WS-CRAP-007: Workflow Engine Batch 2 (5 targets, 144 tests)
- Total: 57 target functions thinned, 116 pure functions extracted, 906 new Tier-1 tests
- Critical CRAP functions: 262 -> 140 (-46.6%)
- Total CRAP debt: 32,960 -> 11,864 (-64.0%)
- Post-execution CRAP analysis: docs/audits/2026-02-27-crap-scores-post-wp-crap-001.md

**COMPLETE:** WS-REGISTRY-002 -- story_backlog Retirement
- Fully retired story_backlog and story_detail document types
- 3 files deleted (handler, service, prompt dir), 18 files edited, 7 retirement tests
- Runtime bug fixed: production_service.py epic_id -> work_package_id
- Dead code removed: epic_context parameter in role_prompt_service.py

**COMPLETE:** Codebase Audit (pre/post WS-PIPELINE-003)
- Full audit documents in docs/audits/
- Registry integrity baseline established
- CRAP score baseline established (docs/audits/2026-02-26-crap-scores.md)

**COMPLETE:** Hygiene Cleanup
- ruff --fix: 469 auto-fixes across app/ and tests/
- Deleted dead files: primary_implementation_plan_handler.py, document_builder_backup.py, llm_execution_logger_original.py

**COMPLETE:** UI Constitution v2.0 Mock
- Standalone HTML at docs/branding/examples/floor-constitution-mock.html
- Design system docs in docs/branding/

**COMPLETE:** WS-SKILLS-001 -- Decompose CLAUDE.md into Claude Code Skills
**COMPLETE:** IPP Naming Standardization
**COMPLETE:** Admin Transcript Viewer Fix

**COMPLETE:** WS-METRICS-001 -- Developer Execution Metrics Collection and Storage
- Database schema (ws_executions, ws_bug_fixes) via Alembic migration
- PostgreSQL repository, service layer, API router (POST/GET endpoints)
- Dashboard, cost-summary, and scoreboard aggregation endpoints
- Idempotent phase updates, status/phase-name enum enforcement
- 30 verification tests covering all 15 criteria

**COMPLETE:** WS-PGC-SEC-002 -- Dual Gate Secret Ingress Control
**COMPLETE:** WS-PGC-SEC-002-A -- Secret Detector Calibration Spike
**COMPLETE:** WS-SDP-003 -- IA-Driven Tab Rendering + IPF Input Alignment
**COMPLETE:** ADR-053 / WS-SDP-001 / WS-SDP-002 -- Planning Before Architecture
**COMPLETE:** WS-OPS-001 -- Transient LLM Error Recovery and Honest Gate Outcomes
**COMPLETE:** ADR-050 -- Work Statement Verification Constitution (execution_state: complete)
**COMPLETE:** ADR-051 -- Work Package as Runtime Primitive
**COMPLETE:** ADR-052 -- Document Pipeline Integration for WP/WS
**COMPLETE:** WS-ONTOLOGY-001 through WS-ONTOLOGY-007
**COMPLETE:** WS-ADMIN-RECONCILE-001, WS-ADMIN-EXEC-UI-001
**COMPLETE:** WP-AWS-DB-001 -- Remote DEV/TEST database infrastructure

---

## Test Suite

- **~3453 tests** passing as of 2026-03-01 (906 new from WP-CRAP-001)
- 20 pre-existing failures (workflow definition validation, skills decomposition drift, ws_metrics migration)
- Tier 0: pytest has 1 pre-existing failure, lint has pre-existing issues, typecheck PASS, frontend PASS, registry PASS
- Mode B debt: SPA component tests use grep-based source inspection (no React test harness)

---

## WP-CRAP-001 Artifacts

### New Pure Function Modules (30 files)

| Module | Functions | WS |
|--------|----------:|-----|
| app/domain/workflow/nodes/qa_parsing.py | 8 | WS-CRAP-001 |
| app/domain/workflow/result_handling.py | 3 | WS-CRAP-001 |
| app/api/v1/services/render_pure.py | 4 | WS-CRAP-002 |
| app/api/v1/services/pgc_pure.py | 4 | WS-CRAP-002 |
| app/api/v1/services/intake_pure.py | 4 | WS-CRAP-002 |
| app/api/services/production_pure.py | 7 | WS-CRAP-003 |
| app/api/services/admin_workbench_pure.py | 3 | WS-CRAP-003 |
| app/api/services/service_pure.py | 8 | WS-CRAP-003 |
| app/domain/services/render_model_pure.py | 11 | WS-CRAP-005 |
| app/domain/services/document_builder_pure.py | 4 | WS-CRAP-005 |
| app/domain/services/prompt_assembler_pure.py | 4 | WS-CRAP-005 |
| app/web/routes/public/intake_pure.py | 11 | WS-CRAP-006 |
| app/web/routes/public/document_pure.py | 3 | WS-CRAP-006 |
| app/web/routes/public/workflow_build_pure.py | 5 | WS-CRAP-006 |
| app/web/routes/public/project_pure.py | 5 | WS-CRAP-006 |
| app/web/routes/public/view_pure.py | 3 | WS-CRAP-006 |
| app/domain/workflow/state_mapping.py | 4 | WS-CRAP-007 |
| app/domain/workflow/constraint_matching.py | 4 | WS-CRAP-007 |
| app/domain/workflow/document_assembly.py | 6 | WS-CRAP-007 |
| app/domain/workflow/nodes/semantic_qa_pure.py | 3 | WS-CRAP-007 |
| app/domain/workflow/nodes/gate_pure.py | 3 | WS-CRAP-007 |

### New Test Files (28 files, 906 tests)

Tests in tests/tier1/ -- all pure in-memory, no DB, no I/O.

---

## Verification Debt

| Item | Reason | Mechanization Plan |
|------|--------|--------------------|
| mypy type checking | Added to requirements.txt, not yet configured | Configure for app/, add to Tier 0 harness |
| SPA component tests (WS-007) | No React test harness | Source inspection proxy; upgrade to Jest + RTL when harness established |
| ExecutionList tests (WS-ADMIN-EXEC-UI-001) | No React test harness | Source inspection proxy; upgrade to Jest + RTL when harness established |

---

## Database Configuration

**Local dev** now uses AWS DEV database. The `.env` file no longer contains DATABASE_URL.

```bash
# Run app against AWS DEV
export DATABASE_URL=$(ops/scripts/db_connect.sh dev)
export ENVIRONMENT=dev_aws
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests against AWS DEV
export DATABASE_URL=$(ops/scripts/db_connect.sh dev)
python -m pytest tests/ -x -q
```

**AWS DEV database:**
- 36 tables created from current ORM models (includes ws_executions, ws_bug_fixes)
- 14 document types seeded (9 core + 5 BCP)
- `primary_implementation_plan` doc type renamed in document_types table (2026-02-24)
- Prompts are file-based from combine-config/ (no DB seeding needed)
- role_prompts/role_tasks tables are legacy (not used at runtime)

---

## Admin Panel Status

**Location:** `/admin` (SPA route, served by home_routes.py)

### Features Complete
- **Execution list** with full ID display, project code column, sortable headers, doc-type filter, search (WS-ADMIN-EXEC-UI-001)
- **Execution detail** with overview, transcript (full content by default, collapsible), QA coverage (WS-ADMIN-RECONCILE-001)
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

## Workflow Architecture

### Document Creation Workflows (DCWs)
- `concierge_intake` v1.4.0
- `project_discovery` v1.8.0
- `technical_architecture` v1.0.0
- `primary_implementation_plan` v1.0.0
- `implementation_plan` v1.0.0

### Project Orchestration Workflows (POWs)
- `intake_and_route` v1.0.0
- `software_product_development` v1.0.0

---

## React SPA Status

**Location:** `spa/` directory

### Features Complete
- All previous features through 2026-02-19
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
+-- ws_metrics_service.py          # WS execution metrics (dashboard, scoreboard, cost summary)
+-- secret_governance.py           # Orchestrator Tier-0 secret detection gate

app/core/
+-- secret_detector.py             # Canonical secret detector (entropy + char distribution + patterns)

app/api/middleware/
+-- secret_ingress.py              # HTTP ingress secret detection (Gate 1)

spa/src/components/
+-- DocumentNode.jsx               # Unified L1/L2 node (WP metadata display)
+-- WSChildList.jsx                # WS children sidecar tray
+-- Floor.jsx                      # Production floor layout

.claude/skills/                    # 10 Claude Code Skills (on-demand operational knowledge)

tests/tier1/handlers/
+-- test_work_package_handler.py   # 20 tests (WS-001)
+-- test_work_statement_handler.py # 21 tests (WS-002)
+-- test_project_logbook_handler.py # 24 tests (WS-003)
+-- test_ipp_wp_candidates.py      # 15 tests (WS-004)
+-- test_ipf_wp_reconcile.py       # 17 tests (WS-005)
+-- test_epic_feature_removal.py   # 21 tests (WS-006)
+-- test_production_floor_wp_ws.py # 17 tests (WS-007)

tests/tier1/
+-- test_secret_detector_calibration.py # 24 tests (WS-PGC-SEC-002-A)
+-- test_secret_dual_gate.py            # 39 tests (WS-PGC-SEC-002)
+-- test_ws_metrics.py                  # 30 tests (WS-METRICS-001)
+-- test_skills_decomposition.py        # 117 tests (WS-SKILLS-001)
```

---

## Key Technical Decisions

All previous decisions (1-45) plus:

46. **CRAP score testability refactoring** -- Extract pure data transformation logic from complex orchestrator methods into standalone `*_pure.py` modules. Original methods become thin wrappers that delegate. Pattern: Extract Pure Logic -> Write Tier-1 tests -> Thin original. This reduces both CC and increases coverage simultaneously.

---

## Quick Commands

```bash
# Run backend (AWS DEV)
cd ~/dev/TheCombine && source venv/bin/activate
export DATABASE_URL=$(ops/scripts/db_connect.sh dev)
export ENVIRONMENT=dev_aws
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Build SPA for production
cd spa && npm run build

# Run tests
export DATABASE_URL=$(ops/scripts/db_connect.sh dev)
python -m pytest tests/ -x -q

# Run Tier 0 verification harness
cd ~/dev/TheCombine && ./ops/scripts/tier0.sh

# Tier 0 with frontend check
./ops/scripts/tier0.sh --frontend

# Run CRAP analysis
python3 -m pytest tests/ -q --cov=app --cov-report=json:/tmp/combine_coverage.json --no-header
python3 -m radon cc app/ -j -n A > /tmp/combine_complexity.json
python3 ops/scripts/crap_analysis.py
```

---

## Handoff Notes

### Recent Work (2026-02-27 / 2026-03-01)
- WP-CRAP-001 fully executed: 7 Work Statements, 57 functions refactored, 906 new tests
- WS-CRAP-001 and WS-CRAP-002 executed directly in main
- WS-CRAP-003 through WS-CRAP-007 executed in parallel via worktree subagents, merged back
- WS-CRAP-007 had conflicting files (plan_executor.py, qa.py) with WS-CRAP-001 -- manually merged
- Post-execution CRAP analysis generated with delta comparison against baseline

### Recent Work (2026-02-26)
- Codebase audit (pre/post WS-PIPELINE-003): full inventory of orphaned artifacts
- WS-REGISTRY-002 executed: story_backlog + story_detail fully retired
- Runtime bug fixed: production_service.py:474 epic_id -> work_package_id
- Dead code removed: epic_context param, primary_implementation_plan_handler.py, 2 backup files
- ruff --fix: 469 lint auto-fixes
- UI Constitution v2.0 mock created
- Design system docs authored (docs/branding/)

### Next Work
- Commit WP-CRAP-001 changes (uncommitted: 33 modified files, 59 untracked files)
- Fix 20 pre-existing test failures (skills decomposition drift, workflow validation, ws_metrics migration)
- Top remaining CRAP targets: get_document_render_model (662.6), get_production_tracks (626.9), document_routes.get_document (500.8)
- Integrate Claude Code metrics reporting during WS execution
- Establish React test harness to retire Mode B debt on SPA tests
- Project Logbook as productized PROJECT_STATE.md for Combine-managed projects

### Open Threads
- TA emitting ADR candidates -- future work pinned in ADR-052
- MCP connector -- read-only document query layer as first step toward Claude Code integration
- "Send to Combine" clipboard prompt -- not yet authored
- Metrics API has no authentication -- acceptable for internal dev, needs auth before production

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files
- Sync IPP task prompt field names with IPP schema
- Configure mypy and resolve Verification Debt
- Clean up .claude/worktrees/ after confirming merges are complete

### Known Issues
- Two copies of IPF schema must be kept in sync
- IPP task prompt field names don't match IPP schema
- BCP pipeline still uses "epic"/"feature" as hierarchy level names (intentional, separate from document types)
- init_db.py schema.sql doesn't work on RDS (workaround: ORM-based creation)
- db_reset.sh can't DROP SCHEMA public on RDS (workaround: drop tables individually)
- Workflow definition validation warnings for intake_and_route and software_product_development (missing nodes/edges/entry_node_ids)
- `.gitignore` `*secret*` pattern requires explicit negation for every new file with "secret" in name

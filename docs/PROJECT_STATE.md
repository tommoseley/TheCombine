# PROJECT_STATE.md

**Last Updated:** 2026-02-23
**Updated By:** Claude (Secret detection + Metrics session)

## Current Focus

**COMPLETE:** WS-METRICS-001 -- Developer Execution Metrics Collection and Storage
- Database schema (ws_executions, ws_bug_fixes) via Alembic migration
- PostgreSQL repository, service layer, API router (POST/GET endpoints)
- Dashboard, cost-summary, and scoreboard aggregation endpoints
- Idempotent phase updates, status/phase-name enum enforcement
- 30 verification tests covering all 15 criteria

**COMPLETE:** WS-PGC-SEC-002 -- Dual Gate Secret Ingress Control
- Canonical detector module (`app/core/secret_detector.py`) with entropy + char distribution + known patterns
- HTTP ingress middleware (Gate 1) — scans POST/PUT/PATCH before persistence, returns 422 on detection
- Orchestrator governance gate (Gate 2) — HARD_STOP on secret detection at PGC/stabilization/render/replay
- PGC injection clauses (Tier-0, non-removable)
- Content-type-aware scanning (JSON, form-encoded, multipart skip)
- 39 verification tests covering all 13 criteria

**COMPLETE:** WS-PGC-SEC-002-A -- Secret Detector Calibration Spike
- Empirically determined thresholds: length=20, entropy=3.0, char_class_adjustment=0.85
- TPR=100%, FPR=0.00% on 5,500 prose + 675 secret corpus
- 24 verification tests

**COMPLETE:** WS-SDP-003 -- IA-Driven Tab Rendering + IPF Input Alignment
- Backend injects IA config (rendering_config, information_architecture) on all render-model API paths
- SPA routes to tabbed viewer when rendering_config present, renders from raw_content via IA binds
- IPF DCW inputs aligned with ADR-053: removed TA dependency, added project_discovery
- IPF task prompt, schemas, package.yaml all updated for IPP-only input baseline
- 34 IA tests + 5 IPF alignment tests passing

**COMPLETE:** ADR-053 / WS-SDP-001 / WS-SDP-002 -- Planning Before Architecture
- POW reordered: Discovery -> IPP -> IPF -> TA -> WPs (ADR-053 canonical order)
- IPF inputs updated (Discovery + IPP), TA inputs updated (Discovery + IPP + IPF)
- SPA audit confirmed no UI changes needed (no TA-before-IPF assumptions)

**COMPLETE:** WS-OPS-001 -- Transient LLM Error Recovery and Honest Gate Outcomes
**COMPLETE:** ADR-050 -- Work Statement Verification Constitution (execution_state: complete)
**COMPLETE:** ADR-051 -- Work Package as Runtime Primitive
**COMPLETE:** ADR-052 -- Document Pipeline Integration for WP/WS
**COMPLETE:** WS-ONTOLOGY-001 through WS-ONTOLOGY-007
**COMPLETE:** WS-ADMIN-RECONCILE-001, WS-ADMIN-EXEC-UI-001
**COMPLETE:** WP-AWS-DB-001 -- Remote DEV/TEST database infrastructure

---

## Test Suite

- **2476 tests** passing as of 2026-02-23 (prev 2286 + 24 calibration + 39 dual gate + 30 metrics + 97 other)
- Tier 0 harness passes clean (lint, tests, frontend build)
- Tier 1 tests cover all ontology work statements (6 criteria groups each)
- Mode B debt: SPA component tests use grep-based source inspection (no React test harness)

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
- 34 tables created from current ORM models (+ 2 pending: ws_executions, ws_bug_fixes via migration 20260223_001)
- 14 document types seeded (9 core + 5 BCP)
- Prompts are file-based from combine-config/ (no DB seeding needed)
- role_prompts/role_tasks tables are legacy (not used at runtime)

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
```

---

## Key Technical Decisions

All previous decisions (1-39) plus:

40. **Dual gate secret detection** -- Canonical detector invoked at HTTP ingress (middleware, pre-persistence) and orchestrator Tier-0 boundary (pre-stabilization, pre-render, replay). Both gates use same detector.
41. **Multi-factor secret detection** -- Pure entropy insufficient for hex strings; added character distribution analysis (char_class_count with mixed-charset adjustment) and context-aware exclusions (labeled hex, git refs, URLs, benign base64)
42. **Content-type-aware ingress scanning** -- Form-encoded bodies URL-decoded before scanning to avoid false positives from `+` signs; multipart/form-data skipped (binary content)
43. **Metrics persistence via PostgreSQL** -- WS execution metrics stored in PostgreSQL (not in-memory) via `PostgresWSMetricsRepository` with async session dependency injection

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

# Tier 0 allowing Mode B for missing tools
./ops/scripts/tier0.sh --allow-missing typecheck
```

---

## Handoff Notes

### Recent Work (2026-02-23)
- Merged 26 local + 20 remote workbench branches to main (all were subsets of one superset)
- GOV-SEC-T0-002 accepted, WS-PGC-SEC-002-A executed (calibration spike), WS-PGC-SEC-002 executed (dual gate)
- WS-METRICS-001 executed (execution metrics with PostgreSQL persistence)
- CLAUDE.md governance additions: Autonomous Bug Fixing, Subagent Usage, Metrics Reporting, Planning Discipline
- `.gitignore` updated with negation patterns for governance secret artifacts
- 2476 tests passing (190 new tests this session)

### Recent Work (2026-02-22)
- Bypassed DocDef layer: IA config injected on all render-model API paths, SPA renders tabs from raw_content via IA binds
- WS-SDP-003: IPF DCW inputs aligned with ADR-053 (removed TA, added project_discovery)
- IPF task prompt, schemas, and package.yaml updated for IPP-only baseline
- TechnicalArchitectureViewer gains raw content mode with envelope fallback
- 9 new tests (4 IA config + 5 IPF alignment)

### Next Work
- Apply Alembic migration `20260223_001` to DEV/TEST RDS databases
- Integrate Claude Code metrics reporting during WS execution (POST to `/api/v1/metrics/ws-execution`)
- Re-run IPF generation against corrected inputs (TA dependency removed)
- Establish React test harness to retire Mode B debt on SPA tests
- Project Logbook as productized PROJECT_STATE.md for Combine-managed projects
- WS as Combine document type (enables factory to author its own work)
- Fix init_db.py to use ORM-based creation on RDS (instead of stale schema.sql)
- Fix db_reset.sh to handle RDS permission model (can't DROP SCHEMA public)

### Open Threads
- TA emitting ADR candidates -- future work pinned in ADR-052
- MCP connector -- read-only document query layer as first step toward Claude Code integration
- "Send to Combine" clipboard prompt -- not yet authored
- Multi-LLM Sow tool -- explored, existing tools sufficient for now
- Metrics API has no authentication -- acceptable for internal dev, needs auth before production

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files
- Sync IPP task prompt field names with IPP schema
- Configure mypy and resolve Verification Debt

### Known Issues
- Two copies of IPF schema must be kept in sync
- IPP task prompt field names don't match IPP schema
- BCP pipeline still uses "epic"/"feature" as hierarchy level names (intentional, separate from document types)
- init_db.py schema.sql doesn't work on RDS (workaround: ORM-based creation)
- db_reset.sh can't DROP SCHEMA public on RDS (workaround: drop tables individually)
- Workflow definition validation warnings for intake_and_route and software_product_development (missing nodes/edges/entry_node_ids)
- `.gitignore` `*secret*` pattern requires explicit negation for every new file with "secret" in name


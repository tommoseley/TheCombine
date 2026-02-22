# PROJECT_STATE.md

**Last Updated:** 2026-02-21
**Updated By:** Claude (ADR-053 combine-config fix session)

## Current Focus

**COMPLETE:** ADR-053 / WS-SDP-001 / WS-SDP-002 -- Planning Before Architecture
- POW reordered: Discovery -> IPP -> IPF -> TA -> WPs (ADR-053 canonical order)
- IPF inputs updated (Discovery + IPP), TA inputs updated (Discovery + IPP + IPF)
- SPA audit confirmed no UI changes needed (no TA-before-IPF assumptions)

**COMPLETE:** WS-OPS-001 -- Transient LLM Error Recovery and Honest Gate Outcomes
- Automatic retry with exponential backoff (0.5s/2s/8s) on transient API errors (529, 5xx)
- `LLMOperationalError` raised on exhaustion with structured fields (provider, status_code, request_id, attempts)
- Intake gate returns honest `operational_error` outcome instead of silent regex fallback
- UI error panel with "temporarily unavailable" message and Retry button
- Fixed transport error retryability bug in AnthropicProvider

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

**COMPLETE:** WS-ONTOLOGY-001 through WS-ONTOLOGY-007
**COMPLETE:** WS-ADMIN-RECONCILE-001, WS-ADMIN-EXEC-UI-001

**COMPLETE:** WP-AWS-DB-001 -- Remote DEV/TEST database infrastructure
- DEV and TEST databases on AWS RDS (combine-devtest instance, Postgres 18.1)
- Credentials in AWS Secrets Manager, retrieved at runtime via ops/scripts/db_connect.sh
- Local dev now points at AWS DEV database (no local PostgreSQL needed)

---

## Test Suite

- **2277 tests** passing as of 2026-02-21 (14 from WS-OPS-001, 6 from WS-SDP-001, 3 from WS-SDP-002)
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
- 34 tables created from current ORM models
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
- `implementation_plan_primary` v1.0.0
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

All previous decisions (1-36) plus:

37. **AWS DEV database as local dev target** -- Local .env no longer contains DATABASE_URL; credentials fetched from Secrets Manager at runtime via db_connect.sh
38. **ORM-based schema bootstrap for fresh databases** -- init_db.py's schema.sql approach doesn't work on RDS; use Base.metadata.create_all() with all models imported instead
39. **Seed data uses column filtering** -- seed_document_types() filters dict keys to valid ORM columns, allowing seed data to carry metadata (creates_children, parent_doc_type) without breaking ORM construction

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

### Recent Work (2026-02-21)
- Fixed ADR-053 POW reorder: runtime definition in `combine-config/` was still TA-before-IPF; now corrected
- Parametrized `test_sdp_pow_order.py` to verify both seed and combine-config files (6 tests)
- Pushed fix to `workbench/ws-bb53d5bb1f83`

### Recent Work (2026-02-20)
- **ADR-053 / WS-SDP-001 / WS-SDP-002:** Planning Before Architecture — POW reordered, UI confirmed clean
- **WS-OPS-001:** Transient LLM error recovery — retry with backoff, honest gate outcomes, UI retry button
- Connected local dev to AWS DEV database (WP-AWS-DB-001 follow-up)
- Fixed ORM index bug in llm_logging.py (func.text → text in partial index WHERE clauses)
- Fixed seed_document_types() — column filtering, non-null builder_role/task for system types
- Resolved long-standing tier0 harness test failure (lint errors + ai.md tracking)
- 2271 tests passing

### Next Work
- Merge `workbench/ws-bb53d5bb1f83` to main (ADR-053 combine-config fix)
- Merge `workbench/ws-e583fd0642f5` to main (7 ontology commits + prior docs commit)
- Merge `workbench/ws-6b30ced080f1` to main (AWS DB + lint fixes)
- Mark ADR-051 and ADR-052 execution_state as complete
- Add Test-First Rule to AI.md (ADR-050 acceptance criterion 5)
- Add ADR-050 reference to POL-WS-001 (ADR-050 acceptance criterion 4)
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


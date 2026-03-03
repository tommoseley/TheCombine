# PROJECT_STATE.md

**Last Updated:** 2026-03-03
**Updated By:** Claude (WP-CRAP-002 testability refactoring)

## Current Focus

**COMPLETE:** WP-CRAP-002 -- Testability Refactoring: Workflow Engine Top 3 (2026-03-03)
- WS-CRAP-008: `_handle_result` CC 41→10, CRAP 967→49 (7 sub-methods, 17 tests)
- WS-CRAP-009: `_spawn_child_documents` CC 35→4, CRAP 710→10 (5 sub-methods + 3 pure helpers, 18 tests)
- WS-CRAP-010: `QANodeExecutor.execute` CC 36→7, CRAP 600→15 (5 check methods + 2 helpers, 20 tests)
- Combined: CC 112→21, CRAP 2,278→74 (-96.8%), F-grade functions 4→1
- 55 new Tier-1 tests (2,309 total passing), 0 existing tests broken
- New module: `child_document_helpers.py` (3 pure functions, 100% coverage)
- Post-refactoring audit: docs/audits/2026-03-03-crap-scores-post-wp-crap-002.md

**COMPLETE:** WS-WB-025 -- IA Contract Alignment (2026-03-03)
- 10 IA findings resolved: 2 CRITICAL, 1 HIGH, 3 MEDIUM, 1 LOW (3 deferred out of scope)
- Bug fix: WSResponse revision type mismatch (scalar int → dict normalization)

**COMPLETE:** CRAP Score Audit (2026-03-03, pre WP-CRAP-002)
- 147 critical, top 3 worst: _handle_result (967.4), _spawn_child_documents (710.1), QANodeExecutor.execute (600.1)
- Post WP-CRAP-002: 145 critical, F-grade 4→1, top 3 eliminated from rankings
- Reports: docs/audits/2026-03-03-crap-scores.md, docs/audits/2026-03-03-crap-scores-post-wp-crap-002.md

**COMPLETE:** WP-WB-002 -- Work Binder LLM Proposal Station Primitive
- WS-WB-020: document_readiness.py with is_doc_ready_for_downstream() (11 tests)
- WS-WB-021: WP schema ws_index[] declared + version bump (24 tests)
- WS-WB-022: task_execution_service.py with execute_task() primitive (8 tests)
- WS-WB-023: propose_work_statements@1.0.0 task prompt + meta
- WS-WB-024: 4 audit event types in wb_audit_service (33 tests)
- WS-WB-025: POST /work-binder/propose-ws endpoint + SPA wiring (16 tests)
- Total: 92 new tests, 3870 total passing, 0 failures
- IA verification: schema PASS, work_package IA section N/A (pre-existing gap)

**COMPLETE:** WS-WB-009 -- Work Binder Candidate Population
- GET /work-binder/candidates endpoint (read-only, returns WPCs with promoted flag via lineage)
- IMPORT CANDIDATES explicit button (no auto-import on GET)
- SPA: candidate display in WPIndex with amber sliver, promote action in WPContentArea

**COMPLETE:** WS-IAV-001 + WS-IAV-002 -- IA Verification Fix + IP Prompt Remediation
- IA verification skill Phase 1.1 fixed: bidirectional schema-to-document field diff
- IP task prompt rewritten to match collapsed pipeline (no IPP/TA reconciliation)
- candidate_reconciliation removed (function now in Work Binder promotion)
- Handler fix: removed transform field injection violating additionalProperties: false
- 18 Tier-1 tests, 7/7 original violations resolved, re-verification: 0 FAIL, 32 PASS, 4 LOW

**COMPLETE:** PGC QuestionTray Inline Rendering
- QuestionTray.jsx respects inline prop (no absolute positioning, no sidecar overlay)
- ContentPanel passes inline correctly

**COMPLETE:** WP-WB-001 -- Work Binder Operations
- WorkBinder SPA decomposed: monolithic WorkBinder.jsx -> 7 files (index, WPIndex, WPContentArea, WorkView, HistoryView, GovernanceView, CSS)
- Work Binder API routes (app/api/v1/routers/work_binder.py)
- WP/WS CRUD services, WP edition tracking, WS promotion, candidate import, audit service
- Governance invariant tests, schema evolution tests, work binder route tests
- WP 1.1.0, WS 1.1.0, WPC 1.0.0 schemas created in combine-config/schemas/

**COMPLETE:** Tier 0 Stabilization (2026-03-01)
- Ruff lint: 91 errors fixed across app/ and tests/ (F811, F841, F401, F403, E402, F821, E741)
- Workflow validation: allow null parent_doc_type for top-level entities, fix self-type iteration validator
- Registry: created work_package:1.1.0, work_statement:1.1.0, work_package_candidate:1.0.0 schemas
- Tests: updated WorkBinder assertions for decomposed components, fixed stale handler imports
- Tier 0 result: lint PASS, typecheck PASS, frontend PASS, registry PASS (63/63), pytest 3614 pass

**COMPLETE:** WP-CRAP-001 -- Testability Refactoring (7 Work Statements)
- Total: 57 target functions thinned, 116 pure functions extracted, 906 new Tier-1 tests
- Critical CRAP functions: 262 -> 140 (-46.6%)
- Total CRAP debt: 32,960 -> 11,864 (-64.0%)

**COMPLETE:** WS-REGISTRY-002 -- story_backlog Retirement
**COMPLETE:** Codebase Audit (pre/post WS-PIPELINE-003)
**COMPLETE:** Hygiene Cleanup
**COMPLETE:** UI Constitution v2.0 Mock
**COMPLETE:** WS-SKILLS-001 -- Decompose CLAUDE.md into Claude Code Skills
**COMPLETE:** IPP Naming Standardization
**COMPLETE:** Admin Transcript Viewer Fix
**COMPLETE:** WS-METRICS-001 -- Developer Execution Metrics Collection and Storage
**COMPLETE:** WS-PGC-SEC-002 -- Dual Gate Secret Ingress Control
**COMPLETE:** WS-PGC-SEC-002-A -- Secret Detector Calibration Spike
**COMPLETE:** WS-SDP-003 -- IA-Driven Tab Rendering + IPF Input Alignment
**COMPLETE:** ADR-053 / WS-SDP-001 / WS-SDP-002 -- Planning Before Architecture
**COMPLETE:** WS-OPS-001 -- Transient LLM Error Recovery and Honest Gate Outcomes
**COMPLETE:** ADR-050 -- Work Statement Verification Constitution
**COMPLETE:** ADR-051 -- Work Package as Runtime Primitive
**COMPLETE:** ADR-052 -- Document Pipeline Integration for WP/WS
**COMPLETE:** WS-ONTOLOGY-001 through WS-ONTOLOGY-007
**COMPLETE:** WS-ADMIN-RECONCILE-001, WS-ADMIN-EXEC-UI-001
**COMPLETE:** WP-AWS-DB-001 -- Remote DEV/TEST database infrastructure

---

## Quality Infrastructure

### Skills (Claude Code)
- **pressure-test**: Pre-flight WP validation (schema, prerequisites, dependency chain, execution risk)
- **ia-verification**: Post-flight conformance checking (schema shape, registry, API surface, governance)
- **crap-refactor**: CRAP score analysis + bounded refactoring WS generation
- 7 additional operational skills in .claude/skills/

### Quality Gates
- Pressure test → execution → IA verification → remediation → re-verification (proven cycle)
- IA verification found 7 violations in IP document, CC self-remediated from report (WS-IAV-002)
- Pressure test caught 6 execution bombs before WP-WB-001 implementation

---

## Test Suite

- **2309 Tier-1 tests** passing as of 2026-03-03 (55 new from WP-CRAP-002)
- Tier 0: pytest PASS, lint PASS, typecheck PASS, frontend PASS, registry PASS (64 assets)
- SPA: 626 modules, builds clean
- Mode B debt: SPA component tests use grep-based source inspection (no React test harness)

---

## Platform Primitives (New)

| Primitive | Location | Purpose |
|-----------|----------|---------|
| document_readiness | app/domain/services/document_readiness.py | Mechanical readiness gate for downstream consumption |
| task_execution | app/domain/services/task_execution_service.py | Reusable LLM task invocation outside workflow engine |
| wb_audit_service | app/domain/services/wb_audit_service.py | Structured audit events for Work Binder mutations |

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

## Architecture

```
app/domain/services/
+-- document_readiness.py          # is_doc_ready_for_downstream() gate
+-- task_execution_service.py      # execute_task() - reusable LLM primitive
+-- ws_proposal_service.py         # WS proposal station logic
+-- work_package_state.py          # WP state machine
+-- work_statement_state.py        # WS state machine
+-- work_statement_registration.py # WS-to-WP registration + rollup
+-- logbook_service.py             # Logbook CRUD
+-- ws_metrics_service.py          # WS execution metrics
+-- secret_governance.py           # Tier-0 secret detection gate

app/api/v1/routers/
+-- work_binder.py                 # Candidates, promote, propose-ws endpoints

spa/src/components/WorkBinder/
+-- index.jsx                      # Orchestrator (candidates + WPs)
+-- WPIndex.jsx                    # Left sidebar (CANDIDATES + PACKAGES sections)
+-- WPContentArea.jsx              # Center panel (WP detail + candidate detail + propose)
+-- WorkView.jsx                   # WS sheet list
+-- HistoryView.jsx                # Edition history
+-- GovernanceView.jsx             # Governance metadata
+-- WorkBinder.css                 # Styles

.claude/skills/
+-- ia-verification/SKILL.md       # Post-flight conformance verification
+-- wp-pressure-test/SKILL.md      # Pre-flight WP validation
+-- crap-refactor/skill.md         # CRAP analysis + refactoring
```

---

## Key Technical Decisions

All previous decisions (1-46) plus:

47. **IA verification as post-flight gate** -- Complements pressure test (pre-flight). Checks implementation artifacts against authoritative sources (schema, WS, ADR). Bidirectional field diff catches both missing and undeclared fields.

48. **Task execution primitive** -- Reusable service for LLM calls outside the workflow engine. Handles prompt loading, ADR-010 logging, output schema validation. Prevents router-level ad hoc LLM execution.

49. **Document readiness gate** -- Mechanical predicate (is_doc_ready_for_downstream) used by WB propose station and future gates. Replaces ambiguous "stabilized" concept.

50. **Promoted flag via lineage** -- Work Package promotion status computed from source_candidate_ids linkage, not derived ID naming. Survives rename/split/merge.

51. **Read-only candidate listing** -- GET /work-binder/candidates never mutates. Import is explicit POST action. Prevents audit noise from prefetch/retry.

52. **IA contract alignment as formal WS** -- Cross-layer drift (schema → API → frontend) treated as governed work, not ad hoc fixes. WS-WB-025 established the pattern: audit → WS → test-first fix → verify.

53. **File-level coverage as CRAP proxy** -- CRAP audits use file-level coverage as per-function proxy. More stable than AST-based per-function mapping across runs. May overestimate coverage for large files.

54. **importlib bypass for circular imports in tests** -- Tier-1 tests for plan_executor.py and qa.py use `importlib.util.spec_from_file_location` to avoid the `app.domain.workflow.__init__.py` circular import chain. Side effect: test coverage from these tests doesn't appear in file-level coverage reports.

---

## Handoff Notes

### Recent Work (2026-03-03)
- WP-CRAP-002 executed: 3 WSs decomposing workflow engine's 3 worst functions
  - _handle_result CC 41→10, _spawn_child_documents CC 35→4, QANodeExecutor.execute CC 36→7
  - 55 new Tier-1 tests, combined CRAP 2,278→74, F-grade functions 4→1
- WSResponse revision normalization bug fixed (scalar int → dict via Pydantic field_validator)
- WS-WB-025 executed: 7 IA contract fixes (2 CRITICAL, 1 HIGH, 3 MEDIUM, 1 LOW), 10 new tests
- CRAP score audits: pre + post WP-CRAP-002 comparison

### Next Work
- work_package IA section authoring (package.yaml information_architecture + rendering blocks, add to TIER1_DOC_TYPES)
- Portfolio agent IP: reject and redraft using fixed prompt
- Remaining CRAP targets: get_production_tracks (461), compare_runs (342), get_document (276), get_document_render_model (246)
- check_promotion_validity (CC=41, sole remaining F-grade) -- decomposition would eliminate all F-grade
- Zero-coverage files: admin.py, accounts.py, auth/routes.py, prompt_assembler.py, schema_resolver.py
- Industrial AI content: "What Is Industrial AI?" essay
- WarmPulse dogfood project

### Open Threads
- TA emitting ADR candidates -- future work pinned in ADR-052
- MCP connector -- read-only document query layer
- "Send to Combine" clipboard prompt
- Metrics API has no authentication
- Prompt governance rule: task prompts must not describe output field names (schema describes shape)
- Consultation Board concept (multi-model deliberation) -- post-beta

### Known Issues
- Two copies of IPF schema must be kept in sync
- BCP pipeline still uses "epic"/"feature" as hierarchy level names
- init_db.py schema.sql doesn't work on RDS
- db_reset.sh can't DROP SCHEMA public on RDS
- Workflow definition validation warnings for POWs
- `.gitignore` `*secret*` pattern requires explicit negation
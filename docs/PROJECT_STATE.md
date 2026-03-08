# PROJECT_STATE.md

**Last Updated:** 2026-03-08
**Updated By:** Claude (WS-WB-040 stabilization + Produce Next + breadcrumb pulse + Work Binder auto-import)

## Current Focus

**COMPLETE:** WS-WB-040 + Production UX Flow (2026-03-08)
- WP-level atomic stabilization: single "STABILIZE PACKAGE" replaces per-WS buttons (6 tests)
- "Produce Next" button on frontier completed documents (inline in header badge row)
- Pipeline breadcrumb pulsing animation for in-progress stages
- "Produce Work Binder" flow: TA complete → navigate to Work Binder + auto-import candidates

**COMPLETE:** Cross-Project Scoping + IA Audit + UX Tuning (2026-03-07)
- Cross-project scoping: all 9 work-binder endpoints accept project_id, SPA passes it on all calls
- QA remediation: outcome mismatch fix (gate remaps failed→fail, was breaking retry loop)
- IA audit: concierge_intake IA authored (5 sections), WP computed fields removed from IA
- IA contract tests: 42 tests verifying all package.yaml IA binds match production content
- Binder render 409 resolved (IA gate now passes all 9 projects, 64 documents)
- UX: sort by projectId, deep link after intake, collapsed sidebar improvements, user button simplified
- Startup banner: shows real DB config instead of stale sqlite fallback
- Binder Audit concept (CBA-1.0) scoped for future WS-RENDER-007 (mode=audit)

**COMPLETE:** Three Parallel WSs (2026-03-06)
- WS-RING0-002: Escalation wiring to QA circuit breaker + cancel endpoint (13 tests)
- WS-DEEPLINK-001: SPA cold-load deep link resolution
- WS-PROMPT-PROVENANCE-001: Full prompt provenance on builder_metadata (15 tests)

**COMPLETE:** CRAP Score Audit & Three-Tier Remediation (2026-03-06)
- Tier 1 (CC reduction): check_promotion_validity CC=41→10, get_document_render_model CC=26→14, get_production_tracks CC=25→14, _artifact_id_to_path CC=20→4
- Tier 2 (zero-coverage): 81 tests for 7 functions
- Tier 3 (partial-coverage): 97 tests for 7 functions
- Max CRAP dropped from 681.9 to 199.7 (-71%), CRAP>500 eliminated entirely
- New modules: render_pure.py, production_pure.py (extracted pure helpers)

**COMPLETE:** WS-GOV-001 — Governance Policies (2026-03-06)
- POL-QA-001: Testing & Verification Standard
- POL-CODE-001: Code Construction Standard
- POL-ARCH-001: Architectural Integrity Standard
- 3 new policies in docs/policies/ (pending move to combine-config/policies/ per WS-RENDER-006)

**COMPLETE:** WS-RENDER-005 — Binder WS Inclusion (2026-03-06)
- Fixed data matching: endpoint passes id/parent_document_id to renderer
- Added parent_document_id fallback in _get_ordered_ws()
- 12 new tests for WS nesting in binder output

**COMPLETE:** Markdown Render Pipeline (WS-RENDER-001 through WS-RENDER-004, 2026-03-05)
- WS-RENDER-001: markdown_renderer.py — 7 block renderers (paragraph, list, ordered-list, table, key-value-pairs, nested-object, card-list), pure function
- WS-RENDER-002: binder_renderer.py — cover block, TOC, pipeline-ordered assembly, WS nesting under WPs
- WS-RENDER-003: ia_gate.py — verify_document_ia() with 50% coverage threshold, PASS/FAIL/SKIP
- WS-RENDER-004: evidence_renderer.py — YAML frontmatter (SHA-256 source_hash), Evidence Index table
- Render endpoints: single doc + binder, format=md, mode=standard|evidence
- Download dropdowns: FullDocumentViewer, ConfigDrivenDocViewer, Floor.jsx (binder) — all support standard/evidence
- IA audit: all 4 document types with IA (project_discovery, implementation_plan, technical_architecture, work_package) fully ADR-054 compliant
- 52 new render pipeline tests, 3883 total passing

**COMPLETE:** Studio Layout Phase 2: ProjectTree Auto-Collapse + Pipeline Breadcrumb (2026-03-05)
- ProjectTree auto-collapses to 48px icon rail when project active
- PipelineBreadcrumb replaces 320px vertical PipelineRail in Work Binder mode
- Reclaims ~530px horizontal space for Work Binder content
- WorkBinder progressive disclosure: WSDetailView, wsUtils extracted

**COMPLETE:** WS-WEB-CLEANUP-001 -- Remove Dead Jinja2/HTMX Layer (2026-03-05)
- Deleted entire app/web/ directory (routes, templates, static, BFF, viewmodels)
- Deleted dead magic-link auth router (app/api/routers/auth.py)
- Removed 13 orphaned test files, removed USE_LEGACY_TEMPLATES config flag
- Confirmed zero Jinja2 route hits via instrumentation during full PGC flow
- 3808 tests passing, IA audit 75/75

**COMPLETE:** WP-ONTOLOGY-CLEANUP (2026-03-05)
- WS-ONTOLOGY-001: "slug" → "project_id" in ADR-055/056/057, ROUTING_CONTRACT, WS docs. Registered `edition` in ADR-057.
- WS-ONTOLOGY-002: instance_id → display_id in work_binder.py (0 instance_id refs remaining), projects.py, production_pure/service.
- Migration 20260305_001: Dropped legacy idx_documents_latest_single/multi (superseded by idx_documents_latest_display)

**COMPLETE:** WP-ROUTE-001 -- Unified Routing v2 (ADR-056) (2026-03-05)
- WS-ROUTE-001 through WS-ROUTE-005 implemented (previous session)
- Fixed _resolve_project() duplicate function shadow crash (swapped args)
- Removed INSERT PACKAGE button (no backend POST endpoint)
- Fixed Concierge Intake rendering: arrays as bullet lists instead of JSON.stringify
- Fixed white screen on empty Work Binder (stale showInsertForm reference)
- HTMX admin removal tests updated for SPA catch-all (route table check)
- Production migration 20260304_001 applied manually
- Deployed to production, all CI green, smoke test passed

**COMPLETE:** WP-ID-001 -- Document Identity Standard (ADR-055) (2026-03-04)
- WS-ID-001 through WS-ID-005: migration, service, wiring, legacy removal, DB reset
- DB infrastructure: db_dump_schema.sh, db_reset.sh (RDS-safe), db_migrate.sh (schema.sql bootstrap)
- QA prompt fix: project_discovery_qa v1.2.0
- Batch display_id fix: propose_work_statements mints first, increments locally

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

- **4215+ Tier-1 tests** passing as of 2026-03-07 (56+ new: IA contract + scoping + QA remediation)
- Tier 0: pytest PASS, lint PASS, typecheck PASS, frontend PASS, registry PASS
- SPA: builds clean
- Mode B debt: SPA component tests use grep-based source inspection (no React test harness)

---

## Platform Primitives (New)

| Primitive | Location | Purpose |
|-----------|----------|---------|
| display_id_service | app/domain/services/display_id_service.py | Human-readable document identity minting (ADR-055) |
| document_readiness | app/domain/services/document_readiness.py | Mechanical readiness gate for downstream consumption |
| task_execution | app/domain/services/task_execution_service.py | Reusable LLM task invocation outside workflow engine |
| wb_audit_service | app/domain/services/wb_audit_service.py | Structured audit events for Work Binder mutations |
| markdown_renderer | app/domain/services/markdown_renderer.py | IA-driven Markdown block rendering (7 render_as types) |
| binder_renderer | app/domain/services/binder_renderer.py | Project binder assembly (cover, TOC, pipeline ordering) |
| ia_gate | app/domain/services/ia_gate.py | IA coverage verification gate (50% threshold) |
| evidence_renderer | app/domain/services/evidence_renderer.py | Evidence mode frontmatter + index generation |

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
+-- display_id_service.py          # mint_display_id(), parse/resolve (ADR-055)
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

55. **Document Identity Standard (ADR-055)** -- Human-readable display_id ({PREFIX}-{NNN}) replaces UUID-based identity for user-facing contexts. Lazy imports to avoid circular chains. Batch minting queries MAX once, increments locally.

56. **RDS-safe DB reset** -- Individual object drops with pg_depend extension filtering instead of DROP SCHEMA CASCADE (RDS users don't own public schema). Schema bootstrap from pg_dump output instead of init_db.py.

57. **IA-driven Markdown rendering** -- Render pipeline walks IA sections and dispatches to block renderers by render_as type. Pure functions, deterministic output. Evidence mode adds YAML frontmatter with SHA-256 source hash for provenance tracing.

58. **IA gate coverage threshold** -- 50% of IA-declared fields must be present for PASS. Missing fields above threshold are warnings (rendered sections omitted gracefully). Below threshold is FAIL (409 Conflict). Catches broken documents while tolerating optional fields.

---

## Handoff Notes

### Recent Work (2026-03-08)
- WS-WB-040: WP-level atomic stabilization (backend endpoint + frontend button, 6 tests)
- "Produce Next" button: frontier-only, inline in document header badge row
- Pipeline breadcrumb pulsing for in-progress stages
- "Produce Work Binder" button on TA complete → auto-import candidates
- All changes uncommitted

### Next Work
- Commit session changes (WS-WB-040 + production UX flow)
- WS-RENDER-007: Binder Audit mode (mode=audit) — mechanical governance/traceability/readiness checks
- Remaining CRAP targets: 18 functions with CRAP>100 (coverage debt, moderate CC 11-14)
- Three download dropdown components could be consolidated into shared component

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
- init_db.py is obsolete for bootstrap (replaced by schema.sql loading) — should be removed or updated
- document_types seed data in loader.py INITIAL_DOCUMENT_TYPES stale (2 entries, no display_prefix)
- Workflow definition validation warnings for POWs
- `.gitignore` `*secret*` pattern requires explicit negation
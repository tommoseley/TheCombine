# Codebase Audit Summary -- 2026-02-26 (Post WS-PIPELINE-003)

**Branch:** `workbench/ws-b12f2a74613a`
**Scope:** Full codebase -- READ-ONLY audit
**Baseline:** `docs/audits/2026-02-26-audit-summary.md` (pre-PIPELINE-003)
**Tools:** ruff (F401/F841), grep, cross-reference scripts, registry integrity checker
**Context:** Run after completing WS-PIPELINE-003 (Legacy Ontology Cleanup -- Epic/Feature/Backlog Removal)

---

## Delta vs Previous Audit

### Resolved Findings

| # | Previous Finding | Severity | Resolution |
|---|-----------------|----------|------------|
| 3 | Missing config artifacts: `backlog_item` prompts, `plan_explanation` prompts | High | **Resolved** -- both `backlog_item/` and `plan_explanation/` directories deleted by WS-PIPELINE-003 |
| 6 | `epic` in active_releases with no handler | Medium | **Resolved** -- `epic` removed from active_releases and config directory deleted |
| 6 | `feature` in active_releases with no handler | Medium | **Resolved** -- `feature` removed from active_releases and config directory deleted |
| 7 | Orphan `primary_implementation_plan` config chain (5 dirs) | High | **Partially resolved** -- all 5 config directories deleted. Handler file on disk (`primary_implementation_plan_handler.py`) still exists (deferred) |
| 12 | 3 orphan workflow directories (`feature_set_generator`, `story_set_generator`, `primary_implementation_plan`) | Medium | **Resolved** -- all 3 deleted |
| 12 | Orphan task prompt directories (`feature_set_generator`, `story_set_generator`, `primary_implementation_plan`) | Medium | **Resolved** -- all deleted |
| 12 | Orphan PGC directory (`primary_implementation_plan.v1`) | Medium | **Resolved** -- deleted |
| 12 | Orphan schema directory (`primary_implementation_plan`) | Medium | **Resolved** -- deleted |

### Changed Severity

| # | Finding | Previous | Current | Notes |
|---|---------|----------|---------|-------|
| 19 | Unused imports (ruff F401) | 211 | 208 | Down 3 (cleanup from deleted files) |
| 17 | Orphan config entries | 7 | 1 | Down 6 -- epic, feature, backlog_item, plan_explanation, feature_set_generator, story_set_generator removed. `schemas/registry/` remains (contains registry schemas, not an orphan -- reclassified) |
| 27 | Total test functions | 2,570 | 2,517 | Down 53 -- test files for deleted document types removed |

### New Findings

| # | Finding | Severity | Notes |
|---|---------|----------|-------|
| N1 | 54 remaining `epic` references in `app/` (excluding story_backlog and commands.py) | Medium | Spread across persistence models, LLM thread models, role_prompt_service, production_service, document_routes, registry/loader (story_backlog schema). Mostly in deferred subsystems (story_backlog, commands) |
| N2 | 514 `epic` references in `tests/` (excluding story_backlog and test_epic_feature_removal) | Low | Expected: test files for deferred story_backlog functionality |
| N3 | `app/domain/handlers/base_handler.py:431` still references `epic_id` in docstring | Low | Single docstring example |
| N4 | 6 pre-existing workflow test failures (SPD V9 validation) | Medium | Root cause: WS-PIPELINE-001 changed iteration structure without updating `may_own`/`collection_field` |
| N5 | 616 hardcoded hex colors in SPA (up from 358) | Medium | Recount with broader pattern -- previous audit may have used narrower regex |

### Unchanged Findings (Carried Forward)

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Missing task prompt dirs: `work_package`, `work_statement` | High | Unchanged |
| 2 | Missing global schema dirs: `work_package`, `work_statement` | High | Unchanged |
| 4 | API layer: 115 unused imports (was 119) | High | Slight improvement |
| 5 | Mech handlers entirely untested (11 files, 0%) | High | Unchanged |
| 8 | `story_backlog` not in governed config | High | Unchanged (deferred to WS-REGISTRY-002) |
| 9 | Handler test coverage at 33% | Medium | Unchanged |
| 10 | Tier 2 nearly empty | Medium | Unchanged |
| 11 | SPA has zero JS test infrastructure | Medium | Unchanged |
| 13 | Backup files on disk | Medium | Unchanged |
| 14 | Auth provider coverage at 50% | Medium | Unchanged |
| 15 | Web/BFF routes 73% untested | Medium | Unchanged |

---

## Health Score

| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Unused imports (ruff F401) | 211 | 208 | -3 |
| Unused variables (ruff F841) | 17 | 8 | -9 |
| Orphan Python modules (backup/dead files) | 3 | 3 | 0 |
| Orphan config entries (dirs not in active_releases) | 7 | 1 | -6 |
| Config without runtime consumer | 3 | 0 | -3 |
| Missing config artifacts (declared but absent) | 4 | 2 | -2 |
| Unregistered handlers (file exists, not in registry) | 1 | 1 | 0 |
| Handlers with no config entry | 2 | 2 | 0 |
| Hardcoded hex colors in SPA | 358 | 616 | +258 (recount) |
| Registry integrity (active_releases) | -- | 62/62 PASS | -- |
| Total test functions | 2,570 | 2,517 | -53 |
| Test results | -- | 20 fail, 2464 pass, 33 skip | -- |
| Pre-existing failures | -- | 20 (13 skills, 6 workflow, 1 metrics) | -- |

---

## Findings by Subsystem

---

### 1. Document Generation (Handlers + Domain Services)

**Files:** `app/domain/handlers/`, `app/domain/services/`

#### Dead Code

| File | Line | Finding | Code |
|------|------|---------|------|
| `app/domain/handlers/base_handler.py` | 29 | Unused import `DocumentTransformError` | F401 |
| `app/domain/handlers/base_handler.py` | 30 | Unused import `DocumentRenderError` | F401 |
| `app/domain/handlers/story_backlog_handler.py` | 10 | Unused imports `List`, `Optional` | F401 |
| `app/domain/services/document_builder.py` | 514 | Unused variable `html` | F841 |
| `app/domain/services/prompt_assembler.py` | 16 | Unused import `field` | F401 |
| `app/domain/services/schema_resolver.py` | 14 | Unused import `AsyncSession` | F401 |
| `app/domain/services/staleness_service.py` | 9 | Unused import `Set` | F401 |
| `app/domain/services/story_backlog_service.py` | 10,12,24,462 | 4 unused imports | F401 |
| `app/domain/services/thread_execution_service.py` | 11,12,15,25 | 4 unused imports | F401 |

F401 by directory: `handlers/` = 4, `services/` = 11.

**Backup files (still present):**
- `app/domain/services/document_builder_backup.py` -- backup copy, not imported anywhere
- `app/domain/services/llm_execution_logger_original.py` -- backup copy, not imported anywhere

#### Orphan Config

- **`primary_implementation_plan_handler.py`** exists on disk but is NOT registered in `registry.py` HANDLERS dict (unchanged from previous audit)
- **`story_backlog`** handler is registered in `registry.py` but has NO entry in `active_releases.document_types` (deferred to WS-REGISTRY-002)
- **`project_logbook`** handler is registered in `registry.py` but has NO entry in `active_releases` AND no directory under `combine-config/document_types/` (unchanged)

**RESOLVED:** `epic` and `feature` config-without-consumer findings are resolved -- both removed from active_releases.

#### Test Coverage

| Scope | Files | Tested | Coverage |
|-------|-------|--------|----------|
| `app/domain/handlers/` | 13 (was 15) | 5 | **38%** (was 33%) |
| `app/domain/services/` | ~20 | ~11 | **55%** |

Handler count dropped from 15 to 13: `backlog_item_handler.py` and `plan_explanation_handler.py` deleted.

---

### 2. Workflow Engine

**Files:** `app/domain/workflow/`

#### Dead Code (23 unused imports)

| File | Count | Notable |
|------|-------|---------|
| `workflow_executor.py` | 6 | `Any`, `List`, `Tuple`, `IterationInstance`, `ExecutionResult` |
| `nodes/task.py` | 2 | Unused vars `issue_type`, `qid` (F841) |
| `nodes/mock_executors.py` | 2 | `List`, `Optional` |
| `pg_state_persistence.py` | 2 | `Any`, `Dict` |
| `thread_manager.py` | 2 | `uuid4`, `ThreadExecutionService` |
| `plan_validator.py` | 2 | `Optional`, unused var `end_node_ids` |
| `interrupt_registry.py` | 3 | `field`, `Project`, `WorkflowExecution` |
| Other (4 files) | 4 | Various typing/dataclass imports |

#### Orphan Config

**RESOLVED:** All 3 orphan workflow directories removed by WS-PIPELINE-003:
- ~~`combine-config/workflows/feature_set_generator/`~~ deleted
- ~~`combine-config/workflows/story_set_generator/`~~ deleted
- ~~`combine-config/workflows/primary_implementation_plan/`~~ deleted

**Remaining:** Stale version directories on disk (superseded by active versions):
- `concierge_intake/releases/1.3.0/` (active: 1.4.0)
- `project_discovery/releases/1.8.0/` (active: 2.0.0)
- `technical_architecture/releases/1.0.0/` (active: 2.0.0)

#### Pre-existing Test Failures

6 workflow tests fail due to SPD V9 iteration validation (root cause: WS-PIPELINE-001):
- `test_load_file_from_real_workflow`
- `test_loads_from_real_directory`
- `test_get_returns_workflow`
- `test_valid_workflow_passes`
- `test_ancestor_reference_permitted`
- `test_same_scope_context_permitted`

---

### 3. Config Registry

**Files:** `app/config/`, `combine-config/`

#### Active Releases Summary

| Section | Count |
|---------|-------|
| document_types | 9 (was 13) |
| roles | 7 |
| schemas | 19 |
| workflows | 8 (was 11) |
| tasks | 19 |
| pgc | 3 (was 4) |
| mechanical_ops | 15 |
| templates | 3 |
| **Total** | **83 (was 89)** |

Registry integrity: **62/62 PASS** (all active_releases entries resolve to existing artifacts).

#### Alignment Check

| Section | Status |
|---------|--------|
| document_types | ALIGNED (9 dirs, 9 entries) |
| workflows | ALIGNED (8 dirs, 8 entries) |
| mechanical_ops | ALIGNED (15 dirs, 15 entries) |
| schemas | 1 extra dir: `registry/` (contains registry meta-schemas, not a document type schema -- intentional) |

**RESOLVED:** All orphan config directories from previous audit have been deleted:
- ~~`document_types/epic/`~~ ~~`feature/`~~ ~~`backlog_item/`~~ ~~`plan_explanation/`~~ ~~`primary_implementation_plan/`~~ all deleted
- ~~`workflows/feature_set_generator/`~~ ~~`story_set_generator/`~~ ~~`primary_implementation_plan/`~~ all deleted
- ~~`prompts/tasks/feature_set_generator/`~~ ~~`story_set_generator/`~~ ~~`primary_implementation_plan/`~~ all deleted
- ~~`prompts/pgc/primary_implementation_plan.v1/`~~ deleted
- ~~`schemas/primary_implementation_plan/`~~ deleted

#### Missing Config (Still Present)

| Section | Key | Expected Path | Status |
|---------|-----|---------------|--------|
| tasks | `work_package` | `combine-config/prompts/tasks/work_package/` | **MISSING** |
| tasks | `work_statement` | `combine-config/prompts/tasks/work_statement/` | **MISSING** |

Note: `work_package` and `work_statement` have embedded schemas at their `document_types` paths, but no global task prompt directories. This is unchanged from the previous audit.

---

### 4. SPA Floor

**Files:** `spa/src/`

#### Component Inventory

| Category | Count |
|----------|-------|
| Top-level components | 21 |
| Block components | 24 |
| Admin components | (subdir) |
| Concierge components | (subdir) |
| Viewers | (subdir) |

#### Hardcoded Hex Colors

**616 hardcoded hex color values** across SPA source files (`.jsx`, `.js`, `.css`). Previous audit reported 358 -- likely used a narrower regex or fewer file types.

#### Unused Utilities (unchanged)

| File | Status |
|------|--------|
| `spa/src/utils/layout.js` | Unused (0 importers) |
| `spa/src/utils/mockData.js` | Unused (test fixture only) |
| `spa/src/utils/factories.js` | Unused (test fixture only) |
| `spa/src/hooks/useFloorSSE.js` | Unused (0 importers) |

#### Test Coverage

**Zero JavaScript test infrastructure.** No Jest, Vitest, or other JS test runner detected. Unchanged.

---

### 5. API Layer

**Files:** `app/api/`, `app/api/v1/`

#### Dead Code (115 unused imports -- largest subsystem)

F401 distribution:

| Area | Count |
|------|-------|
| `app/api/v1/` | 45 |
| `app/api/services/` | 44 |
| `app/api/routers/` | 15 |
| `app/api/models/` | 8 |
| `app/api/middleware/` | 2 |
| `app/api/repositories/` | 1 |

F841 unused variables (3):
- `app/api/services/role_prompt_service.py` -- unused `pipeline_id`
- `app/api/services/mech_handlers/executor.py` -- unused `op_type`
- `app/api/services/release_service.py` -- unused `package`

#### Mech Handlers: Entirely Untested (unchanged)

`app/api/services/mech_handlers/` has 11 source files and zero test files.

#### Test Coverage (unchanged)

| Scope | Files | Tested | Coverage |
|-------|-------|--------|----------|
| `app/api/` (all) | ~110 | ~47 | **43%** |
| `app/api/services/mech_handlers/` | 11 | 0 | **0%** |
| `app/api/middleware/` | 4 | 0 | **0%** |

---

### 6. Auth

**Files:** `app/auth/`

#### Dead Code (17 unused imports -- unchanged)

| File | Count |
|------|-------|
| `app/auth/service.py` | 5 |
| `app/auth/db_models.py` | 4 |
| `app/auth/middleware.py` | 4 |
| Other (4 files) | 4 |

#### Test Coverage: 50% (unchanged)

---

### 7. Web/BFF Layer

**Files:** `app/web/`

- 8 unused imports (was 9 -- slight improvement)
- `app/web/routes/public/document_routes.py` still contains story_backlog auto-init from EpicBacklog (deferred)
- Jinja2 template routes largely superseded by SPA

---

### 8. Persistence Layer

**Files:** `app/persistence/`, `app/domain/repositories/`

- 7 unused imports in `app/persistence/` (pg_repositories: 7)
- 4 unused imports in `app/domain/repositories/`

---

## Cross-Cutting Reference Audit

### Term: `epic` / `Epic`

| Area | Count | Status |
|------|-------|--------|
| `app/` (excl. story_backlog, commands) | 54 refs | Partially cleaned |
| `tests/` (excl. story_backlog, removal test) | 514 refs | Deferred (story_backlog tests) |
| `combine-config/` | 0 | **Fully cleaned** |
| `active_releases.json` | 0 | **Fully cleaned** |

Key remaining locations:
- `app/persistence/models.py` -- Thread model docstrings and field comments (4 refs)
- `app/api/models/llm_thread.py` -- Thread model docstrings and field comments (4 refs)
- `app/api/models/document.py` -- instance_id doc comment (2 refs)
- `app/api/services/role_prompt_service.py` -- `epic_context` parameter and formatting (8 refs)
- `app/api/services/production_service.py` -- epic context and spawner logic (4 refs)
- `app/api/v1/schemas/workflow.py` -- scope hierarchy includes "epic" (1 ref)
- `app/api/v1/routers/projects.py` -- `epic_id` in content extraction (2 refs)
- `app/domain/registry/loader.py` -- story_backlog schema references (12 refs)
- `app/web/routes/public/document_routes.py` -- story_backlog auto-init (15 refs)
- `app/api/routers/commands.py` -- story_backlog commands (20+ refs, entire file is story_backlog)

**Verdict:** Config layer fully cleaned. Runtime code references are entirely in story_backlog-adjacent code (deferred to WS-REGISTRY-002) or generic docstring examples.

### Term: `feature_spec` / `FeatureSpec` / `backlog_item` / `BacklogItem` / `plan_explanation` / `PlanExplanation`

| Area | Count | Status |
|------|-------|--------|
| `app/` | 0 | **Fully removed** |
| `combine-config/` | 0 | **Fully removed** |
| `active_releases.json` | 0 | **Fully removed** |

**Verdict:** Complete removal. These terms are extinct in the codebase.

### Term: `primary_implementation_plan`

| Area | Status |
|------|--------|
| `combine-config/` (all dirs) | **Fully removed** |
| `active_releases.json` | **Removed** |
| `app/domain/handlers/primary_implementation_plan_handler.py` | Still on disk, NOT registered |
| `app/` code references | 4 references (down from prior audit) |

**Verdict:** Config fully cleaned. Handler file orphaned on disk (deferred to WS-CLEANUP-EFS-001 or similar).

### Term: `story_backlog`

| Area | Status |
|------|--------|
| `app/domain/handlers/story_backlog_handler.py` | Registered in `registry.py` |
| `app/domain/services/story_backlog_service.py` | Active service |
| `app/api/routers/commands.py` | StoryBacklog init + generate commands |
| `app/web/routes/public/document_routes.py` | Auto-init from EpicBacklog |
| `combine-config/_active/active_releases.json` | **NOT PRESENT** |
| `combine-config/document_types/` | **NO directory** |

**Verdict:** Unchanged from previous audit. Lives entirely in code, not governed config. Deferred to WS-REGISTRY-002.

### Term: `ArchitecturalSummaryView`

| Area | File | Status |
|------|------|--------|
| `app/core/middleware/deprecation.py` | Deprecation route mapping | Active |
| `app/web/routes/public/document_routes.py` | Hardcoded `view_docdef` | Active |

**Verdict:** Reduced from 3 app files to 2. Removed from `projects.py` hardcoded fallback dict.

---

## Critical (Act Now)

1. **Missing task prompt directories:** `work_package` and `work_statement` are in `active_releases.tasks` but have NO directory at `combine-config/prompts/tasks/`. (Carried forward, unchanged)

2. **Missing global schema directories:** `work_package` and `work_statement` are in `active_releases.schemas` but have NO directory at `combine-config/schemas/`. (Carried forward, unchanged)

## High (Act Soon)

3. **API layer: 115 unused imports** -- largest dead code concentration. (Slight improvement from 119, carried forward)

4. **Mech handlers entirely untested** -- 11 files in `app/api/services/mech_handlers/` with zero test coverage. (Carried forward)

5. **`story_backlog` not in governed config** -- handler registered, service exists, but no `active_releases` entry or `combine-config/document_types/` directory. (Deferred to WS-REGISTRY-002)

6. **6 pre-existing workflow test failures** -- SPD V9 iteration validation broken since WS-PIPELINE-001. Root cause: `work_package` doc type lacks `collection_field`/`may_own` entries expected by validator.

## Medium (Track as Debt)

7. **54 remaining `epic` references in `app/`** -- mostly in story_backlog-adjacent code. Will be cleaned when story_backlog is resolved (WS-REGISTRY-002).

8. **Handler test coverage at 38%** -- 8 of 13 handlers untested (improved from 10/15 by deleting untested handlers).

9. **Tier 2 nearly empty** -- only 2 files and 13 test functions. (Unchanged)

10. **SPA has zero JS test infrastructure.** (Unchanged)

11. **Backup files on disk** -- `document_builder_backup.py`, `llm_execution_logger_original.py` are dead code. (Unchanged)

12. **Auth provider coverage at 50%.** (Unchanged)

13. **Web/BFF routes 73% untested.** (Unchanged)

14. **616 hardcoded hex colors in SPA.** (Recount -- broader regex than previous audit)

15. **Orphan handler file** -- `primary_implementation_plan_handler.py` exists on disk but is not registered. (Unchanged)

## Low (Informational)

16. **Stale workflow version directories** -- old versions on disk. (Unchanged)

17. **SPA orphan components** -- same as previous audit. (Unchanged)

18. **Unused SPA utilities** -- `layout.js`, `mockData.js`, `factories.js`, `useFloorSSE.js`. (Unchanged)

19. **208 total unused imports** across the Python codebase. (Down from 211)

20. **13 skills_decomposition test failures + 1 ws_metrics** -- pre-existing, related to CLAUDE.md skill extraction.

---

## Test Summary

| Metric | Value |
|--------|-------|
| Tests collected | 2,517 (was 2,570) |
| Tests deselected | 26 |
| Tests passed | 2,464 |
| Tests failed | 20 |
| Tests skipped | 33 |
| Pre-existing failures | 20 (13 skills_decomposition, 6 workflow, 1 ws_metrics) |
| New failures from WS-PIPELINE-003 | **0** |

---

## Recommended Work Statements (Updated)

### Resolved by WS-PIPELINE-003
- ~~WS-CLEANUP-ORPHAN-CONFIG~~ (partially) -- orphan config dirs for epic/feature/backlog_item/plan_explanation/primary_implementation_plan all deleted

### Still Recommended

1. **WS-REGISTRY-002** (story_backlog): Decide fate of story_backlog -- either add to governed config or retire handler+service+commands+routes. Will also clean 54+ `epic` references in app/.

2. **WS-CLEANUP-DEAD-IMPORTS**: Run `ruff check app/ --select F401,F841 --fix` to auto-remove 208 unused imports and 8 unused variables.

3. **WS-SPA-THEME-COMPLIANCE**: Replace 616 hardcoded hex colors in SPA components with CSS variable references.

4. **WS-TEST-MECH-HANDLERS**: Write Tier 1 tests for `app/api/services/mech_handlers/` (11 files, 0% coverage).

5. **WS-CLEANUP-BACKUP-FILES**: Remove `document_builder_backup.py`, `llm_execution_logger_original.py`, and `primary_implementation_plan_handler.py`.

6. **WS-WORKFLOW-V9-FIX**: Fix SPD workflow V9 validation -- add `collection_field`/`may_own` to work_package doc type or update validator expectations. Resolves 6 pre-existing test failures.

---

_Audit generated by codebase-auditor skill. All findings are read-only observations -- no code was modified._

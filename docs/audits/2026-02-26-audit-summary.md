# Codebase Audit Summary -- 2026-02-26

**Branch:** `workbench/ws-b12f2a74613a`
**Scope:** Full codebase -- READ-ONLY audit
**Tools:** ruff (F401/F841), vulture (80%+ confidence), grep, cross-reference scripts
**Modules run:** Dead Code, Orphan Config, SPA Dependencies, Test Coverage, Cross-Cutting References

---

## Health Score

| Metric | Count | Severity |
|--------|-------|----------|
| Unused imports (ruff F401) | 211 | Medium |
| Unused variables (ruff F841 + vulture) | 17 | Medium |
| Orphan Python modules (backup/dead files) | 3 | Low |
| Orphan config entries (dirs not in active_releases) | 7 | Medium |
| Config without runtime consumer | 3 | Medium |
| Missing config artifacts (declared but absent) | 4 | High |
| Unregistered handlers | 1 | Medium |
| Handlers with no config entry | 2 | Medium |
| Orphan React components | 9 | Low |
| Hardcoded hex colors in SPA | 358 | Medium |
| Source files without tests | ~80 | Medium |
| Modules with zero test coverage | 5 | High |
| Cross-cutting contamination terms | 5 areas | Medium |
| Total test functions | 2,570 | -- |

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

**Backup files (likely dead):**
- `app/domain/services/document_builder_backup.py` -- backup copy, not imported anywhere
- `app/domain/services/llm_execution_logger_original.py` -- backup copy, not imported anywhere

#### Orphan Config

- **`primary_implementation_plan_handler.py`** exists on disk but is NOT registered in `registry.py` HANDLERS dict
- **`story_backlog`** handler is registered in `registry.py` but has NO entry in `active_releases.document_types`
- **`project_logbook`** handler is registered in `registry.py` but has NO entry in `active_releases` AND no directory under `combine-config/document_types/`

#### Config Without Runtime Consumer

- **`concierge_intake`** is in `active_releases.document_types` but has no handler in `registry.py` (uses workflow-specific prompting)
- **`epic`** is in `active_releases.document_types` but has no handler (package.yaml declares `creation_mode: constructed`)
- **`feature`** is in `active_releases.document_types` but has no handler

#### Missing Artifacts (Declared But Absent)

- **`backlog_item`** package.yaml declares `prompts/task.prompt.txt` but no `prompts/` directory exists
- **`plan_explanation`** package.yaml declares `prompts/task.prompt.txt` but no `prompts/` directory exists

#### Test Coverage

| Scope | Files | Tested | Coverage |
|-------|-------|--------|----------|
| `app/domain/handlers/` | 15 | 5 | **33%** |
| `app/domain/services/` | ~20 | ~11 | **55%** |

**Untested handlers:** `architecture_spec_handler`, `backlog_item_handler`, `base_handler`, `execution_plan_handler`, `intent_packet_handler`, `pipeline_run_handler`, `plan_explanation_handler`, `primary_implementation_plan_handler`, `project_discovery_handler`, `story_backlog_handler`

**Untested services:** `document_builder`, `llm_response_parser`, `thread_execution_service`, `work_statement_registration`, `work_statement_state`, `work_package_state`, `secret_governance`, `logbook_service`

---

### 2. Workflow Engine

**Files:** `app/domain/workflow/`

#### Dead Code (26 unused imports)

| File | Count | Notable |
|------|-------|---------|
| `workflow_executor.py` | 6 | `Any`, `List`, `Tuple`, `IterationInstance`, `ExecutionResult` |
| `nodes/task.py` | 2 | Unused vars `issue_type`, `qid` (F841) |
| `nodes/mock_executors.py` | 2 | `List`, `Optional` |
| `pg_state_persistence.py` | 2 | `Any`, `Dict` |
| `thread_manager.py` | 2 | `uuid4`, `ThreadExecutionService` |
| `plan_validator.py` | 2 | `Optional`, unused var `end_node_ids` |
| `interrupt_registry.py` | 3 | `field`, `Project`, `WorkflowExecution` |
| Other (7 files) | 7 | Various typing/dataclass imports |

#### Orphan Config

- **3 orphan workflow directories** not in `active_releases.workflows`:
  - `combine-config/workflows/feature_set_generator/`
  - `combine-config/workflows/story_set_generator/`
  - `combine-config/workflows/primary_implementation_plan/`
- **Stale version directories** (superseded by active versions):
  - `concierge_intake/releases/1.3.0/` (active: 1.4.0)
  - `project_discovery/releases/1.8.0/` (active: 2.0.0)
  - `technical_architecture/releases/1.0.0/` (active: 2.0.0)

#### Test Coverage

| Scope | Files | Tested | Coverage |
|-------|-------|--------|----------|
| `app/domain/workflow/` | ~30 | ~20 | **67%** |

Test distribution: 598 test functions across `tests/domain/` + relevant `tests/tier1/workflow/` files.

**Untested:** `thread_manager`, `outcome_recorder`, `pg_state_persistence`, `interrupt_registry`, `scope`, `nodes/task.py`, `nodes/end.py`, `nodes/mock_executors.py`

---

### 3. Intake/Concierge

**Files:** `app/web/routes/public/intake_workflow_routes.py`, `app/domain/workflow/nodes/intake_gate*`, concierge-related config

#### Dead Code

| File | Line | Finding |
|------|------|---------|
| `app/web/routes/public/intake_workflow_routes.py` | 32 | Unused import `Project` |
| `app/domain/workflow/nodes/intake_gate.py` | 12 | Unused import `json` |

#### Config Status

- `concierge_intake` workflow: active at 1.4.0, directory and definition.json present
- `concierge_intake` document type: active at 1.0.0, directory and package.yaml present
- **No handler registered** for `concierge_intake` -- uses workflow-specific prompting (intentional)

#### Test Coverage

- `tests/tier1/workflow/` contains intake-related tests (`test_spawn_child_documents`, `test_project_orchestrator_inputs`)
- `tests/web/test_intake_workflow_bff.py` and `test_intake_workflow_integration.py` cover the BFF layer
- `app/web/routes/public/intake_workflow_routes.py` and `app/web/routes/public/concierge_routes.py` have no dedicated unit tests

---

### 4. SPA Floor

**Files:** `spa/src/`

#### Orphan Components (never imported)

| File | Status |
|------|--------|
| `spa/src/components/FullDocumentViewer.jsx` | VERIFY -- may be entry point |
| `spa/src/components/ProjectInfoPanel.jsx` | ORPHAN |
| `spa/src/components/WorkPackagePanel.jsx` | ORPHAN |
| `spa/src/components/DocumentDetailPanel.jsx` | ORPHAN |
| `spa/src/components/viewers/RawContentViewer.jsx` | VERIFY |
| `spa/src/components/viewers/DocumentTreeViewer.jsx` | VERIFY |
| `spa/src/components/viewers/IntakeTranscriptViewer.jsx` | VERIFY |
| `spa/src/components/viewers/PipelineRunViewer.jsx` | VERIFY |
| `spa/src/components/blocks/StringListBlock.jsx` | VERIFY |

#### Hardcoded Hex Colors

**358 hardcoded hex color values across 58 files.** These should use CSS variables for theme consistency.

Top offenders by file (estimated from prior analysis):
- Component files with inline `style={{ color: '#...' }}` patterns
- `spa/src/components/blocks/IABlockRenderer.jsx` -- partially fixed (TableRenderer) but other renderers may still have hardcoded colors
- `spa/src/styles/themes.css` -- defines CSS variables (these are correct)
- `spa/src/utils/constants.js` -- defines edge/theme constants

#### Unused Utilities

| File | Status |
|------|--------|
| `spa/src/utils/layout.js` | Unused (0 importers) |
| `spa/src/utils/mockData.js` | Unused (test fixture only) |
| `spa/src/utils/factories.js` | Unused (test fixture only) |
| `spa/src/hooks/useFloorSSE.js` | Unused (0 importers) |

#### Build Staleness

SPA source files are newer than build artifacts -- rebuild may be needed (last rebuild was during this session for the IABlockRenderer dark mode fix).

#### Test Coverage

**Zero JavaScript test infrastructure.** No Jest, Vitest, or other JS test runner detected. The SPA is entirely untested.

---

### 5. Config Registry

**Files:** `app/config/`, `combine-config/`

#### Dead Code

No unused imports in `app/config/` (only 2 source files).

#### Orphan Config Directories (Not in active_releases)

| Type | Directory | Status |
|------|-----------|--------|
| Document type | `primary_implementation_plan/` | Deprecated (per package.yaml) |
| Workflow | `feature_set_generator/` | Orphan |
| Workflow | `story_set_generator/` | Orphan |
| Workflow | `primary_implementation_plan/` | Orphan |
| Task prompt | `feature_set_generator/` | Orphan |
| Task prompt | `story_set_generator/` | Orphan |
| Task prompt | `primary_implementation_plan/` | Orphan |
| PGC | `primary_implementation_plan.v1/` | Orphan |
| Schema | `primary_implementation_plan/` | Orphan |

#### Missing Config (In active_releases But No Directory)

| Section | Key | Expected Path | Status |
|---------|-----|---------------|--------|
| tasks | `work_package` | `combine-config/prompts/tasks/work_package/` | **MISSING** |
| tasks | `work_statement` | `combine-config/prompts/tasks/work_statement/` | **MISSING** |
| schemas | `work_package` | `combine-config/schemas/work_package/` | **MISSING** |
| schemas | `work_statement` | `combine-config/schemas/work_statement/` | **MISSING** |

Note: Both `work_package` and `work_statement` have embedded schemas at their `document_types` paths, but no global schema or task prompt directories.

#### Test Coverage

| File | Tested |
|------|--------|
| `app/config/package_loader.py` | YES (`tests/unit/config/test_package_loader.py`) |
| `app/config/package_model.py` | No dedicated test |

---

### 6. API Layer

**Files:** `app/api/`, `app/api/v1/`

#### Dead Code (119 unused imports -- largest subsystem)

**Top clusters:**

| Area | Count | Notable |
|------|-------|---------|
| `app/api/services/admin_workbench_service.py` | 6 | `Path`, `VersionNotFoundError`, `DocumentTypePackage`, `RolePrompt`, `Template`, `ActiveReleases` + unused var `active_version` |
| `app/api/v1/routers/production.py` | 5 | `ProductionState`, `Station`, `STATE_DISPLAY_TEXT`, `map_node_outcome_to_state`, `map_station_from_node` |
| `app/api/v1/routers/websocket.py` | 5 | `json`, `Optional`, `Depends`, `EventBroadcaster`, `ExecutionService` |
| `app/api/v1/routers/telemetry.py` | 5 | `datetime`, `Decimal`, `Any`, `Dict`, `Field` |
| `app/api/services/workspace_service.py` | 5 | `Path`, `Any`, `GitConflictError`, `ValidationReport/Result/Severity` |
| `app/api/services/__init__.py` | 6 | Re-exports of unused service classes |
| `app/api/v1/routers/admin_releases.py` | 5 | `ReleaseInfo`, `ReleaseState`, `ReleaseHistoryEntry`, `RollbackResult`, `ImmutabilityViolationError` |
| `app/api/routers/composer.py` | 3 | `AssembledPrompt`, `RenderModel`, `RenderBlock` |
| `app/api/v1/services/llm_execution_service.py` | 3 | `uuid4`, `StoredDocument`, `StoredExecutionState` |
| Other (60+ files) | 76 | Various typing, sqlalchemy, pydantic imports |

**Vulture findings (100% confidence):**
- `app/api/services/role_prompt_service.py:89` -- unused variable `pipeline_id`
- `app/api/services/mech_handlers/executor.py:139` -- unused variable `op_type`
- `app/api/services/release_service.py:146` -- unused variable `package`

#### Mech Handlers: Entirely Untested

`app/api/services/mech_handlers/` has 11 source files and zero test files:
- `base.py`, `entry.py`, `exclusion_filter.py`, `executor.py`, `extractor.py`, `invariant_pinner.py`, `merger.py`, `registry.py`, `router.py`, `spawner.py`, `validator.py`

#### Middleware: Entirely Untested

`app/api/middleware/` has 4 files, none tested:
- `body_size.py`, `error_handling.py`, `logging.py`, `request_id.py`, `secret_ingress.py`

#### Test Coverage

| Scope | Files | Tested | Coverage |
|-------|-------|--------|----------|
| `app/api/` (all) | ~110 | ~47 | **43%** |
| `app/api/services/` | ~25 | ~6 | **24%** |
| `app/api/services/mech_handlers/` | 11 | 0 | **0%** |
| `app/api/middleware/` | 4 | 0 | **0%** |
| `app/api/models/` | ~12 | ~2 indirect | **17%** |
| `app/api/v1/routers/` | ~15 | ~8 | **53%** |

---

### 7. Auth

**Files:** `app/auth/`

#### Dead Code (17 unused imports)

| File | Count | Notable |
|------|-------|---------|
| `app/auth/service.py` | 4 | `hashlib`, `datetime`, `update`, `insert`, `IntegrityError` |
| `app/auth/db_models.py` | 4 | `datetime`, `UUID`, `DateTime`, `Integer` |
| `app/auth/middleware.py` | 4 | `User`, `PersonalAccessToken`, `hash_token`, `hash_pat` |
| `app/auth/dependencies.py` | 1 | `RedirectResponse` |
| `app/auth/oidc_config.py` | 1 | `Optional` |
| `app/auth/providers/base.py` | 1 | `Optional` |
| `app/auth/routes.py` | 1 | `Optional` |

#### Test Coverage

| Scope | Files | Tested | Coverage |
|-------|-------|--------|----------|
| `app/auth/` | 14 | 7 | **50%** |

**Untested:** `utils.py`, `rate_limits.py`, `dependencies.py`, `oidc_config.py`, `service.py`, `providers/base.py`, `providers/google.py`

---

### Cross-Cutting: Web/BFF Layer

**Files:** `app/web/`

Not a requested subsystem, but notable:

- 9 unused imports across `app/web/`
- 11 of 15 route files have no tests (**27% coverage**)
- `app/web/routes/public/workflow_build_routes.py:267` -- unused variable `document_id`
- Jinja2 template routes are largely superseded by the SPA

---

### Cross-Cutting: Persistence Layer

**Files:** `app/domain/repositories/`, `app/persistence/`, `app/infrastructure/`

- 4 unused imports in `app/domain/repositories/`
- 10 unused imports in `app/persistence/`
- 6 of 7 `app/domain/repositories/` files untested (**14% coverage**)
- `app/middleware/` (2 files) entirely untested

---

## Cross-Cutting Reference Audit

### Term: `primary_implementation_plan`

| Area | Status |
|------|--------|
| `combine-config/document_types/primary_implementation_plan/` | Orphan dir (not in active_releases), package.yaml marked deprecated |
| `combine-config/workflows/primary_implementation_plan/` | Orphan dir |
| `combine-config/prompts/tasks/primary_implementation_plan/` | Orphan dir |
| `combine-config/prompts/pgc/primary_implementation_plan.v1/` | Orphan dir |
| `combine-config/schemas/primary_implementation_plan/` | Orphan dir |
| `app/domain/handlers/primary_implementation_plan_handler.py` | File on disk, NOT registered in HANDLERS dict |
| `app/api/v1/routers/projects.py` | References in docdef normalization block (ArchitecturalSummaryView fallback dict) |

**Verdict:** Full orphan chain. Safe to move to `recycle/` once confirmed no DB records reference this type.

### Term: `ArchitecturalSummaryView`

| Area | File | Status |
|------|------|--------|
| combine-config | `technical_architecture/package.yaml` | `view_docdef: null` (cleared this session) |
| app | `app/api/v1/routers/projects.py` | Referenced in hardcoded fallback dict (~line 904) |
| app | `app/web/routes/public/view_routes.py` | Referenced in Jinja2 route fallback |
| app | `app/web/routes/admin/composer_routes.py` | Referenced in admin composer |

**Verdict:** Still referenced in 3 app files despite `view_docdef: null` in config. Harmless (fallback only) but should be cleaned up.

### Term: `story_backlog`

| Area | Status |
|------|--------|
| `app/domain/handlers/story_backlog_handler.py` | Registered in `registry.py` as `story_backlog` |
| `app/domain/services/story_backlog_service.py` | Active service |
| `combine-config/_active/active_releases.json` | **NOT PRESENT** in `document_types` |
| `combine-config/document_types/` | **NO directory** for `story_backlog` |

**Verdict:** Lives entirely in code, not governed config. Handler is registered but has no config backing.

### Term: `view_docdef` Authority Sources

Three authority sources exist:
1. **combine-config package.yaml** (now authoritative per code change this session)
2. **Database `document_types` table** (legacy fallback)
3. **Hardcoded dicts in `projects.py` and Jinja2 routes** (bypasses both)

**Verdict:** Authority was consolidated this session, but hardcoded dicts remain as dead fallback paths.

### Terms: `epic`, `feature`

| Area | Status |
|------|--------|
| `combine-config/document_types/epic/` | Active in active_releases, no handler (creation_mode: constructed) |
| `combine-config/document_types/feature/` | Active in active_releases, no handler |
| Tests | `test_epic_feature_cleanup.py`, `test_epic_feature_removal.py` validate cleanup |

**Verdict:** Intentionally handler-less document types. Config is clean.

---

## Critical (Act Now)

1. **Missing task prompt directories:** `work_package` and `work_statement` are in `active_releases.tasks` but have NO directory at `combine-config/prompts/tasks/`. If any code path tries to load these task prompts, it will fail at runtime.

2. **Missing global schema directories:** `work_package` and `work_statement` are in `active_releases.schemas` but have NO directory at `combine-config/schemas/`. They do have embedded schemas in their document_type packages.

3. **Missing packaged task prompts:** `backlog_item` and `plan_explanation` package.yaml files declare `prompts/task.prompt.txt` but no `prompts/` directory exists under their release.

## High (Act Soon)

4. **API layer: 119 unused imports** -- largest dead code concentration. The `app/api/services/admin_workbench_service.py` alone has 6 unused imports plus an unused variable.

5. **Mech handlers entirely untested** -- 11 files in `app/api/services/mech_handlers/` with zero test coverage. These are mechanical operation handlers that modify production data.

6. **SPA: 358 hardcoded hex colors** -- theme breakage risk. Only `IABlockRenderer.TableRenderer` was fixed this session; other components still have hardcoded values.

7. **Orphan `primary_implementation_plan` chain** -- full config tree (document_type, workflow, task, PGC, schema, handler file) exists but is disconnected from active_releases and registry.

8. **`story_backlog` not in governed config** -- handler registered, service exists, but no `active_releases` entry or `combine-config/document_types/` directory.

## Medium (Track as Debt)

9. **Handler test coverage at 33%** -- 10 of 15 handlers untested. These are critical document generation paths.

10. **Tier 2 nearly empty** -- only 2 files and 13 test functions. Wiring/contract tests are thin.

11. **SPA has zero JS test infrastructure** -- no Jest, Vitest, or any JavaScript testing framework.

12. **3 orphan workflow directories** (`feature_set_generator`, `story_set_generator`, `primary_implementation_plan`) -- can be moved to `recycle/`.

13. **Backup files on disk** -- `document_builder_backup.py`, `llm_execution_logger_original.py` are dead code.

14. **Auth provider coverage at 50%** -- Google OIDC provider and base provider untested.

15. **Web/BFF routes 73% untested** -- mostly superseded by SPA but still deployed.

## Low (Informational)

16. **Stale workflow version directories** -- old versions of `concierge_intake` (1.3.0), `project_discovery` (1.8.0), `technical_architecture` (1.0.0) on disk.

17. **SPA orphan components** -- 9 components potentially unused (some may be dynamically loaded).

18. **Unused SPA utilities** -- `layout.js`, `mockData.js`, `factories.js`, `useFloorSSE.js`.

19. **211 total unused imports** across the Python codebase (ruff F401).

---

## Test Distribution Summary

| Tier | Files | Test Functions | % of Total |
|------|-------|----------------|------------|
| Tier 1 | 47 | 848 | 33% |
| Domain | 39 | 598 | 23% |
| Unit | 19 | 234 | 9% |
| API | 20 | 195 | 8% |
| Infrastructure | 7 | 85 | 3% |
| LLM | 5 | 83 | 3% |
| Auth | 7 | 82 | 3% |
| Core | 4 | 58 | 2% |
| Web | 3 | 56 | 2% |
| Observability | 3 | 40 | 2% |
| Operational | 4 | 37 | 1% |
| Execution | 3 | 32 | 1% |
| Persistence | 2 | 27 | 1% |
| Integration | 3 | 26 | 1% |
| E2E | 2 | 25 | 1% |
| UI | 2 | 22 | 1% |
| Smoke | 1 | 14 | 1% |
| Tier 2 | 2 | 13 | 1% |
| Root-level | 5 | 95 | 4% |
| **TOTAL** | **177** | **2,570** | **100%** |

---

## Recommended Work Statements

Based on findings, the following WSs are recommended:

1. **WS-CLEANUP-ORPHAN-CONFIG**: Remove orphan `primary_implementation_plan` chain (document_type, workflow, task, PGC, schema dirs) and unregistered handler file. Move to `recycle/`. Clean up `active_releases.json` entries for missing `work_package`/`work_statement` task and schema dirs.

2. **WS-CLEANUP-DEAD-IMPORTS**: Run `ruff check app/ --select F401,F841 --fix` to auto-remove 211+ unused imports and 6 unused variables across all subsystems.

3. **WS-SPA-THEME-COMPLIANCE**: Replace 358 hardcoded hex colors in SPA components with CSS variable references. Establish lint rule to prevent regression.

4. **WS-TEST-MECH-HANDLERS**: Write Tier 1 tests for `app/api/services/mech_handlers/` (11 files, 0% coverage). These are mechanical operation handlers that modify production state.

5. **WS-CLEANUP-BACKUP-FILES**: Remove `document_builder_backup.py` and `llm_execution_logger_original.py` (dead backup copies).

6. **WS-CONFIG-STORY-BACKLOG**: Either add `story_backlog` to governed config (`active_releases.json` + `combine-config/document_types/`) or remove the handler and service if the document type is being retired.

---

_Audit generated by codebase-auditor skill. All findings are read-only observations -- no code was modified._

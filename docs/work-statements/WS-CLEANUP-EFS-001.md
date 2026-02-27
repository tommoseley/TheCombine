# WS-CLEANUP-EFS-001: Remove Epic, Feature, and Story Artifacts

## Status: Superseded by WS-PIPELINE-003

> **Note:** This WS was drafted before WP-PIPELINE-001 consolidated all legacy cleanup
> under WS-PIPELINE-003. This document is retained as historical reference for its
> detailed file-by-file inventory. WS-PIPELINE-003 is the authoritative WS for execution.

## Parent Work Package

- WP-PIPELINE-001

## Dependencies

- **WS-PIPELINE-001** must be complete before execution (POW is rewritten before old types are removed)

## Governing References

- ADR-051 -- Work Package as Runtime Primitive ("Epics, Features, and Stories are eliminated")
- ADR-052 -- Document Pipeline WP/WS Integration
- POL-WS-001 -- Work Statement Standard

## Verification Mode: A

## Scope Declaration: Multi-commit

This WS covers removal across app code, configuration, templates, tests, and migrations.
If scope expands beyond what is listed here, STOP and draft an Implementation Plan.

---

## Objective

Remove all Epic, Feature, and Story artifacts from the codebase. Per ADR-051 §9:
"Epics, Features, and Stories are eliminated — replaced by a cleaner, execution-aligned hierarchy."
The WP/WS model is now the normative hierarchy. Legacy E/F/S code is dead weight.

---

## Inventory

### A. Code — Services & Handlers (app/)

| # | File | What | Action |
|---|------|------|--------|
| A1 | `app/domain/services/fanout_service.py` | `EpicFeatureFanoutService`, `FeatureStoryFanoutService` | DELETE file |
| A2 | `app/domain/services/story_backlog_service.py` | `StoryBacklogService`, `GenerateEpicResult` | DELETE file |
| A3 | `app/domain/services/backlog_pipeline.py` | BCP orchestration (epic/feature/story hierarchy) | DELETE file |
| A4 | `app/domain/services/graph_validator.py` | EPIC/FEATURE/STORY level validation | DELETE file |
| A5 | `app/domain/services/backlog_ordering.py` | Backlog ordering (EPIC/FEATURE/STORY levels) | DELETE file |
| A6 | `app/domain/handlers/story_backlog_handler.py` | `StoryBacklogHandler` | DELETE file |
| A7 | `app/domain/handlers/backlog_item_handler.py` | `BacklogItemHandler` (EPIC/FEATURE/STORY discriminator) | DELETE file |
| A8 | `app/domain/handlers/registry.py` | `story_backlog` and `backlog_item` registrations + imports | EDIT: remove lines |

### B. Code — API Routes & Models (app/)

| # | File | What | Action |
|---|------|------|--------|
| B1 | `app/api/routers/commands.py` | StoryBacklogInitRequest, GenerateEpicRequest/Response, all `/story-backlog/*` routes | DELETE file or gut E/F/S routes |
| B2 | `app/core/middleware/deprecation.py` | `/view/EpicBacklogView` and `/view/StoryBacklogView` redirects | EDIT: remove entries |
| B3 | `app/api/schemas/requests.py` | Any E/F/S request schemas | AUDIT — remove if present |
| B4 | `app/api/schemas/responses.py` | Any E/F/S response schemas | AUDIT — remove if present |

### C. Code — Other References (app/) — Audit Required

These files contain references that may be incidental (string in a list, comment, etc.) or structural.
Each must be audited and cleaned:

| # | File | Likely Reference |
|---|------|------------------|
| C1 | `app/api/v1/routers/projects.py` | May reference epic doc types |
| C2 | `app/api/services/production_service.py` | Epic/story in production logic |
| C3 | `app/api/services/project_service.py` | Epic/story in project queries |
| C4 | `app/domain/services/set_reconciler.py` | Reconciliation for epics |
| C5 | `app/domain/workflow/plan_executor.py` | Epic/story references in executor |
| C6 | `app/domain/workflow/input_resolver.py` | Input resolution for epic types |
| C7 | `app/domain/workflow/iteration.py` | Iteration logic referencing epics |
| C8 | `app/domain/workflow/scope.py` | Scope definitions for epic/story |
| C9 | `app/domain/services/staleness_service.py` | Staleness checks for epic docs |
| C10 | `app/domain/services/llm_response_parser.py` | Parser referencing epic/story |
| C11 | `app/domain/services/render_model_builder.py` | Render model for epic views |
| C12 | `app/api/services/search_service.py` | Search indexing epic/story docs |
| C13 | `app/api/services/document_definition_service.py` | DocDef for epic types |
| C14 | `app/api/utils/id_generators.py` | Epic/feature ID patterns |
| C15 | `app/domain/models/llm_logging.py` | LLM log references |
| C16 | `app/api/models/document_type.py` | Document type model |
| C17 | `app/api/models/document.py` | Document model |
| C18 | `app/domain/handlers/work_package_handler.py` | May reference epic for migration context |
| C19 | `app/domain/registry/loader.py` | Registry loader for epic types |
| C20 | `app/web/routes/public/document_routes.py` | Epic document routes |
| C21 | `app/web/routes/public/view_routes.py` | Epic view routes |
| C22 | `app/web/routes/admin/composer_routes.py` | Composer routes for epic |
| C23 | `app/web/routes/public/debug_routes.py` | Debug routes referencing epics |
| C24 | `app/web/routes/public/search_routes.py` | Search routes for epic docs |
| C25 | `app/persistence/models.py` | Persistence model comments |
| C26 | `app/core/config.py` | Config references |
| C27 | `app/api/models/role_task.py` | Role/task model |
| C28 | `app/api/models/llm_thread.py` | Thread model |
| C29 | `app/api/models/document_definition.py` | DocDef model |
| C30 | `app/api/services/workspace_service.py` | Workspace service |
| C31 | `app/api/services/role_prompt_service.py` | Role prompt service |
| C32 | `app/domain/services/document_builder.py` | Document builder |
| C33 | `app/domain/handlers/base_handler.py` | Base handler |
| C34 | `app/domain/schemas/metrics.py` | Metrics schema |
| C35 | `app/api/v1/schemas/workflow.py` | Workflow API schema |

### D. Jinja2 Templates

| # | File | Action |
|---|------|--------|
| D1 | `app/web/templates/public/pages/partials/_story_backlog_content.html` | DELETE file |
| D2 | `app/web/templates/public/pages/home.html` | EDIT: remove E/F/S nav links |
| D3 | `app/web/templates/public/partials/_document_viewer_content.html` | EDIT: remove E/F/S viewer logic |
| D4 | `app/web/templates/public/partials/_document_viewer.html` | EDIT: remove E/F/S viewer logic |
| D5 | `app/web/templates/public/components/search_results.html` | EDIT: remove E/F/S result types |
| D6 | `app/web/templates/production/line_react.html` | AUDIT: check for E/F/S references |

### E. SPA — Static Assets

| # | File | Action |
|---|------|--------|
| E1 | `app/web/static/spa/assets/index-vhICrant.js` | Stale SPA build artifact — will be replaced by rebuild |
| E2 | `app/web/static/spa/assets/index-vhICrant.js.map` | Same |
| E3 | `app/web/static/spa/assets/index-ClYuWLLi.css` | Same |
| E4 | `app/web/static/public/js/thread_monitor.js` | AUDIT: check for E/F/S references |

### F. Configuration (combine-config/)

| # | Path | Action |
|---|------|--------|
| F1 | `combine-config/document_types/epic/` | DELETE directory |
| F2 | `combine-config/document_types/feature/` | DELETE directory |
| F3 | `combine-config/document_types/backlog_item/` | DELETE directory |
| F4 | `combine-config/schemas/epic/` | DELETE directory |
| F5 | `combine-config/schemas/feature/` | DELETE directory |
| F6 | `combine-config/schemas/backlog_item/` | DELETE directory |
| F7 | `combine-config/workflows/backlog_generator/` | DELETE directory |
| F8 | `combine-config/workflows/feature_set_generator/` | DELETE directory |
| F9 | `combine-config/workflows/story_set_generator/` | DELETE directory |
| F10 | `combine-config/prompts/tasks/epic_backlog/` | DELETE directory |
| F11 | `combine-config/prompts/tasks/epic_architecture/` | DELETE directory |
| F12 | `combine-config/prompts/tasks/story_backlog/` | DELETE directory |
| F13 | `combine-config/prompts/tasks/story_implementation/` | DELETE directory |
| F14 | `combine-config/prompts/tasks/feature_set_generator/` | DELETE directory |
| F15 | `combine-config/prompts/tasks/story_set_generator/` | DELETE directory |
| F16 | `combine-config/prompts/tasks/backlog_generator/` | DELETE directory |
| F17 | `combine-config/_active/active_releases.json` | EDIT: remove 12 E/F/S entries (epic, feature, backlog_item in document_types + schemas; backlog_generator, story_implementation, epic_backlog, story_backlog, epic_architecture in tasks; backlog_generator, feature_set_generator, story_set_generator in workflows) |

### G. Tests

| # | File | Action |
|---|------|--------|
| G1 | `tests/tier1/services/test_fanout_service.py` | DELETE — tests deleted service |
| G2 | `tests/tier1/services/test_backlog_pipeline.py` | DELETE — tests deleted service |
| G3 | `tests/tier1/services/test_graph_validator.py` | DELETE — tests deleted service |
| G4 | `tests/tier1/services/test_backlog_ordering.py` | DELETE — tests deleted service |
| G5 | `tests/tier1/handlers/test_epic_feature_removal.py` | KEEP and UPDATE — these verify removal; strengthen assertions |
| G6 | `tests/tier1/handlers/test_epic_feature_cleanup.py` | KEEP and UPDATE — same |
| G7 | `tests/api/routers/test_command_routes.py` | DELETE or gut E/F/S route tests |
| G8 | `tests/core/middleware/test_deprecation.py` | EDIT: remove E/F/S redirect tests |
| G9 | `tests/integration/test_adr034_proof.py` | AUDIT — may reference epic views |
| G10 | `tests/integration/test_docdef_golden_traces.py` | AUDIT — may reference epic docdefs |

Additional test files to audit (references may be incidental):

| # | File |
|---|------|
| G11 | `tests/tier1/handlers/test_ipp_wp_candidates.py` |
| G12 | `tests/tier1/handlers/test_ipf_wp_reconciliation.py` |
| G13 | `tests/tier1/handlers/test_pow_rewrite.py` |
| G14 | `tests/tier1/handlers/test_production_floor_wp_ws.py` |
| G15 | `tests/tier1/services/test_production_child_tracks.py` |
| G16 | `tests/tier1/workflow/test_spawn_child_documents.py` |
| G17 | `tests/unit/test_document_ownership.py` |
| G18 | `tests/domain/workflow/test_context.py` |
| G19 | `tests/domain/workflow/test_iteration.py` |
| G20 | `tests/domain/workflow/test_workflow_executor.py` |
| G21 | `tests/domain/workflow/test_workflow_state.py` |
| G22 | `tests/domain/workflow/test_validator.py` |
| G23 | `tests/domain/workflow/test_loader.py` |
| G24 | `tests/domain/workflow/test_input_resolver.py` |
| G25 | `tests/domain/workflow/test_models.py` |
| G26 | `tests/domain/test_render_model_builder.py` |
| G27 | `tests/domain/registry/test_document_registry.py` |
| G28 | `tests/domain/registry/test_view_docdef_resolution.py` |
| G29 | `tests/domain/services/test_staleness_service.py` |
| G30 | `tests/domain/services/test_ux_config_service.py` |
| G31 | `tests/api/v1/conftest.py` |
| G32 | `tests/api/v1/test_workflows.py` |
| G33 | `tests/api/test_document_definition_service.py` |
| G34 | `tests/test_document_status_service.py` |

### H. Migrations (DO NOT DELETE — append only)

| # | File | Action |
|---|------|--------|
| H1 | `alembic/versions/20260216_002_add_instance_id.py` | No change (historical) |
| H2 | `alembic/versions/20260216_003_add_bcp_document_types.py` | No change (historical) |
| H3 | NEW migration required | Add migration to soft-delete or archive `epic`, `feature`, `backlog_item` from `document_types` table |

### I. Documentation (DO NOT DELETE — historical record)

| # | File | Action |
|---|------|--------|
| I1 | `docs/work-statements/WS-001-Epic-Backlog-BFF-Refactor.md` | No change (historical) |
| I2 | `docs/work-statements/WS-EPIC-SPAWN-001.md` | No change (historical) |
| I3 | `docs/work-statements/WS-STORY-BACKLOG-VIEW.md` | No change (historical) |
| I4 | `docs/work-statements/WS-STORY-BACKLOG-COMMANDS-SLICE-1.md` | No change (historical) |
| I5 | `docs/work-statements/WS-STORY-BACKLOG-COMMANDS-SLICE-2.md` | No change (historical) |
| I6 | ADRs referencing epics (ADR-034, ADR-027, etc.) | No change (append-only) |
| I7 | `docs/PROJECT_STATE.md` | UPDATE: remove BCP known-issue entry, note E/F/S removal |

---

## Summary Counts

| Category | DELETE file | DELETE dir | EDIT | AUDIT | KEEP |
|----------|-----------|-----------|------|-------|------|
| A. Handlers/Services | 7 | — | 1 | — | — |
| B. API Routes/Models | 1 | — | 1 | 2 | — |
| C. Other app/ refs | — | — | — | 35 | — |
| D. Templates | 1 | — | 4 | 1 | — |
| E. SPA static | — | — | — | 1 | 3 (rebuild) |
| F. Config dirs + releases | — | 16 | 1 | — | — |
| G. Tests | 4 | — | 1 | 24 | 2 (strengthen) |
| H. Migrations | — | — | — | — | 2 (no touch) + 1 new |
| I. Docs | — | — | 1 | — | 6 (historical) |
| **TOTAL** | **13** | **16** | **9** | **63** | **14** |

---

## Prohibited Actions

- DO NOT delete or modify Alembic migration files (H1, H2)
- DO NOT delete or modify ADRs or historical Work Statements (I1–I6)
- DO NOT delete database rows — use a migration to mark types as deprecated/archived
- DO NOT remove WP/WS code that replaced E/F/S — only remove E/F/S-specific artifacts
- DO NOT remove `combine-config/prompts/pgc/` PGC prompts (they reference E/F/S only incidentally)

## Execution Order (Recommended)

1. **Phase 1 — Config cleanup** (F1–F17): Delete dead config directories + purge active_releases.json entries
2. **Phase 2 — Dead code deletion** (A1–A7, B1, D1): Delete files with no remaining consumers
3. **Phase 3 — Registry & wiring cleanup** (A8, B2): Remove imports and registrations
4. **Phase 4 — Audit pass** (C1–C35, G11–G34): Read each file, remove or update E/F/S references
5. **Phase 5 — Test cleanup** (G1–G4, G7, G8): Delete/update tests for deleted code
6. **Phase 6 — Strengthen verification tests** (G5, G6): Update removal assertions
7. **Phase 7 — Migration** (H3): New Alembic migration to archive doc types in DB
8. **Phase 8 — SPA rebuild + PROJECT_STATE update** (E1–E3, I7)
9. **Phase 9 — Tier 0 verification**: Full test suite must pass

---

## Definition of Done

- [ ] No file in `app/` imports or references Epic, Feature, Story, or Backlog Item as a doc type
- [ ] No config directory exists for `epic`, `feature`, or `backlog_item` in `combine-config/`
- [ ] No workflow, prompt, or schema exists for E/F/S fanout or generation
- [ ] Handler registry contains zero E/F/S handlers
- [ ] Existing epic_feature_removal and epic_feature_cleanup tests pass (strengthened)
- [ ] New migration archives E/F/S doc types in database
- [ ] Tier 0 passes (`ops/scripts/tier0.sh`)
- [ ] `docs/PROJECT_STATE.md` updated to reflect removal
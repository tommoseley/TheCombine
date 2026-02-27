# WS-PIPELINE-003 Change Audit

## Status: Complete
## Date: 2026-02-26
## Scope: Legacy Ontology Cleanup (Epic/Feature/Backlog Removal)

---

## Phase 1: Archive Config Directories

### Created (new directories + files)

`combine-config/_archive/` -- Archive root for deprecated config, with subdirectories:
- `document_types/` -- epic, feature, backlog_item, plan_explanation (4 dirs moved here)
- `workflows/` -- backlog_generator, story_set_generator, feature_set_generator, plan_explanation (4 dirs)
- `schemas/` -- epic, feature, backlog_item, plan_explanation (4 dirs)
- `prompts/tasks/` -- epic_backlog, epic_architecture, story_set_generator, feature_set_generator, story_implementation, backlog_generator, plan_explanation, strategy_architecture_v1, strategy_discovery_v1, strategy_requirements_v1, strategy_review_v1 (11 dirs)
- `prompts/pgc/` -- primary_implementation_plan.v1 (1 dir)
- Also archived: document_types/primary_implementation_plan, schemas/primary_implementation_plan, workflows/primary_implementation_plan, prompts/tasks/primary_implementation_plan (4 dirs, orphaned IPP artifacts)

**Why:** WS prohibited deletion; archive preserves history while removing from active paths.

### Edited

**`combine-config/_active/active_releases.json`** -- Complete rewrite. Removed 19 entries across document_types (4), schemas (4), tasks (9), workflows (2). Result: 81 -> 62 assets.

**Why:** Archived types must not appear in active registry.

---

## Phase 2: Clean Config Schemas

### Edited

**`combine-config/schemas/clarification_question_set/releases/1.0.0/schema.json`**
- `question_set_kind` enum: removed `"epic_backlog"`, `"story_backlog"`
- `artifact_scope` enum: `["project", "epic", "story", "document", "unknown"]` -> `["project", "work_package", "document", "unknown"]`
- Description example: `EPIC_SCOPE` -> `WP_SCOPE`

**Why:** These enums referenced deprecated ontology terms.

**Judgment call:** Removed `"story_backlog"` from `question_set_kind` even though story_backlog is deferred to WS-REGISTRY-002. Rationale: story_backlog questions would use `"scope_clarification"` or `"other"`, not a dedicated kind. This could be revisited in WS-REGISTRY-002.

**`combine-config/schemas/workflow_plan/releases/1.0.0/schema.json`**
- `scope_type` enum: `["document", "project", "epic"]` -> `["document", "project", "work_package"]`

**`combine-config/schemas/registry/package.schema.json`**
- `scope` enum: `["project", "epic", "feature"]` -> `["project", "work_package", "work_statement"]`

---

## Phase 3: Remove App Code

### Deleted (8 files)

| File | Why |
|------|-----|
| `app/domain/handlers/backlog_item_handler.py` | BCP handler, no active doc type |
| `app/domain/handlers/plan_explanation_handler.py` | BCP handler, purely epic-chain (Phase 0 audit confirmed) |
| `app/domain/services/fanout_service.py` | BCP fanout orchestration |
| `app/domain/services/backlog_pipeline.py` | BCP pipeline service |
| `app/domain/services/graph_validator.py` | BCP dependency graph validator |
| `app/domain/services/backlog_ordering.py` | BCP ordering service |
| `app/domain/services/set_reconciler.py` | BCP set reconciliation |
| `app/web/templates/public/pages/partials/_story_backlog_content.html` | Jinja2 partial for story_backlog rendering (SPA supersedes) |

### Edited

**`app/domain/handlers/registry.py`**
- Removed imports: `BacklogItemHandler`, `PlanExplanationHandler`
- Removed registrations: `"backlog_item"`, `"plan_explanation"`
- Kept: `StoryBacklogHandler` (deferred to WS-REGISTRY-002)

---

## Phase 4: Clean App References (parallel agents)

### Deleted (4 more files)

| File | Why |
|------|-----|
| `app/api/v1/routers/backlog_pipeline.py` | BCP-specific API router |
| `app/api/schemas/requests.py` | `PipelineStartRequest` with `epic_id` field |
| `app/api/schemas/responses.py` | `PipelineCreatedResponse` with `epic_id` field |
| `app/api/utils/id_generators.py` | `generate_epic_id`, `generate_story_id` |

### Edited (~28 files)

**Structural changes (functional code):**

| File | Change | Why |
|------|--------|-----|
| `app/api/v1/__init__.py` | Removed `backlog_pipeline_router` import + registration | Router deleted |
| `app/api/utils/__init__.py` | Removed `id_generators` import | Module deleted |
| `app/api/services/project_service.py` | `epic_count` -> `work_package_count`, `get_project_with_epics` -> `get_project_with_work_packages` | Ontology rename |
| `app/api/services/search_service.py` | Removed `epics`/`stories` fields from `SearchResults`, removed epic-specific search methods | Epic search removed |
| `app/domain/registry/loader.py` | Removed `epic_backlog` seed entry from hardcoded fallback | No longer active |
| `app/domain/services/staleness_service.py` | Removed `epic_backlog` from dependency graph | No longer active |
| `app/domain/services/render_model_builder.py` | `EpicDetailView` -> `DocumentDetailView` in fallback logic | Ontology rename |
| `app/domain/schemas/metrics.py` | `epic_description` -> `description` | Ontology rename |
| `app/core/config.py` | Removed `EPIC_DIR`, `EPICS_ROOT`, `epic_dir()` | No epic directory structure |
| `app/core/middleware/deprecation.py` | Removed `EpicBacklogView` redirect | Deprecated view removed |
| `app/domain/workflow/plan_executor.py` | `"FEATURE"` -> `"CAPABILITY"`, `epic` -> `work_package` in docstrings | Ontology rename |

**Docstring/comment-only changes:**

| File | Change |
|------|--------|
| `app/domain/workflow/iteration.py` | Example updates in docstrings |
| `app/domain/workflow/scope.py` | Example updates in docstrings |
| `app/domain/workflow/input_resolver.py` | Example updates in docstrings |
| `app/domain/handlers/base_handler.py` | `epic_id` -> generic example |
| `app/web/routes/public/search_routes.py` | Template context updates |
| `app/web/routes/public/debug_routes.py` | Comment updates |
| Various web templates (6 files) | Epic references in HTML comments/labels |

**Phase 6 docstring edits:**

| File | Change |
|------|--------|
| `app/web/routes/admin/composer_routes.py` | `docdef:EpicBacklog:1.0.0` -> `docdef:ImplementationPlan:1.0.0` (2 locations) |
| `app/api/services/document_definition_service.py` | Same pattern (3 locations) |
| `app/api/models/document_type.py` | `EpicBacklogView` -> `ImplementationPlanView`, `epic_id` -> `work_package_id`, `epic_generation` -> `implementation_plan`, scope comment, doc_type_id example (5 locations) |
| `app/api/models/document_definition.py` | `docdef:EpicBacklog:1.0.0` -> `docdef:ImplementationPlan:1.0.0` (1 location) |

---

## Phase 5: Clean Tests

### Deleted (7 files)

| File | Why |
|------|-----|
| `tests/tier1/services/test_fanout_service.py` | Tests for deleted service |
| `tests/tier1/services/test_backlog_pipeline.py` | Tests for deleted service |
| `tests/tier1/services/test_graph_validator.py` | Tests for deleted service |
| `tests/tier1/services/test_backlog_ordering.py` | Tests for deleted service |
| `tests/tier1/services/test_set_reconciler.py` | Tests for deleted service |
| `tests/tier1/handlers/test_ipp_wp_candidates.py` | Tests for IPP->WP candidate flow (deprecated) |
| `tests/tier1/services/test_production_child_tracks.py` | Tests for deprecated child tracking |

### Edited (10 test files)

| File | Change |
|------|--------|
| `tests/infrastructure/test_configuration.py` | Removed epic config references |
| `tests/api/routers/test_command_routes.py` | Epic docstring examples |
| `tests/domain/workflow/test_workflow_state.py` | Epic scope examples |
| `tests/domain/registry/test_view_docdef_resolution.py` | Epic view references |
| `tests/domain/registry/test_document_registry.py` | Epic type references |
| `tests/domain/services/test_ux_config_service.py` | Epic config references |
| `tests/test_document_status_service.py` | Epic status references |
| `tests/core/middleware/test_deprecation.py` | Epic redirect tests |
| `tests/api/test_document_definition_service.py` | Epic docdef examples |
| `tests/tier1/workflow/test_spawn_child_documents.py` | `"epic"` -> `"work_package"` throughout (FakeDocument, _make_child_specs, assertions, raw envelope test) |

---

## Judgment Calls and Ambiguities

1. **story_backlog question_set_kind removal** -- Removed `"story_backlog"` from clarification question schema enum even though story_backlog handler is deferred. Could be debatable; WS-REGISTRY-002 can re-add if needed.

2. **`"FEATURE"` -> `"CAPABILITY"` in plan_executor.py** -- The string `"FEATURE"` appeared in a docstring describing workflow concepts. Chose `"CAPABILITY"` as the generic replacement rather than `"WORK_PACKAGE"` because the context was about describing what a work unit represents, not a specific doc type.

3. **Governed prompt boundaries** -- Several surviving task prompts (`implementation_plan`, `technical_architecture`, PGC prompts) contain epic references in their prompt text. Per user resolution, these are deferred to WS-PIPELINE-004 because editing prompts requires version bumps under seed governance rules. No `.prompt.txt` files were touched.

4. **story_backlog functional code untouched** -- The entire story_backlog chain (`app/domain/services/story_backlog_service.py`, `app/api/routers/commands.py`, `app/web/routes/public/document_routes.py`, `app/domain/registry/loader.py` seed data) contains heavy epic references (`epic_id`, `epics[]`, `EpicBacklog`). All deferred to WS-REGISTRY-002 per user resolution. This accounts for the majority of remaining `epic` grep hits in `app/`.

5. **test_spawn_child_documents.py** -- This test was missed in Phase 5 (subagent did not catch it because the test fixture uses raw module loading to avoid circular imports, and the assertion was `"epic"` as a string value rather than a code symbol). Found it during Tier 0 and fixed it.

6. **Pre-existing workflow test failures** -- 6 tests in `tests/domain/workflow/` fail due to SPD workflow V9 validation (iteration source references `work_package` doc type which lacks `collection_field: "work_packages"`). This is a WS-PIPELINE-001 issue -- the SPD workflow definition was changed in a prior commit. Confirmed pre-existing by stashing changes and re-running.

---

## Verification Summary

| Check | Result |
|-------|--------|
| Structural BCP identifier grep (`BacklogItem\|PlanExplanation\|backlog_item\|plan_explanation` in app/) | ZERO matches |
| Registry integrity (`check_registry_integrity.py`) | 62/62 PASS |
| Lint (ruff) | PASS |
| Typecheck (mypy) | PASS |
| Frontend build (vite) | PASS |
| Tests | 2464 passed, 33 skipped, 20 failed (all pre-existing) |

### Pre-existing failures (not from this work)

- 13 `test_skills_decomposition` (CLAUDE.md sizing)
- 1 `test_ws_metrics` (migration file)
- 6 workflow tests (SPD workflow V9 validation -- WS-PIPELINE-001 issue)

### New failures introduced: ZERO

---

## File Count Summary

| Action | Count |
|--------|-------|
| Config dirs archived | 28 |
| App files deleted | 12 |
| Test files deleted | 7 |
| Config files edited | 4 |
| App files edited | ~32 |
| Test files edited | 10 |

---

_End of WS-PIPELINE-003 Change Audit_

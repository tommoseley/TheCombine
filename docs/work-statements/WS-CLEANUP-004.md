# WS-CLEANUP-004: Backend Module Decomposition

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — Medium finding: oversized modules, workspace service sprawl

## Verification Mode: A

## Allowed Paths

- app/domain/workflow/
- app/api/services/workspace_service.py
- app/api/services/
- app/api/v1/routers/projects.py
- app/api/v1/routers/
- app/api/v1/__init__.py
- tests/

---

## Objective

Decompose three oversized backend Python modules into focused sub-modules to reduce cognitive load and improve maintainability:

1. `app/domain/workflow/plan_executor.py` (2423 LOC) → core + 6 extracted helpers
2. `app/api/services/workspace_service.py` (2134 LOC) → core + extracted scaffolders
3. `app/api/v1/routers/projects.py` (2071 LOC) → parent router + sub-routers

---

## Preconditions

- 4857 tests passing
- WS-CLEANUP-003 completed (domain/API boundary fix applied to plan_executor.py)

---

## Scope

### In Scope

#### plan_executor.py Decomposition

Extract the following cohesive groups into sibling modules in `app/domain/workflow/`:

| Extract | Target | Content |
|---------|--------|---------|
| QA retry logic | `qa_retry_handler.py` | `_prepare_qa_retry_tracking`, `_handle_qa_retry_feedback`, `_extract_qa_feedback`, `_find_generating_node` |
| Invariant/constraint ops | `invariant_processor.py` | `_pin_invariants_*`, `_filter_excluded_*`, `_promote_pgc_*`, `_embed_pgc_*`, `_build_invariant_statement` |
| Child document spawning | `child_document_manager.py` | `_spawn_child_documents`, `_upsert_child_document`, stale marking, upsert loop, commit/notify |
| Event emission | `execution_event_emitter.py` | `_emit_stations_declared`, `_emit_station_changed`, `_emit_internal_step` |
| Thread/governance recording | `execution_recorder.py` | `_persist_conversation`, `_sync_thread_status`, `_record_governance_outcome` |
| PGC processing | `pgc_processor.py` | `_handle_pgc_user_answers`, `_get_pgc_questions_for_merge`, `_load_pgc_answers_for_qa` |

Core `plan_executor.py` retains: `__init__`, `start_execution`, `execute_step`, `run_to_completion_or_pause`, `_execute_node`, `_handle_result`, `_advance_to_next_node`, `submit_user_input`, `handle_escalation_choice`.

#### workspace_service.py Decomposition

Extract into sibling modules in `app/api/services/`:

| Extract | Target | Content |
|---------|--------|---------|
| Artifact ID operations | `artifact_id_resolver.py` | `_parse_artifact_id`, `_artifact_id_to_path`, `_resolve_fragment_path`, `_path_to_artifact_id` |
| Release management | `release_manager.py` | All `_update_active_releases*` methods |
| Scaffolding operations | `workspace_scaffolders.py` | `create_orchestration_workflow`, `create_document_type`, `create_dcw_workflow`, `create_role_prompt`, `create_template`, `create_standalone_schema` + their delete counterparts |

Core `workspace_service.py` retains: constructor, lifecycle (`create_workspace`, `close_workspace`, `get_current_workspace`, `cleanup_expired_workspaces`), state (`get_workspace_state`), artifact CRUD (`get_artifact`, `write_artifact`, `get_diff`, `get_preview`, `commit`, `discard`).

#### projects.py Decomposition

Split into sub-routers in `app/api/v1/routers/`:

| Extract | Target | Content |
|---------|--------|---------|
| Document routes + helpers | `projects_documents.py` | Document get/render/render-model/PGC endpoints + all `_render_*_summary` helpers + `_prepare_document_content`, `_repair_truncated_json`, `_build_pgc_from_*` |
| Workflow routes | `projects_workflows.py` | Workflow get/update/drift/history/complete endpoints |
| Work package routes | `projects_workpackages.py` | WP list/generate/get-ws/generate-ws endpoints |

Core `projects.py` retains: CRUD routes (list, create, get, patch, archive, unarchive, delete), tree, interrupts, shared helpers (`_resolve_project`, `_project_to_response`). Includes sub-routers.

### Out of Scope

- Frontend module decomposition (separate WS-CLEANUP-005)
- Changing any business logic or API contracts
- Adding new features

---

## Prohibited Actions

- Do not change any API endpoint paths, request/response schemas, or behavior
- Do not change any business logic
- Do not rename public functions or classes (internal `_` prefixed methods may be moved)
- Do not merge or split any existing tests — only update imports

---

## Procedure

### Phase 1: plan_executor.py

1. Create each target module, moving the specified methods as module-level functions or classes
2. Methods that reference `self` state become functions that accept the needed state as parameters, OR become methods on a helper class that receives required dependencies
3. Update `plan_executor.py` to import from new modules and delegate
4. Run tests — all must pass

### Phase 2: workspace_service.py

5. Extract `artifact_id_resolver.py` — pure functions, no state dependency
6. Extract `release_manager.py` — operates on `active_releases.json`, needs workspace path
7. Extract `workspace_scaffolders.py` — creation methods that need workspace context
8. Update `workspace_service.py` to import and delegate
9. Run tests — all must pass

### Phase 3: projects.py

10. Create sub-routers with `APIRouter(prefix="", tags=[...])` — same path prefix, just organized
11. Move endpoint functions + their helper functions to sub-router modules
12. Include sub-routers in main `projects.py` router
13. Share `_resolve_project` and `_project_to_response` via a `projects_common.py` or direct import
14. Run tests — all must pass

### Phase 4: Verify

15. Run full test suite
16. Verify no import errors: `python -c "from app.api.main import app"`
17. Run Tier 0

---

## Verification Checklist

- [ ] `plan_executor.py` core is under 1000 LOC
- [ ] `workspace_service.py` core is under 800 LOC
- [ ] `projects.py` core is under 600 LOC
- [ ] All extracted modules exist and contain the specified functions
- [ ] No API endpoint paths or behaviors changed
- [ ] All tests pass
- [ ] Tier 0 passes

## Definition of Done

Three oversized backend modules decomposed into focused sub-modules. All existing behavior preserved. All tests pass. Core modules are each under their LOC targets.

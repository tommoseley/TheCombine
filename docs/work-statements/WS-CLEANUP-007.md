# WS-CLEANUP-007: Remaining Large Module Decomposition

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — Remaining maintainability finding: still-large modules after first decomposition wave
- WS-CLEANUP-004 (first backend decomposition pass)
- WS-CLEANUP-005 (first frontend decomposition pass)

## Verification Mode: A

## Allowed Paths

- app/api/v1/routers/
- app/api/services/
- app/domain/workflow/
- spa/src/components/
- spa/src/hooks/
- tests/

---

## Objective

Perform a second-wave decomposition of the largest remaining modules that still carry high cognitive load after WS-CLEANUP-004 and WS-CLEANUP-005.

Primary targets:

1. `app/api/v1/routers/work_binder.py`
2. `app/api/v1/routers/admin_workspaces.py`
3. `app/domain/workflow/plan_executor.py`
4. `spa/src/components/admin/workflow/StepWorkflowEditor.jsx`
5. `app/api/services/admin_workbench_service.py` (if still oversized after related extractions)

The goal is not to keep splitting for its own sake. The goal is to carve out coherent submodules with clearer responsibility boundaries.

---

## Preconditions

- WS-CLEANUP-004 completed
- WS-CLEANUP-005 completed
- WS-CLEANUP-006 completed or intentionally deferred if not required for these targets
- 4843 tests passing
- SPA build passing

---

## Scope

### In Scope

#### 1. `work_binder.py` decomposition

Split `app/api/v1/routers/work_binder.py` into sub-routers by responsibility.

Suggested extraction:

| Extract | Target | Content |
|---------|--------|---------|
| Candidate endpoints | `work_binder_candidates.py` | list/import/promote candidate routes |
| Work statement endpoints | `work_binder_statements.py` | create/update/list/reorder/stabilize WS routes |
| Proposal endpoints | `work_binder_proposals.py` | propose WS and related generation routes |
| Shared helpers/models | `work_binder_common.py` | shared request/response models, project/doc resolution helpers |

Core `work_binder.py` retains router assembly and any truly shared glue.

#### 2. `admin_workspaces.py` decomposition

Split `app/api/v1/routers/admin_workspaces.py` by operation family.

Suggested extraction:

| Extract | Target | Content |
|---------|--------|---------|
| Workspace lifecycle | `admin_workspaces_lifecycle.py` | open/close/state/discard/commit routes |
| Artifact operations | `admin_workspaces_artifacts.py` | get/write/diff/preview routes |
| Scaffold operations | `admin_workspaces_scaffold.py` | create/delete workflow/doc type/schema/template/role routes |
| Shared models/helpers | `admin_workspaces_common.py` | request/response models, workspace resolution |

Core `admin_workspaces.py` retains router composition only.

#### 3. `plan_executor.py` second-wave reduction

Reduce `app/domain/workflow/plan_executor.py` further by extracting additional cohesive units left behind after WS-CLEANUP-004.

Candidate extractions:

| Extract | Target | Content |
|---------|--------|---------|
| State/context assembly | `execution_context_builder.py` | `_build_context`, related assembly helpers |
| Result transition logic | `execution_result_handler.py` | `_handle_result`, `_handle_terminal_node`, `_advance_to_next_node` delegates if still too dense |
| Persistence/status queries | `execution_status_service.py` | `get_execution_status`, `list_executions`, related DTO shaping |

Do not force all three if one is unnecessary; extract only where it meaningfully reduces complexity.

#### 4. `StepWorkflowEditor.jsx` decomposition

Split the remaining large workflow editor module into focused components.

Suggested extraction:

| Extract | Target | Content |
|---------|--------|---------|
| Toolbar / controls | `workflowEditorSections/EditorToolbar.jsx` | zoom/layout/add/remove/save controls |
| Step list / palette | `workflowEditorSections/StepPalette.jsx` | available node/step insertion UI |
| Canvas wrapper | `workflowEditorSections/WorkflowCanvasShell.jsx` | canvas orchestration / layout wrapper |
| Shared workflow editor hooks | `spa/src/hooks/useStepWorkflowEditor.js` | local editor state/actions if logic is embedded in component |

Core `StepWorkflowEditor.jsx` retains composition and top-level state ownership.

#### 5. `admin_workbench_service.py` review-and-extract

If `app/api/services/admin_workbench_service.py` still contains multiple unrelated responsibilities, extract focused helpers for:

- prompt/package scanning
- artifact metadata assembly
- DCW/workflow discovery helpers

If the module is already coherent enough after related cleanup, no extraction is required.

### Out of Scope

- New business logic
- API path or schema changes
- Frontend visual redesign
- Work Binder business-rule refactors
- Rewriting the workflow editor interaction model

---

## Prohibited Actions

- Do not change endpoint paths or API contracts
- Do not change request/response JSON shapes
- Do not change behavior of Work Binder, admin workspaces, or workflow editing
- Do not create decomposition that merely moves code without improving responsibility boundaries
- Do not split modules into tiny fragments with no ownership clarity

---

## Procedure

### Phase 1: Backend routers

1. Extract `work_binder.py` into sub-routers by responsibility
2. Extract `admin_workspaces.py` into sub-routers by responsibility
3. Keep shared models/helpers in explicit `*_common.py` modules where needed
4. Verify router composition preserves identical paths and tags

### Phase 2: Plan executor second pass

5. Inspect remaining `plan_executor.py` hot spots
6. Extract only the next cohesive cluster(s) that materially reduce LOC and local complexity
7. Keep `PlanExecutor` as the orchestration façade

### Phase 3: Frontend editor

8. Extract `StepWorkflowEditor.jsx` subcomponents and optional hook
9. Preserve props contracts and visual behavior
10. Run SPA build

### Phase 4: Optional admin workbench service extraction

11. If still justified, extract helper modules from `admin_workbench_service.py`
12. Otherwise document explicitly that no extraction was needed

### Phase 5: Verify

13. Run `python -m pytest tests/ -x -q`
14. Run `cd spa && npm run build`
15. Run Tier 0

---

## Verification Checklist

- [ ] `work_binder.py` core is materially reduced and delegated to sub-routers
- [ ] `admin_workspaces.py` core is materially reduced and delegated to sub-routers
- [ ] `plan_executor.py` is further reduced or explicitly justified if no additional safe extraction exists
- [ ] `StepWorkflowEditor.jsx` core is materially reduced
- [ ] `admin_workbench_service.py` reviewed and extracted if warranted
- [ ] No endpoint paths or behaviors changed
- [ ] No UI behavior changed
- [ ] All tests pass
- [ ] SPA build passes
- [ ] Tier 0 passes

## Definition of Done

The largest remaining modules after the first cleanup wave are decomposed into focused, responsibility-aligned submodules. Public behavior is unchanged, and all tests and frontend build checks pass.

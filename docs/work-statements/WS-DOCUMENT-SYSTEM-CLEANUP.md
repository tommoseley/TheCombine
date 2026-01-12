# WS-DOCUMENT-SYSTEM-CLEANUP

| Field | Value |
|-------|-------|
| **Work Statement** | WS-DOCUMENT-SYSTEM-CLEANUP |
| **Status** | Draft |
| **Owner** | Platform / Architecture |
| **Charter** | [Document System Charter](./document-system-charter.md) |
| **Implementation Plan** | [Document Cleanup Plan](./document-cleanup-plan.md) |
| **Related ADRs** | ADR-031, ADR-033, ADR-034, ADR-036 |
| **Supersedes** | WS-DOCUMENT-VIEWER-TABS (enum-based tabs) |
| **Type** | Infrastructure + Governance |
| **Estimated Scope** | 9 phases, independently deployable |

---

## Purpose

Implement the Document System Charter by eliminating three systemic failure modes:

1. **Config Drift** — Hardcoded `DOCUMENT_CONFIG` shadows database
2. **Schema Drift** — Schema evolution breaks historical documents
3. **Route Drift** — Implicit, duplicated, deprecated paths

This WS transitions The Combine from prototype to production-grade document platform.

---

## Non-Negotiable Constraints

- RenderModelV1 remains the sole rendering contract
- All phases independently deployable
- All phases have explicit rollback paths
- No silent route removals (redirect + Warning header required)
- Golden trace tests for all structural changes
- Schema changes never retroactively mutate documents
- No blocking UI during generation
- No auto-regeneration of documents
- No destruction of partial/stale documents

---

## Phase Overview

| Phase | Goal | Drift Fixed | Dependency |
|-------|------|-------------|------------|
| 1 | Config → DB only | Config | None |
| 2 | Schema hash persistence | Schema | None |
| 3 | Document lifecycle states | — | Phase 2 |
| 4 | Staleness propagation | — | Phase 3 |
| 5 | Route deprecation | Route | None |
| 6 | Legacy template feature flag | — | None |
| 7 | Command route normalization | Route | Phase 5 |
| 8 | Debug routes to dev-only | — | None |
| 9 | Data-driven UX (optional) | — | Phase 3 |

**Parallelization**: Phases 1, 2, 5, 6, 8 can run in parallel. Phases 3→4→9 are sequential.

---

## Phase 1: Config Consolidation

### Goal
Eliminate `DOCUMENT_CONFIG` hardcoding. DB becomes sole source of truth.

### Changes

| File | Change |
|------|--------|
| `alembic/versions/xxx_add_view_docdef_prefix.py` | Add `view_docdef_prefix` column to `document_types` |
| `app/domain/services/document_type_service.py` | Read prefix from DB, remove hardcoded fallback |
| `app/config/document_config.py` | Delete or deprecate |
| `seed/document_types.json` | Add `view_docdef_prefix` values |

### Acceptance Criteria

- [ ] `document_types` table has `view_docdef_prefix` column
- [ ] All document types seeded with correct prefix
- [ ] No code references `DOCUMENT_CONFIG` for docdef resolution
- [ ] Changing prefix in DB changes rendering (no deploy)
- [ ] Test: `test_docdef_resolution_from_db()`

### Rollback
Restore `DOCUMENT_CONFIG` fallback (code change + deploy).

---

## Phase 2: Schema Versioning

### Goal
Documents persist `schema_bundle_sha256`. Viewer resolves by hash, not "latest".

### Changes

| File | Change |
|------|--------|
| `alembic/versions/xxx_add_schema_hash.py` | Add `schema_bundle_sha256` to `documents` |
| `app/domain/services/document_service.py` | Persist hash on save |
| `app/domain/services/render_model_builder.py` | Include hash in RenderModel |
| `app/domain/services/schema_resolver.py` | Lookup by hash when rendering |

### Acceptance Criteria

- [ ] `documents.schema_bundle_sha256` column exists
- [ ] New documents persist hash at generation time
- [ ] Viewer uses persisted hash (not latest schema)
- [ ] Schema evolution does not break old documents
- [ ] Test: `test_schema_bundle_determinism()`
- [ ] Test: `test_historical_document_renders_with_original_schema()`

### Rollback
Column is additive. Viewer falls back to latest if hash missing.

---

## Phase 3: Document Lifecycle States

### Goal
Implement ADR-036 states: `missing`, `generating`, `partial`, `complete`, `stale`.

### Changes

| File | Change |
|------|--------|
| `alembic/versions/xxx_add_document_state.py` | Add `state` enum, `state_changed_at` to `documents` |
| `app/api/models/document.py` | Add state field with enum |
| `app/domain/services/document_service.py` | State transition logic |
| `app/domain/services/render_model_builder.py` | Include state in metadata |
| `app/web/templates/.../viewer` | Render state indicators |

### State Transitions (from ADR-036)

```
missing → generating → partial ←→ complete → stale
                ↑          ↑                    │
                └──────────┴─── regenerate ─────┘
```

### Acceptance Criteria

- [ ] `documents.state` enum column exists
- [ ] `documents.state_changed_at` timestamp exists
- [ ] State transitions validated (invalid transitions rejected)
- [ ] RenderModelV1 includes `metadata.state`
- [ ] Viewer shows state indicator (generating=spinner, stale=amber)
- [ ] Partial documents render available sections
- [ ] Test: `test_state_transitions()`
- [ ] Test: `test_partial_document_renders()`

### Rollback
State column is additive. Viewer treats missing state as `complete`.

---

## Phase 4: Staleness Propagation

### Goal
Upstream document changes mark downstream documents as `stale`.

### Changes

| File | Change |
|------|--------|
| `app/domain/services/staleness_service.py` | New: `StalenessService.propagate()` |
| `app/domain/services/document_service.py` | Hook staleness propagation on save |
| `seed/document_type_dependencies.json` | Dependency graph config |

### Dependency Graph

| Document Type | Depends On |
|--------------|------------|
| `epic_backlog` | `project_discovery` |
| `story_backlog` | `epic_backlog` |
| `technical_architecture` | `epic_backlog` |

### Acceptance Criteria

- [ ] Dependency graph defined in config/DB
- [ ] Saving upstream doc marks downstream as `stale`
- [ ] Staleness does NOT cascade (only direct dependents)
- [ ] Downstream docs remain viewable when stale
- [ ] No auto-regeneration triggered
- [ ] Test: `test_staleness_propagates_downstream()`
- [ ] Test: `test_staleness_does_not_cascade()`

### Rollback
Remove hook from document save. Staleness stops propagating.

---

## Phase 5: Route Deprecation

### Goal
Old routes redirect to canonical with `Warning: 299 Deprecated` header.

### Changes

| File | Change |
|------|--------|
| `app/web/middleware/deprecation.py` | New: Deprecation middleware |
| `app/web/routes/documents.py` | Add redirects for old routes |
| `app/core/logging.py` | Log deprecated route hits |

### Deprecated Routes

| Old Route | Canonical Route | Action |
|-----------|-----------------|--------|
| `/projects/{id}/epic-backlog` | `/projects/{id}/documents/epic_backlog` | 301 + Warning |
| `/projects/{id}/discovery` | `/projects/{id}/documents/project_discovery` | 301 + Warning |
| `/view/{doc_type}/preview` | `/admin/preview/{doc_type}` | 301 + Warning |

### Acceptance Criteria

- [ ] Deprecated routes return 301 redirect
- [ ] Response includes `Warning: 299` header
- [ ] Deprecated route hits logged with route + timestamp
- [ ] Canonical routes work without warning
- [ ] Test: `test_deprecated_route_redirects()`
- [ ] Test: `test_warning_header_emitted()`

### Rollback
Remove middleware. Old routes return 404.

---

## Phase 6: Legacy Template Feature Flag

### Goal
Enable instant rollback to legacy templates via environment variable.

### Changes

| File | Change |
|------|--------|
| `app/config/settings.py` | Add `USE_LEGACY_TEMPLATES` flag (default: False) |
| `app/web/templates/` | Move legacy to `recycle/` folder |
| `app/domain/services/template_resolver.py` | Check flag, resolve from recycle/ if True |

### Acceptance Criteria

- [ ] `USE_LEGACY_TEMPLATES=true` enables legacy templates
- [ ] `USE_LEGACY_TEMPLATES=false` (default) uses new templates
- [ ] Switching flag requires no redeploy (env var only)
- [ ] Legacy templates preserved in `recycle/` folder
- [ ] Test: `test_legacy_template_flag()`

### Rollback
Set `USE_LEGACY_TEMPLATES=true` in environment.

---

## Phase 7: Command Route Normalization

### Goal
All commands under `/api/commands/{domain}/{action}`.

### Changes

| File | Change |
|------|--------|
| `app/api/routes/commands.py` | Consolidate command routes |
| `app/web/routes/*.py` | Redirect old command routes |

### Route Mapping

| Old Route | Canonical Route |
|-----------|-----------------|
| `/bff/epic-backlog/build` | `/api/commands/documents/build` |
| `/bff/story-backlog/generate` | `/api/commands/documents/generate` |
| `/api/projects/{id}/generate` | `/api/commands/documents/generate` |

### Acceptance Criteria

- [ ] All commands accessible via `/api/commands/...`
- [ ] Old routes redirect with deprecation warning
- [ ] Commands return `task_id` for async tracking
- [ ] SSE endpoints under `/api/commands/.../stream`
- [ ] Test: `test_command_routes_normalized()`

### Rollback
Restore old route handlers alongside new.

---

## Phase 8: Debug Routes to Dev-Only

### Goal
Debug/diagnostic routes only available when `DEBUG=true`.

### Changes

| File | Change |
|------|--------|
| `app/api/routes/debug.py` | Wrap with environment check |
| `app/web/routes/admin.py` | Protect sensitive admin routes |

### Protected Routes

- `/debug/*`
- `/api/internal/*`
- `/admin/schema-browser`
- `/admin/render-debug`

### Acceptance Criteria

- [ ] Protected routes return 404 in production
- [ ] Protected routes work when `DEBUG=true`
- [ ] No information leakage in production 404
- [ ] Test: `test_debug_routes_hidden_in_production()`

### Rollback
Remove environment check.

---

## Phase 9: Data-Driven UX (Optional)

### Goal
CTAs, badges, display variants, visibility rules configurable via data.

### Changes

| File | Change |
|------|--------|
| `alembic/versions/xxx_add_ux_config.py` | Add `state_badges` to `document_types`, UX fields to docdefs |
| `app/web/templates/.../partials/_document_not_found.html` | Read CTA from docdef |
| `app/web/templates/.../components/project_list.html` | Read badges from document_types |
| `app/domain/services/fragment_renderer.py` | Apply `display_variant` CSS class |

### Data-Driven Elements

| Element | Location | Example |
|---------|----------|---------|
| CTA label/icon | `docdef.primary_action` | `{"label": "Begin Research", "icon": "compass"}` |
| State badges | `document_types.state_badges` | `{"stale": {"icon": "alert-circle", "color": "amber"}}` |
| Display variant | `section.display_variant` | `"compact"`, `"expanded"` |
| Collapse default | `section.default_collapsed` | `true` |
| Visibility | `section.visibility_rules` | `{"show_if_empty": false}` |

### Acceptance Criteria

- [ ] CTA label/icon from docdef (no HTML changes)
- [ ] Badge icon/color from document_types (no HTML changes)
- [ ] `display_variant` applies CSS class to fragment
- [ ] Empty sections hidden when `show_if_empty: false`
- [ ] Test: `test_cta_from_docdef()`
- [ ] Test: `test_badges_from_document_type()`

### Rollback
Keep hardcoded fallbacks if data missing.

---

## Governance Artifacts (Deliverables)

| Artifact | Location | Status |
|----------|----------|--------|
| ROUTING_CONTRACT.md | `docs/governance/` | To create |
| SCHEMA_SOURCING_RULES.md | `docs/governance/` | To create |
| VIEWER_INVARIANTS.md | `docs/governance/` | To create |
| DOCUMENT_LIFECYCLE.md | `docs/governance/` | To create |
| VIEWER_TABS_CONTRACT.md | `docs/governance/` | To create |
| DATA_DRIVEN_UX.md | `docs/governance/` | To create |

These artifacts are defined in the cleanup plan and should be created as each phase completes.

---

## Test Plan

### Golden Trace Tests (Mandatory)

| Document Type | Snapshot |
|---------------|----------|
| EpicBacklogView | `tests/golden/epic_backlog_render.json` |
| StoryBacklogView | `tests/golden/story_backlog_render.json` |
| ProjectDiscoveryView | `tests/golden/discovery_render.json` |
| ArchitecturalSummaryView | `tests/golden/architecture_render.json` |
| StoryDetailView | `tests/golden/story_detail_render.json` |

**Rule**: Structural changes to RenderModel fail tests. Humans must review diffs.

### Integration Tests

- `test_end_to_end_document_generation()`
- `test_partial_generation_workflow()`
- `test_staleness_indicator_displayed()`
- `test_route_deprecation_logging()`

---

## Success Criteria

This WS is complete when:

1. [ ] All 8 required phases pass acceptance criteria
2. [ ] Phase 9 completed OR explicitly deferred
3. [ ] All 6 governance artifacts created
4. [ ] Golden trace tests passing
5. [ ] No hardcoded `DOCUMENT_CONFIG` references
6. [ ] All deprecated routes emit Warning header
7. [ ] ADR-INVENTORY updated with implementation status
8. [ ] WS-DOCUMENT-VIEWER-TABS marked superseded

---

## Failure Conditions (Automatic Reject)

- HTML in JSON payloads
- Blocking UI during generation
- Auto-regeneration without user action
- Silent route removal (no redirect)
- Schema change breaks historical document
- State transition bypasses validation

---

## Suggested Execution Order

```
Week 1: Phases 1, 2, 6, 8 (parallel, no dependencies)
Week 2: Phase 5, Phase 3
Week 3: Phase 4, Phase 7
Week 4: Phase 9, governance docs, golden traces
```

Adjust based on team capacity. Each phase is a separate PR.

---

## Notes

- This WS implements the [Document System Charter](./document-system-charter.md)
- Detailed steps are in [Document Cleanup Plan](./document-cleanup-plan.md)
- Governance gaps analyzed in [ADR Amendment Analysis](./adr-amendment-analysis.md)
- ADR-036 (Document Lifecycle) is the governing ADR for Phase 3-4

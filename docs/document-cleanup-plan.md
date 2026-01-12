# Document Rendering & Generation Cleanup Plan v2

> **Governing Document**: This plan implements the [Document System Charter](./document-system-charter.md).
> 
> **Purpose**: Detailed implementation phases, test plans, and governance artifacts.
> All phases are independently deployable with explicit rollback paths.
> 
> **Related**: [ADR Amendment Analysis](./adr-amendment-analysis.md) for governance gap analysis.

---

## Executive Summary (11 bullets)

1. **RenderModelV1 is the hourglass waist**: All document rendering flows through RenderModelV1—no exceptions. Viewers never depend on docdefs, schemas, or generation logic.

2. **Two config sources must consolidate**: `DOCUMENT_CONFIG` hardcoding duplicates `document_types` table. Phase 1 eliminates code-level config entirely.

3. **Schema versioning is mandatory**: Documents must persist `schema_bundle_sha256`. Viewer resolves schemas by hash, not "latest". Schema changes never retroactively mutate documents.

4. **Document lifecycle is explicit**: Five states (missing -> generating -> partial -> complete -> stale) with defined actions per state. Partial documents are valid documents.

5. **Projection is first-class**: Summary documents (StoryBacklog) link to detail documents (StoryDetail) via `detail_ref`. Projection is intentional data loss, not omission.

6. **Staleness propagates automatically**: Upstream document changes mark dependents stale. This is a system invariant, not optional behavior.

7. **Route deprecation requires redirects**: Old routes emit `Warning: Deprecated` header and redirect—never silent removal.

8. **Legacy template removal is reversible**: Feature flag `USE_LEGACY_TEMPLATES=true` enables instant rollback without redeploy.

9. **Async UX is the default**: Long-running generation never blocks navigation. SSE preferred over polling. Per-epic completion reflected independently.

10. **Golden trace renders are mandatory**: RenderModel snapshots checked into Git. Structural changes fail tests and require human review.

11. **UX is data-driven by default**: CTAs, badges, display variants, and visibility rules are configured in document definitions—not hardcoded in templates. UX tuning requires no code changes.

---

## A) Inventory & Drift Map

### A.1 Routes Involved in Document Viewing

| Route | File | Function | Purpose | Status |
|-------|------|----------|---------|--------|
| `GET /projects/{id}/documents/{type}` | `document_routes.py` | `get_document()` | Main document viewer | **Canonical** |
| `POST /projects/{id}/documents/{type}/build` | `document_routes.py` | `build_document()` | Trigger generation | **Canonical** |
| `GET /tasks/{task_id}/status` | `document_routes.py` | `get_task_status()` | Poll build progress | **Canonical** |
| `GET /view/{type}` | `view_routes.py` | `view_document()` | ADR-034 stored doc view | **Deprecate** |
| `POST /view/{type}/preview` | `view_routes.py` | `preview_document()` | ADR-034 preview render | **Move to admin** |

### A.2 Routes Involved in Document Building

| Route | File | Function | Purpose | Status |
|-------|------|----------|---------|--------|
| `POST /api/documents/build/{type}` | `documents.py` | `build_document()` | API build trigger | **Deprecate -> redirect** |
| `POST /api/documents/build/{type}/stream` | `documents.py` | `build_document_stream()` | SSE streaming build | **Keep (SSE canonical)** |
| `POST /api/commands/story-backlog/init` | `commands.py` | `init_story_backlog()` | Init story backlog | **Canonical** |
| `POST /api/commands/story-backlog/generate-epic` | `commands.py` | `generate_epic()` | Generate single epic | **Canonical** |
| `POST /api/commands/story-backlog/generate-all` | `commands.py` | `generate_all()` | Generate all epics | **Canonical** |

### A.3 The Three Drifts

| Drift Type | Location | Problem | Resolution |
|------------|----------|---------|------------|
| **Config Drift** | `DOCUMENT_CONFIG` dict | Hardcoded fallbacks create ghost bugs | DB is sole source (Phase 1) |
| **Schema Drift** | `role_tasks.expected_schema` | Schema evolution breaks historical documents | Persist `schema_bundle_sha256` (Phase 2) |
| **Route Drift** | Multiple route files | Old routes silently breaking clients | Redirect + Warning header (Phase 7) |

### A.4 Document Type Resolution (Current State)

| Location | Resolution Method | Problem |
|----------|-------------------|---------|
| `document_routes.py:137` | `DOCUMENT_CONFIG = {...}` | Shadows DB |
| `document_routes.py:264` | `fallback_config = DOCUMENT_CONFIG.get(...)` | Code determines behavior |
| `loader.py:49` | `get_document_config(db, doc_type_id)` | Should be only source |
| `document_routes.py:349` | `view_docdef = fallback_config.get("view_docdef")` | Hardcoded mapping |

### A.5 Schema Sourcing (Current State)

| Location | Schema Source | Problem |
|----------|---------------|---------|
| `role_tasks.expected_schema` | Embedded JSONB | Not versioned, mutable |
| `schema_artifacts` table | Schema Registry | Correct source |
| `component_registry.schema_id` | Reference | Correct pattern |
| **Missing** | `documents.schema_bundle_sha256` | Documents don't persist schema version |
---

## B) Target Architecture

### B.1 The Hourglass Waist (Frozen)

```
+-------------------------------------------------------------+
|                    GENERATION SIDE                          |
|  LLM Output -> Validation -> Stored Document                |
+-------------------------------------------------------------+
                            |
                            v
              +-----------------------------+
              |      RenderModelV1          |  <- SOLE CONTRACT
              |  (The Hourglass Waist)      |
              +-----------------------------+
                            |
                            v
+-------------------------------------------------------------+
|                    RENDERING SIDE                           |
|  RenderModel -> Fragments -> HTML                           |
+-------------------------------------------------------------+
```

**Rule**: LLM output is never rendered directly.

### B.2 Separation of Responsibilities (Frozen)

| Layer | Responsibility |
|-------|---------------|
| **Stored Document** | Canonical, normalized, viewer-ready data |
| **LLM Output** | Ephemeral, intermediate artifact |
| **DocDef** | Structural projection rules |
| **Component** | Semantic contract + guidance |
| **Fragment** | Presentation only |
| **Viewer** | Stateless renderer of RenderModel |

### B.3 Document Lifecycle Contract (New - Frozen)

```
missing -> generating -> partial -> complete -> stale
                ^                              |
                +-------- regenerate ----------+
```

| State | Renderable | Actions Allowed |
|-------|------------|-----------------|
| `missing` | No | `generate` |
| `generating` | Yes (skeleton) | `cancel` |
| `partial` | Yes | `generate section` |
| `complete` | Yes | `mark-stale` |
| `stale` | Yes (amber indicator) | `regenerate` |

**Rule**: Partial documents are valid documents.

### B.4 Projection Layer (New - Frozen)

| Document Type | Stores | Links To |
|--------------|--------|----------|
| `StoryBacklog` | Story summaries + refs | `StoryDetail` via `detail_ref` |
| `StoryDetail` | Full BA output | — |
| `EpicBacklog` | Epic summaries | `EpicArchitecture` via `detail_ref` |
| `EpicArchitecture` | Full architecture | — |
| `ArchitecturalSummary` | Derived indicators only | — |

**Rule**: Projection is intentional data loss, not omission.

### B.5 Viewer Tabs Contract (Frozen)

> Tabs are configuration, not architecture. No code changes required to add/remove/rename tabs.

**Core Principle**: Tabs are fully data-driven and defined entirely in document definitions.

**Section-Level Declaration**:
```json
"viewer_tab": {
  "id": "epics",
  "label": "Epics",
  "order": 20
}
```

**Tab Discovery Rules**:
1. Scan all sections in document definition
2. Collect unique `viewer_tab.id` values
3. Sort by `order` (ascending, default = 100)
4. Render dynamically - no registry, no whitelist

**Default Tab Resolution**:
1. If docdef declares `default_viewer_tab` -> use it
2. Else if tabs exist -> use first by order
3. Else -> render with no tabs UI

**Empty Tab Suppression**: Tabs with zero sections are NOT rendered.

**Tabs DO NOT**:
- Change block rendering or section ordering
- Affect schema validation or PromptAssembler
- Affect RenderModelBuilder semantics
- Affect persistence or derived fields

**Governance Boundary**:
| Change | Requires WS/ADR? |
|--------|------------------|
| Add/rename/reorder tabs | No |
| Move section between tabs | No |
| Change tab discovery mechanics | Yes |
| Introduce tab-specific behavior | Yes |

See D.5 VIEWER_TABS_CONTRACT.md for full specification.

### B.6 Staleness Propagation (New - Frozen)

| When This Changes | These Become Stale |
|-------------------|-------------------|
| Project Discovery | Epic Backlog |
| Epic Backlog | Story Backlog, Architectural Summary |
| Epic (individual) | Story Details for that epic |
| Architecture | Story Details |

**Implementation**: Service layer logic or explicit command calls.

### B.7 Schema Versioning (New - Mandatory)

Every stored document must persist:
- `schema_bundle_sha256`

**Rules**:
1. Viewer resolves schemas by hash, not "latest"
2. Schema upgrades do not retroactively mutate documents
3. If the schema changed, the document did not

### B.8 Canonical Route Structure

```
READ (View-Only):
  GET  /projects/{project_id}/documents/{doc_type_id}

COMMAND (Mutating):
  POST /api/commands/documents/{doc_type_id}/build
  POST /api/commands/documents/{doc_type_id}/mark-stale
  POST /api/commands/story-backlog/init
  POST /api/commands/story-backlog/generate-epic
  POST /api/commands/story-backlog/generate-all

SSE (Streaming):
  GET  /api/commands/documents/{doc_type_id}/build/stream
```

**Command Model Rules**:
1. All commands are async
2. All commands are idempotent where possible
3. All commands return a `task_id`
4. Commands mutate stored documents, never views

### B.9 Data-Driven UX Opportunities (Strategic)

> **Goal**: Maximize UX tunability without code changes or architectural review.

The following UX elements SHOULD be data-driven to enable rapid iteration:

#### B.9.1 Document-Level Call-to-Actions (CTAs)

**Current State**: "Generate" buttons hardcoded in `_document_not_found.html`

**Target State**: Add `primary_action` to document definitions:
```json
"primary_action": {
  "label": "Begin Research",
  "icon": "compass",
  "style": "primary"
}
```

**Benefit**: "Project Discovery" shows "Begin Research", "Story Backlog" shows "Synthesize Epics" - no HTML changes.

#### B.9.2 Component-Level Visual Variance

**Current State**: Fragment rendering uses fixed styles

**Target State**: Add `display_variant` to sections:
```json
"sections": [{
  "section_id": "stories",
  "display_variant": "compact"
}]
```

**Variants**: `compact`, `expanded`, `card`, `table`, `minimal`

**Benefit**: FragmentRenderer applies different Tailwind classes based on variant. Summary views use `compact`, detail views use `expanded`.

#### B.9.3 Sidebar State Badges

**Current State**: Icon/color logic hardcoded in `project_list.html`

**Target State**: Add badge configuration to `document_types`:
```json
"state_badges": {
  "missing": { "icon": "circle", "color": "gray" },
  "generating": { "icon": "loader-2", "color": "blue", "animate": "spin" },
  "complete": { "icon": "check-circle", "color": "green" },
  "stale": { "icon": "alert-circle", "color": "amber" }
}
```

**Benefit**: Changing "stale" from green-check to amber-alert is a database update, not a template change.

#### B.9.4 Section Collapse/Expand Defaults

**Target State**: Add `default_collapsed` to sections:
```json
"sections": [{
  "section_id": "implementation_notes",
  "default_collapsed": true
}]
```

**Benefit**: Long sections start collapsed, reducing cognitive load.

#### B.9.5 Conditional Section Visibility

**Target State**: Add `visibility_rules` to sections:
```json
"sections": [{
  "section_id": "security_section",
  "visibility_rules": {
    "show_if_empty": false,
    "min_items": 1
  }
}]
```

**Benefit**: Empty optional sections don't clutter the UI.

#### Governance Boundary (Data-Driven UX)

| Change | Requires WS/ADR? |
|--------|------------------|
| Change CTA label/icon | No |
| Add display variant | No |
| Change badge colors | No |
| Add new visibility rule type | Yes |
| Change FragmentRenderer logic | Yes |

See D.6 DATA_DRIVEN_UX.md for implementation guidance.

### B.9 Data-Driven UX Extensions (New)

> **Principle**: Tune the UX without architectural review or governance. If it's presentation, it's data.

The following UX elements SHOULD be data-driven to enable rapid iteration:

#### B.9.1 Document-Level Call-to-Actions (CTAs)

**Current Problem**: "Generate" buttons hardcoded in `_document_not_found.html`.

**Solution**: Add `primary_action` to `document_types` or `document_definitions`:

```json
"primary_action": {
  "label": "Begin Research",
  "icon": "compass",
  "variant": "primary"
}
```

**Benefit**: 
- "Project Discovery" → "Begin Research"
- "Story Backlog" → "Synthesize Epics"
- Change UX tone without touching HTML

#### B.9.2 Component-Level Visual Variance

**Current Problem**: Fragment rendering is one-size-fits-all.

**Solution**: Add `display_variant` to section or block definitions:

```json
"sections": [{
  "section_id": "story_list",
  "display_variant": "compact",  // or "expanded", "card", "table"
  ...
}]
```

**Benefit**:
- Compact story lists in summary views
- Expanded details in detail views
- FragmentRenderer applies appropriate Tailwind classes
- All via JSON config, no code changes

#### B.9.3 Sidebar Status Badges

**Current Problem**: Badge icons/colors hardcoded in `project_list.html`.

**Solution**: Add badge configuration to `document_types`:

```json
{
  "doc_type_id": "epic_backlog",
  "status_badges": {
    "missing": { "icon": "file-plus", "color": "gray" },
    "generating": { "icon": "loader-2", "color": "blue", "animate": "spin" },
    "complete": { "icon": "file-check", "color": "green" },
    "stale": { "icon": "alert-triangle", "color": "amber" }
  }
}
```

**Benefit**:
- Change "stale" from green-check to amber-alert via DB update
- Entire sidebar updates across all projects
- No template changes required

#### B.9.4 Section Conditional Visibility

**Solution**: Add `visibility_rules` to sections:

```json
"sections": [{
  "section_id": "security_considerations",
  "visibility_rules": {
    "show_if_empty": false,
    "collapse_by_default": true
  }
}]
```

**Benefit**: Optional sections don't clutter UI when empty.

#### Governance Boundary (Data-Driven UX)

| Change | Requires WS/ADR? |
|--------|------------------|
| Change CTA label/icon | No |
| Add display variant | No |
| Change badge colors | No |
| Add visibility rule | No |
| New variant type in FragmentRenderer | Yes |
| New badge animation type | Yes |
---

## C) Migration Plan (Phased)

### Phase 1: Consolidate Document Type Resolution
**Goal**: Eliminate `DOCUMENT_CONFIG` hardcoding. DB is sole source of truth.

**Files/Modules**:
- `app/web/routes/public/document_routes.py`
- `app/domain/registry/loader.py`
- `app/domain/registry/seed_document_types.py`
- `alembic/versions/xxx_add_view_docdef_prefix.py` (new)

**Steps**:
1. Create migration: add `view_docdef_prefix` column to `document_types`
2. Seed existing mappings:
   - `project_discovery` -> `ProjectDiscovery`
   - `epic_backlog` -> `EpicBacklogView`
   - `technical_architecture` -> `ArchitecturalSummaryView`
   - `story_backlog` -> `StoryBacklogView`
3. Update `get_document_config()` to return `view_docdef_prefix`
4. Remove `DOCUMENT_CONFIG` dict from `document_routes.py`
5. Update `get_document()` to use DB config exclusively

**Tests**:
- `test_get_document_config_from_db()`
- `test_no_hardcoded_document_config()`

**Rollback**: Revert migration, restore `DOCUMENT_CONFIG` (but this should never be needed)

---

### Phase 2: Schema Versioning & Registry Migration
**Goal**: Documents persist `schema_bundle_sha256`. Viewer resolves by hash.

**Files/Modules**:
- `app/api/models/document.py`
- `app/api/models/role_task.py`
- `app/api/services/role_prompt_service.py`
- `app/domain/services/render_model_builder.py`
- `alembic/versions/xxx_add_schema_bundle_sha.py` (new)

**Steps**:
1. Create migration: add `schema_bundle_sha256` column to `documents`
2. Create migration: add `schema_id` column to `role_tasks` (FK to schema_artifacts)
3. Migrate existing `expected_schema` JSONB to `schema_artifacts` entries
4. Update `role_tasks` rows with `schema_id` references
5. Modify document save to persist `schema_bundle_sha256`
6. Modify `RenderModelBuilder` to use persisted hash for schema resolution
7. Mark `expected_schema` column as deprecated

**Tests**:
- `test_document_persists_schema_hash()`
- `test_schema_bundle_determinism()` (same inputs -> same SHA)
- `test_viewer_uses_persisted_hash()`

**Rollback**: Feature flag `USE_LATEST_SCHEMA=true` to bypass hash resolution

---

### Phase 3: Document Lifecycle States
**Goal**: Implement explicit document states with allowed transitions.

**Files/Modules**:
- `app/api/models/document.py`
- `app/api/services/document_service.py`
- `app/web/routes/public/document_routes.py`
- `alembic/versions/xxx_add_document_state.py` (new)

**Steps**:
1. Create migration: add `state` enum column to `documents`
   - Values: `missing`, `generating`, `partial`, `complete`, `stale`
2. Add `state_changed_at` timestamp column
3. Implement state transition validation in `DocumentService`
4. Update `get_document()` to render based on state:
   - `generating` -> skeleton UI
   - `stale` -> amber indicator
5. Update build commands to set appropriate states

**Tests**:
- `test_document_state_transitions()`
- `test_partial_document_renders()`
- `test_stale_document_shows_indicator()`

**Rollback**: Default state to `complete` for existing documents

---

### Phase 4: Staleness Propagation
**Goal**: Upstream changes automatically mark dependents stale.

**Files/Modules**:
- `app/api/services/staleness_service.py` (new)
- `app/api/services/document_service.py`
- `app/domain/registry/loader.py`

**Steps**:
1. Define dependency graph in `document_types`:
   ```python
   DEPENDENCY_GRAPH = {
       "epic_backlog": ["project_discovery"],
       "story_backlog": ["epic_backlog"],
       "technical_architecture": ["epic_backlog"],
   }
   ```
2. Create `StalenessService.propagate(doc_type_id, project_id)`
3. Hook into document save: after save, call `propagate()`
4. Add `mark-stale` command endpoint

**Tests**:
- `test_staleness_propagates_downstream()`
- `test_staleness_does_not_propagate_upstream()`

**Rollback**: Disable propagation via feature flag

---

### Phase 5: Unify Route Structure with Deprecation Warnings
**Goal**: Single route pattern. Deprecated routes redirect with Warning header.

**Files/Modules**:
- `app/web/routes/public/view_routes.py`
- `app/web/routes/public/document_routes.py`
- `app/web/routes/__init__.py`
- `app/core/middleware/deprecation.py` (new)

**Steps**:
1. Create deprecation middleware that adds `Warning: 299 - "Deprecated"` header
2. Update `/view/{type}` to redirect to canonical route + emit warning
3. Update `/api/documents/build/{type}` to redirect + emit warning
4. Move `preview_document()` to `/api/admin/composer/preview/html/{docdef}`
5. Move `FragmentRenderer` from `view_routes.py` to `shared.py`
6. Log all deprecated route hits for monitoring

**Tests**:
- `test_deprecated_route_redirects()`
- `test_deprecated_route_emits_warning_header()`

**Rollback**: Remove middleware, restore direct handling

---

### Phase 6: Legacy Template Deprecation (with Feature Flag)
**Goal**: All rendering through RenderModelV1. Legacy templates behind feature flag.

**Files/Modules**:
- `app/web/routes/public/document_routes.py`
- `app/web/templates/public/pages/partials/_*_content.html`
- `app/core/config.py`

**Steps**:
1. Add feature flag: `USE_LEGACY_TEMPLATES` (default: `false`)
2. Add fallback logging: warn when legacy template is used
3. Update `get_document()`:
   ```python
   if settings.USE_LEGACY_TEMPLATES:
       return legacy_render(...)
   return render_model_render(...)
   ```
4. Ensure all 4 document types have working docdefs
5. Test each document type with new viewer
6. Move legacy templates to `recycle/` (but keep flag operational)

**Tests**:
- Golden renders for all document types
- `test_feature_flag_enables_legacy()`
- `test_no_fallback_warnings_in_logs()`

**Rollback**: Set `USE_LEGACY_TEMPLATES=true` in environment

---

### Phase 7: Command Route Normalization
**Goal**: All document commands under `/api/commands/`.

**Files/Modules**:
- `app/api/routers/commands.py`
- `app/api/routers/documents.py`

**Steps**:
1. Add new canonical routes in `commands.py`:
   - `POST /api/commands/documents/{type}/build`
   - `POST /api/commands/documents/{type}/mark-stale`
2. Update old routes to redirect with deprecation warning
3. Update frontend to use new routes
4. Monitor deprecated route usage
5. After 2 weeks with zero hits, remove old routes

**Tests**:
- `test_command_routes_return_task_id()`
- `test_commands_are_idempotent()`
- `test_old_routes_redirect()`

**Rollback**: Keep both routes active indefinitely

---

### Phase 8: Debug Routes to Dev-Only
**Goal**: Clean production routes.

**Files/Modules**:
- `app/web/routes/public/debug_routes.py`
- `app/web/routes/__init__.py`

**Steps**:
1. Add environment check:
   ```python
   if settings.DEBUG:
       router.include_router(debug_router)
   ```
2. Verify `/test-*` routes 404 in production

**Tests**:
- `test_debug_routes_404_in_production()`

**Rollback**: Remove environment check

---

### Phase 9: Data-Driven UX Implementation (Optional)
**Goal**: Remove hardcoded UX elements, enable configuration-based tuning.

**Files/Modules**:
- `app/api/models/document_type.py`
- `app/api/models/document_definition.py` (if separate)
- `app/web/templates/public/pages/partials/_document_not_found.html`
- `app/web/templates/public/components/project_list.html`
- `app/domain/services/render_model_builder.py`
- `alembic/versions/xxx_add_ux_config_columns.py` (new)

**Steps**:
1. Add `state_badges` JSONB column to `document_types`
2. Add `primary_action` field to document definition schema
3. Add `display_variant` field to section schema
4. Update `_document_not_found.html` to read CTA from data
5. Update `project_list.html` sidebar to read badges from data
6. Update `FragmentRenderer` to apply variant CSS classes
7. Seed existing hardcoded values into database
8. Remove hardcoded fallbacks

**Tests**:
- `test_cta_from_docdef()`
- `test_badge_from_document_type()`
- `test_display_variant_applies_css()`

**Rollback**: Keep hardcoded fallbacks active if data is missing

**Note**: This phase is optional but recommended for maximum UX flexibility.

---

---

## D) Governance Artifacts

### D.1 ROUTING_CONTRACT.md

```markdown
# Routing Contract v1.0

## The Hourglass Rule

All document rendering flows through RenderModelV1.
- Viewers do not depend on docdefs, schemas, or generation logic
- Builders do not depend on UI concerns
- Fragments never infer semantics

## Route Categories

### READ Routes (View-Only)
- Pattern: `GET /projects/{project_id}/documents/{doc_type_id}`
- Response: HTML (full page or HTMX partial)
- Data Flow: `documents` table -> `RenderModelBuilder` -> `RenderModelV1` -> Fragments

### COMMAND Routes (Mutating)
- Pattern: `POST /api/commands/{domain}/{action}`
- Response: JSON with `task_id`
- Properties: Async, idempotent, mutate documents not views

### Deprecated Route Handling
- MUST redirect to canonical route
- MUST emit `Warning: 299 - "Deprecated"` header
- MUST log for monitoring
- MUST NOT silently remove

## Resolution Chain

1. `doc_type_id` -> `document_types` table (DB only, never code)
2. `view_docdef_prefix` -> `document_definitions` (latest accepted)
3. `RenderModelBuilder.build()` -> `RenderModelV1`
4. Schema resolution uses `schema_bundle_sha256` from document

## Invariants

1. All view routes use RenderModelV1 exclusively
2. All command routes return JSON with task_id
3. Code never shadows DB configuration
4. Schema resolution uses persisted hash, not "latest"
```

### D.2 SCHEMA_SOURCING_RULES.md

```markdown
# Schema Sourcing Rules v1.0

## Canonical Source

**schema_artifacts** table is the ONLY source of truth for JSON schemas.

## Schema Versioning (Mandatory)

Every stored document MUST persist:
- `schema_bundle_sha256`

## Resolution Rules

1. Viewer resolves schemas by hash, not "latest"
2. Schema upgrades do NOT retroactively mutate documents
3. If the schema changed, the document did not

## Schema ID Format

```
schema:{TypeName}:{semver}
Example: schema:EpicV1:1.0.0
```

## Deprecated Sources (DO NOT USE)

| Source | Status | Action |
|--------|--------|--------|
| `role_tasks.expected_schema` | DEPRECATED | Migrate to schema_id |
| `document_types.schema_definition` | UNUSED | Remove column |
| Inline JSON in code | FORBIDDEN | Extract to registry |

## Bundle Computation (Deterministic)

```python
def compute_bundle_sha256(schema_ids: List[str]) -> str:
    schemas = sorted([get_schema(id) for id in schema_ids], key=lambda s: s["$id"])
    bundle = json.dumps(schemas, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(bundle.encode()).hexdigest()
```

## Invariants

1. Same schema_ids -> same bundle SHA256
2. Schema changes require new semver
3. No inline schemas anywhere
4. All schemas have `$id` matching schema_id
```

### D.3 VIEWER_INVARIANTS.md

```markdown
# Viewer Invariants v1.0

## Input Contract

The viewer ONLY accepts `RenderModelV1`:

```python
@dataclass
class RenderModelV1:
    render_model_version: str = "1.0"
    schema_id: str = "schema:RenderModelV1"
    schema_bundle_sha256: str
    document_id: str
    document_type: str
    title: str
    subtitle: Optional[str]
    sections: List[RenderSection]
    metadata: Dict[str, Any]
```

## Tab Contract (Frozen)

> See D.5 VIEWER_TABS_CONTRACT.md for complete specification.

**Core Principle**: Tabs are data-driven, not code-driven.

**Key Rules**:
1. Sections declare `viewer_tab` object with `id`, `label`, `order`
2. Tabs discovered dynamically from docdef sections
3. Empty tabs are suppressed (not rendered)
4. Section titles come only from docdefs
5. No predefined tab whitelist - if data defines it, viewer renders it

**Governance**: Adding/renaming/reordering tabs requires NO code changes.

## Document State Rendering

| State | Rendering |
|-------|-----------|
| `missing` | "Build" CTA only |
| `generating` | Skeleton UI with progress |
| `partial` | Available sections + "Continue" CTA |
| `complete` | Full document |
| `stale` | Full document + amber indicator |

## Fragment Contract

```jinja2
{{ block.type }}     {# schema_id #}
{{ block.key }}      {# unique key #}
{{ block.data }}     {# actual content #}
{{ block.context }}  {# parent context, may be None #}
```

## Rendering Invariants

1. Unknown block types -> placeholder with type info
2. Missing fragments -> graceful degradation + warning log
3. Null data -> skip block silently
4. Template errors -> error placeholder, never crash
```

### D.4 DOCUMENT_LIFECYCLE.md (New)

```markdown
# Document Lifecycle Contract v1.0

## States

```
missing -> generating -> partial -> complete -> stale
                ^                              |
                +-------- regenerate ----------+
```

## State Definitions

| State | Description |
|-------|-------------|
| `missing` | Document does not exist for this type/project |
| `generating` | Build in progress, skeleton available |
| `partial` | Some sections complete, others pending |
| `complete` | All sections generated and validated |
| `stale` | Upstream dependency changed, regeneration recommended |

## Allowed Transitions

| From | To | Trigger |
|------|-----|---------|
| `missing` | `generating` | `generate` command |
| `generating` | `partial` | First section completes |
| `generating` | `complete` | All sections complete |
| `partial` | `generating` | `generate section` command |
| `partial` | `complete` | All sections complete |
| `complete` | `stale` | Upstream change or `mark-stale` |
| `stale` | `generating` | `regenerate` command |

## Staleness Propagation

| When This Changes | These Become Stale |
|-------------------|-------------------|
| Project Discovery | Epic Backlog |
| Epic Backlog | Story Backlog, Architectural Summary |
| Individual Epic | Story Details for that epic |
| Architecture | Story Details |

## Invariants

1. Partial documents are valid documents
2. Stale documents remain viewable
3. State transitions are atomic
4. Staleness propagates downstream only
```

### D.5 VIEWER_TABS_CONTRACT.md (New)

```markdown
# Viewer Tabs Contract v1.0

## Purpose

Viewer tabs are a presentation-only grouping mechanism for document sections.
They do not introduce new semantics, do not affect document meaning, and do
not require architectural approval.

**Tabs are fully data-driven and defined entirely in document definitions.**

## Core Principles

1. Tabs are configuration, not architecture
2. No code or schema changes required to add, remove, or rename tabs
3. Tabs never affect generation, validation, or storage
4. Tabs only group already-rendered sections

## Section-Level Tab Declaration

A document section MAY declare a `viewer_tab` object:

```json
"viewer_tab": {
  "id": "epics",
  "label": "Epics",
  "order": 20
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Stable identifier for the tab (used internally) |
| `label` | Yes | Display label shown in the UI |
| `order` | No | Sort order of tabs (lower = earlier, default = 100) |

## Tab Discovery Rules

The Document Viewer MUST:

1. Scan all sections in the document definition
2. Collect all unique `viewer_tab.id` values
3. Sort tabs by `order` (ascending, default = 100)
4. Render tabs dynamically based on discovered configuration

**There is no registry, no whitelist, and no predefined tab set.**
If the data defines a tab, the viewer renders it.

## Default / Untabbed Sections

**Rule**: Sections without a `viewer_tab` are assigned to the default tab.

**Default Tab Resolution**:

1. If the document definition declares `default_viewer_tab`:
   ```json
   "default_viewer_tab": {
     "id": "overview",
     "label": "Overview",
     "order": 10
   }
   ```
   -> Use this tab

2. Else:
   - If at least one tab exists, use the first tab by order
   - If no tabs exist, render document with no tabs UI

## Empty Tab Suppression

If a tab contains zero sections after resolution, it MUST NOT be rendered.

This allows:
- Optional tabs
- Conditional tabs
- Progressive disclosure without UI clutter

## Rendering Semantics (Explicit Non-Goals)

Tabs DO NOT:
- Change block rendering
- Change section ordering within a tab
- Affect schema validation
- Affect PromptAssembler behavior
- Affect RenderModelBuilder semantics
- Affect derived fields
- Affect persistence

**Tabs are a pure view concern.**

## Stability Guarantees

- Section `key` values remain unchanged
- Block identity is stable regardless of tab placement
- Moving a section between tabs does not invalidate existing documents
- Adding or removing tabs is backward-compatible

## Example: Epic Backlog with "Epics" Tab

```json
{
  "document_def_id": "docdef:EpicBacklogView:1.0.0",
  "default_viewer_tab": {
    "id": "overview",
    "label": "Overview",
    "order": 10
  },
  "sections": [
    {
      "section_id": "epic_backlog_header",
      "viewer_tab": { "id": "overview", "label": "Overview", "order": 10 }
    },
    {
      "section_id": "epic_cards",
      "viewer_tab": { "id": "epics", "label": "Epics", "order": 20 }
    }
  ]
}
```

**No WS. No ADR. No code change.**

## Governance Boundary (Explicit)

| Change | Requires WS/ADR? |
|--------|------------------|
| Add a new tab | No |
| Rename a tab | No |
| Reorder tabs | No |
| Move a section between tabs | No |
| Change tab discovery mechanics | Yes |
| Introduce tab-specific behavior | Yes |

## Final Statement (Frozen)

Viewer tabs are data-defined presentation groupings. They are not architectural
constructs and do not require governance. The viewer renders whatever tabs the
document definition declares.
```

### D.6 DATA_DRIVEN_UX.md (New)

```markdown
# Data-Driven UX Contract v1.0

## Philosophy

> **Principle**: The UX should be tunable without code changes.

Every visual decision that varies by document type, section, or state should be
expressible in data (document definitions, document types, or component specs).

This enables:
- Rapid UX iteration without deploy cycles
- A/B testing via database flags
- Per-customer UX customization (future)
- Non-engineer UX tuning

## Data-Driven UX Elements

### 1. Call-to-Actions (CTAs)

**Location**: `document_definitions.primary_action`

```json
"primary_action": {
  "label": "Begin Research",
  "icon": "compass",
  "style": "primary",
  "confirmation": null
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `label` | Yes | Button text |
| `icon` | No | Lucide icon name |
| `style` | No | `primary`, `secondary`, `danger` |
| `confirmation` | No | Confirmation dialog text (if set) |

**Fallback**: If not specified, use document type name: "Generate {name}"

### 2. Display Variants

**Location**: `document_definitions.sections[].display_variant`

```json
"display_variant": "compact"
```

| Variant | Use Case |
|---------|----------|
| `default` | Standard rendering |
| `compact` | Reduced padding, smaller text |
| `expanded` | Full detail, more whitespace |
| `card` | Card-based layout |
| `table` | Tabular data |
| `minimal` | Icon + title only |

**Implementation**: FragmentRenderer reads variant and applies CSS class:
```python
css_class = f"fragment-{variant}" if variant else "fragment-default"
```

### 3. State Badges

**Location**: `document_types.state_badges`

```json
"state_badges": {
  "missing": { "icon": "circle", "color": "gray" },
  "generating": { "icon": "loader-2", "color": "blue", "animate": "spin" },
  "partial": { "icon": "circle-dot", "color": "blue" },
  "complete": { "icon": "check-circle", "color": "green" },
  "stale": { "icon": "alert-circle", "color": "amber" }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `icon` | Yes | Lucide icon name |
| `color` | Yes | Tailwind color name |
| `animate` | No | Animation class (`spin`, `pulse`) |

**Fallback**: If not specified, use system defaults.

### 4. Section Behavior

**Location**: `document_definitions.sections[]`

```json
{
  "section_id": "implementation_notes",
  "default_collapsed": true,
  "visibility_rules": {
    "show_if_empty": false,
    "min_items": 1
  }
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `default_collapsed` | `false` | Start section collapsed |
| `visibility_rules.show_if_empty` | `true` | Show section with no data |
| `visibility_rules.min_items` | `0` | Minimum items to show section |

### 5. Document Metadata Display

**Location**: `document_types.metadata_display`

```json
"metadata_display": {
  "show_version": true,
  "show_updated_at": true,
  "show_schema_version": false,
  "custom_fields": ["owner", "status"]
}
```

**Benefit**: Control which metadata appears in document headers.

## Resolution Order

1. Section-level config (most specific)
2. Document definition config
3. Document type config
4. System defaults (least specific)

## Caching Considerations

Data-driven UX values SHOULD be cached at the RenderModel level:
- Cache key: `{document_id}:{schema_bundle_sha256}`
- Invalidation: On document save or docdef change

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Change any label, icon, color | No |
| Add new display variant | No |
| Add new visibility rule | No |
| Change resolution order | Yes |
| Add new UX element category | Yes |
| Change caching strategy | Yes |

## Anti-Patterns (Avoid)

1. **Hardcoded icon names in templates** - Use data lookup
2. **CSS classes embedded in routes** - Use variant system
3. **Conditional rendering in templates based on doc_type_id** - Use visibility rules
4. **Button text in HTML** - Use primary_action config

## Migration Path

For existing hardcoded UX:
1. Identify hardcoded element
2. Add data field to appropriate location
3. Update template to read from data
4. Seed existing values
5. Remove hardcoded fallback

## Final Statement

If a UX element varies by document type, section, or state, it belongs in data.
Code should be generic; data should be specific.
```

## Purpose

UX tuning should not require code changes, architectural review, or governance.
If an element is purely presentational, it belongs in data configuration.

## Core Principle

> "Tune the UX without touching code. If it's presentation, it's data."

## Data-Driven UX Elements

### 1. Call-to-Actions (CTAs)

**Location**: `document_types.primary_action` or `document_definitions`

```json
"primary_action": {
  "label": "Begin Research",
  "icon": "compass",
  "variant": "primary",
  "tooltip": "Start the discovery process"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `label` | Yes | Button text |
| `icon` | No | Lucide icon name |
| `variant` | No | `primary`, `secondary`, `ghost` |
| `tooltip` | No | Hover text |

### 2. Status Badges

**Location**: `document_types.status_badges`

```json
"status_badges": {
  "missing": { "icon": "file-plus", "color": "gray" },
  "generating": { "icon": "loader-2", "color": "blue", "animate": "spin" },
  "partial": { "icon": "file-clock", "color": "yellow" },
  "complete": { "icon": "file-check", "color": "green" },
  "stale": { "icon": "alert-triangle", "color": "amber" }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `icon` | Yes | Lucide icon name |
| `color` | Yes | Tailwind color name |
| `animate` | No | CSS animation (`spin`, `pulse`) |

### 3. Display Variants

**Location**: `document_definitions.sections[].display_variant`

```json
"sections": [{
  "section_id": "story_list",
  "display_variant": "compact"
}]
```

| Variant | Description |
|---------|-------------|
| `default` | Standard rendering |
| `compact` | Reduced spacing, smaller text |
| `expanded` | Full details, more whitespace |
| `card` | Card-style with shadows |
| `table` | Tabular layout |

### 4. Section Visibility

**Location**: `document_definitions.sections[].visibility`

```json
"visibility": {
  "show_if_empty": false,
  "collapse_by_default": true,
  "min_items_to_show": 1
}
```

### 5. Viewer Tabs

See D.5 VIEWER_TABS_CONTRACT.md for complete specification.

## Fallback Behavior

All data-driven UX elements MUST have sensible defaults:

| Element | Default |
|---------|---------|
| CTA label | "Generate" |
| CTA icon | Document type icon |
| Badge (missing) | `file-plus` / gray |
| Badge (complete) | `file-check` / green |
| Display variant | `default` |
| Visibility | Show always |

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Change CTA label/icon/color | No |
| Change badge icon/color | No |
| Change display variant | No |
| Change visibility rules | No |
| Add new CTA variant type | Yes |
| Add new display variant | Yes |
| Add new badge animation | Yes |

## Implementation Notes

1. **Null Safety**: Always check for null config, use defaults
2. **Hot Reload**: Config changes should apply without restart
3. **Audit Trail**: Log when defaults are used (indicates missing config)
4. **Validation**: Validate icon names exist in Lucide set

## Strategic Value

Data-driven UX enables:
- A/B testing without deploys
- Per-customer theming (future)
- Rapid iteration on user feedback
- Non-developer UX tuning
- Consistent styling across document types
```
---

## E) Test Plan

### E.1 Golden Trace Renders (Mandatory)

```python
# tests/integration/test_golden_renders.py

GOLDEN_DOCDEFS = [
    "docdef:ProjectDiscovery:1.0.0",
    "docdef:EpicBacklogView:1.0.0",
    "docdef:EpicDetailView:1.0.0",
    "docdef:ArchitecturalSummaryView:1.0.0",
    "docdef:StoryBacklogView:1.0.0",
]

@pytest.mark.parametrize("docdef_id", GOLDEN_DOCDEFS)
async def test_golden_render(docdef_id, db, sample_data):
    """Verify RenderModel output matches golden snapshot."""
    builder = RenderModelBuilder(...)
    model = await builder.build(docdef_id, sample_data[docdef_id])
    
    snapshot_path = f"tests/fixtures/golden/{docdef_id}.json"
    
    # MANDATORY: Checked into Git
    assert os.path.exists(snapshot_path), "Golden snapshot missing"
    
    expected = json.load(open(snapshot_path))
    
    # Structural comparison
    assert model.document_type == expected["document_type"]
    assert len(model.sections) == len(expected["sections"])
    for actual, exp in zip(model.sections, expected["sections"]):
        assert actual.section_id == exp["section_id"]
        assert actual.viewer_tab == exp["viewer_tab"]
        assert len(actual.blocks) == len(exp["blocks"])
```

### E.2 Schema Bundle Determinism

```python
async def test_schema_bundle_determinism(db):
    """Same inputs produce same SHA256."""
    assembler = PromptAssembler(...)
    
    result1 = await assembler.assemble("docdef:EpicBacklog:1.0.0")
    result2 = await assembler.assemble("docdef:EpicBacklog:1.0.0")
    
    assert result1.bundle_sha256 == result2.bundle_sha256

async def test_document_uses_persisted_hash(db, document):
    """Viewer uses schema hash from document, not latest."""
    # Save document with specific schema version
    document.schema_bundle_sha256 = "abc123"
    await db.commit()
    
    # Update schema in registry (simulating schema evolution)
    await update_schema("schema:EpicV1:1.0.1", new_json)
    
    # Render should use persisted hash
    model = await render(document)
    assert model.schema_bundle_sha256 == "abc123"
```

### E.3 Document Lifecycle Tests

```python
async def test_document_state_transitions(db):
    """Verify allowed state transitions."""
    doc = await create_document(state="missing")
    
    # missing -> generating: allowed
    doc.state = "generating"
    await db.commit()  # succeeds
    
    # generating -> stale: NOT allowed
    with pytest.raises(InvalidStateTransition):
        doc.state = "stale"
        await db.commit()

async def test_partial_document_renders(client, partial_doc):
    """Partial documents are valid and renderable."""
    resp = await client.get(f"/projects/{partial_doc.project_id}/documents/epic_backlog")
    assert resp.status_code == 200
    assert "Continue Building" in resp.text

async def test_stale_indicator_shown(client, stale_doc):
    """Stale documents show amber indicator."""
    resp = await client.get(f"/projects/{stale_doc.project_id}/documents/epic_backlog")
    assert resp.status_code == 200
    assert "stale-indicator" in resp.text or "amber" in resp.text
```

### E.4 Staleness Propagation Tests

```python
async def test_staleness_propagates_downstream(db, project):
    """Upstream changes mark dependents stale."""
    # Create complete documents
    discovery = await create_document(project, "project_discovery", state="complete")
    epic_backlog = await create_document(project, "epic_backlog", state="complete")
    
    # Modify upstream
    discovery.content["updated"] = True
    await save_document(discovery)
    
    # Verify downstream is stale
    await db.refresh(epic_backlog)
    assert epic_backlog.state == "stale"

async def test_staleness_does_not_propagate_upstream(db, project):
    """Downstream changes do not affect upstream."""
    discovery = await create_document(project, "project_discovery", state="complete")
    epic_backlog = await create_document(project, "epic_backlog", state="complete")
    
    # Modify downstream
    epic_backlog.content["updated"] = True
    await save_document(epic_backlog)
    
    # Upstream unchanged
    await db.refresh(discovery)
    assert discovery.state == "complete"
```

### E.5 Route Deprecation Tests

```python
async def test_deprecated_route_redirects(client):
    """Old routes redirect to canonical."""
    resp = await client.get("/view/EpicBacklogView", follow_redirects=False)
    assert resp.status_code in [301, 302, 307, 308]
    assert "Warning" in resp.headers

async def test_deprecated_route_warning_header(client):
    """Deprecated routes emit Warning header."""
    resp = await client.get("/view/EpicBacklogView", follow_redirects=False)
    assert "299" in resp.headers.get("Warning", "")
    assert "Deprecated" in resp.headers.get("Warning", "")
```

### E.6 Feature Flag Tests

```python
async def test_legacy_template_feature_flag(client, monkeypatch):
    """Feature flag enables legacy templates."""
    monkeypatch.setenv("USE_LEGACY_TEMPLATES", "true")
    
    resp = await client.get("/projects/xxx/documents/epic_backlog")
    # Should use legacy template
    assert "vm.sections" in resp.text or "_epic_backlog_content" in resp.text

async def test_new_viewer_default(client):
    """New viewer is default without feature flag."""
    resp = await client.get("/projects/xxx/documents/epic_backlog")
    # Should use RenderModel viewer
    assert "render_model" in resp.text or "document-viewer" in resp.text
```

### E.7 Config Resolution Tests

```python
async def test_no_hardcoded_document_config(db):
    """Verify DOCUMENT_CONFIG dict is removed."""
    import app.web.routes.public.document_routes as dr
    assert not hasattr(dr, 'DOCUMENT_CONFIG'), "DOCUMENT_CONFIG should be removed"

async def test_config_from_db_only(db):
    """All config comes from database."""
    config = await get_document_config(db, "epic_backlog")
    
    assert config["name"] == "Epic Backlog"
    assert config["view_docdef_prefix"] == "EpicBacklogView"
    
    # Modify DB, verify change reflected
    await update_document_type(db, "epic_backlog", name="Updated Name")
    config = await get_document_config(db, "epic_backlog")
    assert config["name"] == "Updated Name"
```

---

## F) Summary

This cleanup plan implements the Document System Cleanup & Stabilization Charter:

| Charter Requirement | Phase |
|--------------------|-------|
| RenderModelV1 as hourglass waist | All phases |
| Config drift elimination | Phase 1 |
| Schema versioning with hash | Phase 2 |
| Document lifecycle states | Phase 3 |
| Staleness propagation | Phase 4 |
| Route deprecation with warnings | Phase 5 |
| Legacy template feature flag | Phase 6 |
| Command route normalization | Phase 7 |
| Debug routes to dev-only | Phase 8 |
| Data-driven UX (CTAs, badges, variants) | Phase 9 |
| Viewer tabs data-driven | D.5 (governance) |

**Strategic Outcomes**:
- React migration becomes mechanical, not risky
- User-authored documents become safe
- Concurrent generation scales cleanly
- System becomes explainable to new engineers
- The Combine transitions from clever to durable

Each phase is independently deployable with explicit rollback paths.

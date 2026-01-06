# WS-003: Fragment Registry Implementation

| | |
|---|---|
| **Status** | Complete |
| **Created** | 2026-01-06 |
| **Executor** | AI Agent (Claude) |
| **Approver** | Product Owner |
| **ADR** | ADR-032 |

---

## Purpose

Implement the Fragment Registry and Fragment Renderer per ADR-032 (Fragment-Based Rendering).

This Work Statement covers:
- Phase 1: Fragment Registry (DB layer)
- Phase 2: Fragment Renderer
- Phase 3: Proof of Concept (OpenQuestionV1 in Epic Backlog)

---

## Governing References

| Reference | Purpose |
|-----------|---------|
| ADR-032 | Defines fragment rendering requirements and acceptance criteria |
| ADR-031 | Schema registry (dependency) |
| ADR-030 | BFF pattern (fragments operate within BFF) |
| POL-WS-001 | Governs Work Statement structure and execution |
| POL-ADR-EXEC-001 | Governs ADR execution authorization |

---

## Scope

### Included

- Create `fragment_artifacts` and `fragment_bindings` tables
- Create ORM models for both tables
- Create `FragmentRegistryService` with CRUD and binding lookup
- Create `FragmentRenderer` service
- Seed `OpenQuestionV1` fragment (HTML partial)
- Integrate fragment rendering into Epic Backlog BFF for `open_questions`
- Tests for all new components (~25 tests)

### Excluded

- Full migration of existing templates to fragments
- Display metadata (`x-combine-view`) processing
- Fragment authoring UI
- Additional canonical type fragments beyond OpenQuestionV1

---

## Preconditions

- [x] ADR-032 accepted
- [x] ADR-031 complete (schema registry exists)
- [x] Implementation Plan accepted
- [ ] All existing tests pass (1034)

---

## Procedure

Execute steps in order. Do not skip, reorder, or merge steps.

---

### PHASE 1: Fragment Registry (DB Layer)

---

### Step 1: Create Database Migration

**Action:** Create `alembic/versions/20260106_003_add_fragment_tables.py`

**Table: fragment_artifacts**
- `id` (UUID, PK)
- `fragment_id` (VARCHAR(100), NOT NULL) — e.g., "OpenQuestionV1Fragment"
- `version` (VARCHAR(20), NOT NULL, default '1.0')
- `schema_type_id` (VARCHAR(100), NOT NULL) — canonical type this renders
- `status` (VARCHAR(20), NOT NULL) — 'draft', 'accepted', 'deprecated'
- `fragment_markup` (TEXT, NOT NULL) — HTML/Jinja2 template content
- `sha256` (VARCHAR(64), NOT NULL)
- `created_at` (TIMESTAMP, NOT NULL)
- `created_by` (VARCHAR(100))
- `updated_at` (TIMESTAMP)

**Indexes:**
- UNIQUE on (fragment_id, version)
- Index on (schema_type_id)
- Index on (status)

**Table: fragment_bindings**
- `id` (UUID, PK)
- `schema_type_id` (VARCHAR(100), NOT NULL) — e.g., "OpenQuestionV1"
- `fragment_id` (VARCHAR(100), NOT NULL)
- `fragment_version` (VARCHAR(20), NOT NULL)
- `is_active` (BOOLEAN, NOT NULL, default false)
- `created_at` (TIMESTAMP, NOT NULL)
- `created_by` (VARCHAR(100))

**Indexes:**
- UNIQUE on (schema_type_id, is_active) WHERE is_active = true
- Index on (fragment_id)

**Verification:** Migration applies without error.

---

### Step 2: Create ORM Models

**Action:** Create `app/api/models/fragment_artifact.py`

```python
class FragmentArtifact(Base):
    __tablename__ = "fragment_artifacts"
    # ... columns matching migration

class FragmentBinding(Base):
    __tablename__ = "fragment_bindings"
    # ... columns matching migration
```

**Action:** Update `app/api/models/__init__.py` to export both models.

**Verification:** Models import successfully.

---

### Step 3: Create Fragment Registry Service

**Action:** Create `app/api/services/fragment_registry_service.py`

**Methods:**
- `async create_fragment(fragment_id, schema_type_id, fragment_markup, ...) -> FragmentArtifact`
- `async get_fragment(fragment_id, version=None) -> FragmentArtifact | None`
- `async get_active_fragment_for_type(schema_type_id) -> FragmentArtifact | None`
- `async set_status(fragment_id, version, status) -> FragmentArtifact`
- `async create_binding(schema_type_id, fragment_id, fragment_version) -> FragmentBinding`
- `async activate_binding(schema_type_id, fragment_id, fragment_version) -> FragmentBinding`
- `compute_hash(markup) -> str`

**Rules:**
- `activate_binding` deactivates any existing active binding for that type
- Only one active binding per schema_type_id
- Hash computed on create

**Verification:** Service instantiates, methods callable.

---

### Step 4: Seed OpenQuestionV1 Fragment

**Action:** Create `app/domain/registry/seed_fragment_artifacts.py`

**OpenQuestionV1 Fragment markup:**
```html
<div class="open-question" data-blocking="{{ item.blocking | lower }}">
  <div class="question-text">{{ item.text }}</div>
  {% if item.why_it_matters %}
  <div class="question-why">{{ item.why_it_matters }}</div>
  {% endif %}
  {% if item.blocking %}
  <span class="blocking-badge">Blocking</span>
  {% endif %}
</div>
```

**Seed function:**
- Creates fragment with status="accepted"
- Creates binding with is_active=true

**Verification:** Seed runs, fragment and binding exist.

---

### Step 5: Create Phase 1 Tests

**Action:** Create `tests/api/test_fragment_registry_service.py`

**Required tests:**
1. `test_create_fragment_artifact`
2. `test_create_computes_hash`
3. `test_get_fragment_by_id`
4. `test_get_active_fragment_for_type`
5. `test_set_status`
6. `test_create_binding`
7. `test_activate_binding_deactivates_previous`
8. `test_only_one_active_binding_per_type`

**Verification:** All Phase 1 tests pass.

---

### PHASE 2: Fragment Renderer

---

### Step 6: Create Fragment Renderer Service

**Action:** Create `app/web/bff/fragment_renderer.py`

**Class: FragmentRenderer**

```python
class FragmentRenderer:
    def __init__(self, registry: FragmentRegistryService, jinja_env: Environment):
        ...
    
    async def render(self, schema_type_id: str, data: dict) -> str:
        """Render a single item using the bound fragment."""
        ...
    
    async def render_list(self, schema_type_id: str, items: List[dict]) -> str:
        """Render a list of items, each using the bound fragment."""
        ...
```

**Algorithm:**
1. Look up active binding for schema_type_id
2. Get fragment markup from registry
3. Compile template (cache for performance)
4. Render with data
5. Return HTML string

**Verification:** Renderer instantiates.

---

### Step 7: Create Phase 2 Tests

**Action:** Create `tests/web/test_fragment_renderer.py`

**Required tests:**
1. `test_render_single_item`
2. `test_render_list`
3. `test_render_missing_binding_raises`
4. `test_render_caches_compiled_template`
5. `test_render_with_conditional_content`

**Verification:** All Phase 2 tests pass.

---

### PHASE 3: Proof of Concept

---

### Step 8: Update Epic Backlog BFF

**Action:** Modify `app/web/bff/epic_backlog_bff.py`

**Changes:**
1. Add optional `fragment_renderer` parameter
2. If fragment_renderer provided AND open_questions present:
   - Render open_questions using `fragment_renderer.render_list("OpenQuestionV1", questions)`
   - Add `rendered_open_questions` to ViewModel
3. If not provided, existing behavior unchanged

**Verification:** BFF accepts renderer, produces rendered HTML when available.

---

### Step 9: Update Epic Backlog Template

**Action:** Modify `app/web/templates/public/pages/partials/_epic_backlog_content.html`

**Changes:**
- Check if `vm.rendered_open_questions` exists
- If yes, output raw HTML: `{{ vm.rendered_open_questions | safe }}`
- If no, use existing template logic (backward compatible)

**Verification:** Template handles both cases.

---

### Step 10: Integration Test

**Action:** Create `tests/web/test_epic_backlog_fragment_integration.py`

**Required tests:**
1. `test_epic_backlog_with_fragment_renderer`
2. `test_epic_backlog_without_fragment_renderer_unchanged`
3. `test_rendered_open_questions_contains_expected_html`

**Verification:** All integration tests pass.

---

### Step 11: Run Full Test Suite

**Action:** Execute `python -m pytest tests/ -v`

**Verification:** All tests pass (1034 existing + ~25 new).

---

## Prohibited Actions

1. **Do not modify existing fragment rendering** until Phase 3 Step 9
2. **Do not create additional fragments** — Only OpenQuestionV1 in this WS
3. **Do not implement x-combine-view processing** — Out of scope
4. **Do not break existing Epic Backlog rendering** — Must be backward compatible
5. **Do not store fragments on filesystem** — DB-governed per ADR-032
6. **Do not infer missing steps** — If unclear, STOP and escalate

---

## Verification Checklist

- [ ] `fragment_artifacts` table exists with all columns and indexes
- [ ] `fragment_bindings` table exists with unique active constraint
- [ ] ORM models work
- [ ] FragmentRegistryService CRUD operations work
- [ ] Only one active binding per schema_type_id enforced
- [ ] SHA256 computed for fragment markup
- [ ] OpenQuestionV1 fragment seeded and accepted
- [ ] OpenQuestionV1 binding active
- [ ] FragmentRenderer resolves type → fragment → HTML
- [ ] FragmentRenderer caches compiled templates
- [ ] Epic Backlog BFF accepts optional fragment_renderer
- [ ] Epic Backlog template handles rendered_open_questions
- [ ] Existing Epic Backlog rendering unchanged when renderer not provided
- [ ] All new tests pass (~25)
- [ ] All existing tests pass (1034)

---

## Definition of Done

This Work Statement is complete when:

1. All procedure steps (1-11) have been executed in order
2. All verification checklist items are checked
3. No prohibited actions were taken
4. ADR-032 acceptance criteria 1 and 2 are met
5. ~25 new tests passing, 1034 existing tests still passing

---

## Closure

| Field | Value |
|-------|-------|
| Completed | 2026-01-06 |
| Verified By | Product Owner |
| Deviations | Per-epic rendering (not aggregated backlog-level) |
| Notes | 32 new tests, 1064 total passing. Fragment badge visible in UI. |

---

*End of Work Statement*
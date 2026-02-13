# WS-004: Remove HTML from BFF Contracts (ADR-033 Compliance)

| | |
|---|---|
| **Work Statement** | WS-004 |
| **Title** | Remove HTML from BFF Contracts |
| **ADR** | ADR-033 |
| **Status** | Complete |
| **Expected Scope** | Single-commit |
| **Created** | 2026-01-06 |

---

## Objective

Refactor Epic Backlog BFF to comply with ADR-033: remove `rendered_open_questions` (HTML) from ViewModels, move FragmentRenderer invocation from BFF to template layer.

---

## Scope

### In Scope

1. Remove `rendered_open_questions` field from `EpicCardVM`
2. Remove `rendered_open_questions` field from `EpicBacklogVM`
3. Remove `fragment_renderer` parameter from `get_epic_backlog_vm()`
4. Remove FragmentRenderer wiring from `document_routes.py`
5. Create Jinja2 global/filter `render_fragment(type_id, data)` in template layer
6. Update `_epic_card.html` to iterate `open_questions` and call `render_fragment()`
7. Update tests to reflect new contract shape

### Out of Scope

- Full Render Model implementation (future work)
- Other document types
- Non-web renderers

---

## Preconditions

- [x] ADR-033 accepted
- [x] FragmentRenderer and FragmentRegistryService exist (ADR-032)
- [x] OpenQuestionV1Fragment seeded and active

---

## Procedure

### Step 1: Create Jinja2 Fragment Filter

Create `app/web/template_helpers.py`:

```python
"""
Template helpers for Jinja2 rendering.

ADR-033: Fragment rendering is a web channel concern, not BFF.
"""

from jinja2 import Environment
from app.api.services.fragment_registry_service import FragmentRegistryService
from app.web.bff.fragment_renderer import FragmentRenderer

async def render_fragment(type_id: str, data: dict, renderer: FragmentRenderer) -> str:
    """Render a single canonical type block using the fragment registry."""
    try:
        return await renderer.render(type_id, data)
    except Exception:
        return ""  # Graceful degradation
```

### Step 2: Register Fragment Filter in App Startup

Update `app/web/routes/__init__.py` or template configuration to:
- Create FragmentRenderer instance with DB session
- Register `render_fragment` as Jinja2 global or filter

### Step 3: Remove HTML from ViewModels

**app/web/viewmodels/epic_backlog_vm.py:**
- Remove `rendered_open_questions: Optional[str] = None` from `EpicCardVM`
- Remove `rendered_open_questions: Optional[str] = None` from `EpicBacklogVM`

### Step 4: Remove FragmentRenderer from BFF

**app/web/bff/epic_backlog_bff.py:**
- Remove `fragment_renderer` parameter from `get_epic_backlog_vm()`
- Remove all fragment rendering logic from the function
- Keep `open_questions` as data-only list

### Step 5: Remove FragmentRenderer Wiring from Route

**app/web/routes/public/document_routes.py:**
- Remove `FragmentRenderer` import
- Remove `FragmentRegistryService` import  
- Remove `fragment_registry` and `fragment_renderer` instantiation
- Remove `fragment_renderer=fragment_renderer` from BFF call

### Step 6: Update Template to Render Fragments

**app/web/templates/public/pages/partials/_epic_card.html:**

Replace fragment-aware section with:

```jinja2
<!-- Open Questions -->
{% if epic.open_questions %}
<div class="border-l-4 border-amber-600 ...">
    <div class="flex items-center gap-2 mb-2">
        <h4 class="...">Open Questions</h4>
        <span class="px-1.5 py-0.5 bg-blue-100 ... text-xs">Fragment</span>
    </div>
    <div class="space-y-2">
        {% for q in epic.open_questions %}
        {{ render_fragment('OpenQuestionV1', {
            'id': q.id or '',
            'text': q.question,
            'blocking': q.blocking,
            'why_it_matters': q.why_it_matters or '',
            'options': q.options or [],
            'notes': q.notes or ''
        }) | safe }}
        {% endfor %}
    </div>
</div>
{% endif %}
```

### Step 7: Update Tests

**tests/web/test_epic_backlog_fragment_integration.py:**
- Remove tests checking `vm.rendered_open_questions`
- Update tests to verify `epic.open_questions` is data-only
- Add tests for template-level fragment rendering (if feasible)

---

## Verification

- [ ] `EpicCardVM` has no `rendered_open_questions` field
- [ ] `EpicBacklogVM` has no `rendered_open_questions` field
- [ ] `get_epic_backlog_vm()` has no `fragment_renderer` parameter
- [ ] `document_routes.py` has no FragmentRenderer imports/usage
- [ ] Epic Backlog UI still shows "Fragment" badge
- [ ] Open questions render correctly via template-invoked FragmentRenderer
- [ ] All tests pass

---

## Rollback

Revert commit. No database changes.

---

## Closure

| Field | Value |
|-------|-------|
| Completed | 2026-01-06 |
| Verified By | Product Owner |
| Deviations | Used PreloadedFragmentRenderer (async preload) instead of SyncFragmentRenderer |
| Notes | 1071 tests passing. Fragment badge + full question details render in UI. |
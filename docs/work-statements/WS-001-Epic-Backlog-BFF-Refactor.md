# WS-001: Epic Backlog BFF Refactor

| | |
|---|---|
| **Status** | Complete |
| **Created** | 2026-01-06 |
| **Executor** | AI Agent (Claude) |
| **Approver** | Product Owner |

---

## Purpose

Refactor the Epic Backlog view to comply with ADR-030 (BFF Layer and ViewModel Boundary).

This Work Statement:
- Introduces the BFF layer pattern to The Combine
- Proves the ViewModel boundary on a representative UX surface
- Establishes the mandatory mechanism for applying ADR-030 to future UX surfaces

> **Note:** This Work Statement is a **full-surface exemplar** — it fully refactors the Epic Backlog view rather than proving the pattern minimally. This level of rigor is appropriate for the first application of ADR-030 but is not the required minimum for future Work Statements.

---

## Governing References

| Reference | Purpose |
|-----------|---------|
| ADR-030 | Defines BFF layer and ViewModel boundary requirements |
| POL-WS-001 | Governs Work Statement structure and execution |
| ADR-030 Implementation Plan | Provides phase structure and file inventory |

---

## Scope

### Included

- Create `app/web/viewmodels/` directory and Epic Backlog ViewModels
- Create `app/web/bff/` directory and Epic Backlog BFF function
- Modify `app/web/routes/public/document_routes.py` to call BFF for `epic_backlog`
- Modify `_epic_backlog_content.html` to consume `vm.*` only
- Modify `_epic_card.html` to consume `epic.*` from ViewModel
- Create unit tests for BFF function
- Preserve all existing UI functionality (no regression)

### Excluded

- Other document types (project_discovery, technical_architecture, story_backlog)
- ActionVM or workflow-driven actions
- Separate deployables
- JSON-defined UI schemas
- Database schema changes

---

## Preconditions

Before execution:

- [ ] ADR-030 is committed and accepted
- [ ] POL-WS-001 is committed and active
- [ ] ADR-030 Implementation Plan is committed
- [ ] Current Epic Backlog view renders correctly (baseline verified)
- [ ] All existing tests pass

---

## Procedure

Execute steps in order. Do not skip, reorder, or merge steps.

### Step 1: Create ViewModel Directory and __init__.py

**Action:** Create `app/web/viewmodels/__init__.py`

**Content:**
`python
from .epic_backlog_vm import (
    EpicBacklogVM,
    EpicBacklogSectionVM,
    EpicCardVM,
    EpicSetSummaryVM,
    RiskVM,
    OpenQuestionVM,
    DependencyVM,
    RelatedDiscoveryVM,
)

__all__ = [
    "EpicBacklogVM",
    "EpicBacklogSectionVM",
    "EpicCardVM",
    "EpicSetSummaryVM",
    "RiskVM",
    "OpenQuestionVM",
    "DependencyVM",
    "RelatedDiscoveryVM",
]
`

**Verification:** File exists and is syntactically valid.

---

### Step 2: Create Epic Backlog ViewModels

**Action:** Create `app/web/viewmodels/epic_backlog_vm.py`

**Requirements:**
- Use Pydantic `BaseModel` for all ViewModels
- Include all fields currently used by `_epic_card.html`
- Include `exists: bool` and `message: Optional[str]` on `EpicBacklogVM` for empty/error states
- All fields must have defaults (no required fields that could fail on missing data)

**ViewModels to define:**
1. `OpenQuestionVM` - question, blocking, directed_to
2. `DependencyVM` - depends_on_epic_id, reason
3. `RelatedDiscoveryVM` - risks, unknowns, early_decision_points
4. `EpicCardVM` - all epic card fields including nested VMs
5. `EpicBacklogSectionVM` - id, title, icon, description, empty_message, epics
6. `EpicSetSummaryVM` - overall_intent, mvp_definition, key_constraints, out_of_scope
7. `RiskVM` - description, impact, affected_epics
8. `EpicBacklogVM` - project_id, project_name, document_id, title, subtitle, last_updated_label, epic_set_summary, sections, risks_overview, recommendations_for_architecture, exists, message

**Verification:** File exists, imports successfully, all ViewModels can be instantiated with defaults.

---

### Step 3: Create BFF Directory and __init__.py

**Action:** Create `app/web/bff/__init__.py`

**Content:**
`python
from .epic_backlog_bff import get_epic_backlog_vm

__all__ = ["get_epic_backlog_vm"]
`

**Verification:** File exists and is syntactically valid.

---

### Step 4: Create Epic Backlog BFF Function

**Action:** Create `app/web/bff/epic_backlog_bff.py`

**Requirements:**
- Define `async def get_epic_backlog_vm(*, db, project_id, project_name, base_url) -> EpicBacklogVM`
- Fetch document using existing `_get_document_by_type` helper (import from document_routes)
- Return `EpicBacklogVM(exists=False, message="...")` if document not found
- Classify epics into MVP/Later sections based on `mvp_phase` field
- Map all raw JSON fields to ViewModel fields
- Handle missing/null fields gracefully (use defaults)

**Helper functions to define:**
- `_map_epic_to_card_vm(epic: dict, project_id: UUID, base_url: str) -> EpicCardVM`
- `_empty_sections() -> List[EpicBacklogSectionVM]`
- `_format_dt(dt: Optional[datetime]) -> Optional[str]`

**Verification:** File exists, imports successfully, function can be called with mock data.

---

### Step 5: Update Document Route for Epic Backlog

**Action:** Modify `app/web/routes/public/document_routes.py`

**Changes:**
1. Add import: `from app.web.bff import get_epic_backlog_vm`
2. In `get_document()` function, before the generic document handling, add special case for `epic_backlog`:

`python
if doc_type_id == "epic_backlog":
    vm = await get_epic_backlog_vm(
        db=db,
        project_id=proj_uuid,
        project_name=project["name"],
        base_url="",
    )
    context = {
        "request": request,
        "project": project,
        "vm": vm,
    }
    partial_template = "public/pages/partials/_epic_backlog_content.html"
    
    if is_htmx:
        return templates.TemplateResponse(partial_template, context)
    else:
        context["content_template"] = partial_template
        return templates.TemplateResponse("public/pages/document_page.html", context)
`

**Verification:** Route handles `epic_backlog` requests without error.

---

### Step 6: Update Epic Backlog Content Template

**Action:** Modify `app/web/templates/public/pages/partials/_epic_backlog_content.html`

**Requirements:**
- Remove all references to `document`, `content`, `artifact`
- Access data via `vm.*` only
- Replace Jinja filters (`selectattr`) with iteration over `vm.sections`
- Use `vm.exists` for empty/not-found state
- Preserve all existing visual structure and styling

**Key replacements:**
- `content.epics | selectattr(...) | list` -> `vm.sections[n].epics`
- `content.epic_set_summary` -> `vm.epic_set_summary`
- `content.risks_overview` -> `vm.risks_overview`
- `content.recommendations_for_architecture` -> `vm.recommendations_for_architecture`
- `document.updated_at` -> `vm.last_updated_label`

**Verification:** Template renders without Jinja errors.

---

### Step 7: Update Epic Card Template

**Action:** Modify `app/web/templates/public/pages/partials/_epic_card.html`

**Requirements:**
- Verify all field accesses match ViewModel field names
- Update nested object access if field names differ
- `epic.open_questions[].blocking_for_epic` -> `epic.open_questions[].blocking`

**Verification:** Template renders without Jinja errors.

---

### Step 8: Create BFF Unit Tests

**Action:** Create `tests/web/test_epic_backlog_bff.py`

**Test cases required:**
1. `test_get_epic_backlog_vm_with_document` - happy path with content
2. `test_get_epic_backlog_vm_no_document` - returns exists=False
3. `test_epic_classification_mvp` - epics with mvp_phase="mvp" go to MVP section
4. `test_epic_classification_later` - epics with mvp_phase="later-phase" go to Later section
5. `test_open_questions_mapping` - blocking flag maps correctly
6. `test_dependencies_mapping` - dependency fields map correctly
7. `test_missing_fields_handled` - missing JSON fields don't cause errors

**Test approach:** Mock the `_get_document_by_type` call, verify ViewModel structure.

**Verification:** All tests pass.

---

### Step 9: Integration Verification

**Action:** Manually verify the Epic Backlog view in the running application.

**Checks:**
- [ ] Navigate to Epic Backlog via sidebar (HTMX partial load)
- [ ] Refresh the Epic Backlog page (full page load)
- [ ] MVP section displays correctly
- [ ] Later Phase section displays correctly
- [ ] Epic cards expand/collapse
- [ ] All card sections render (Business Value, In Scope, etc.)
- [ ] Open Questions show blocking indicators
- [ ] Dependencies display
- [ ] Epic Set Summary displays
- [ ] Risks Overview displays
- [ ] Raw JSON collapsible works

**Verification:** All checks pass with no visual regression.

---

### Step 10: Run Full Test Suite

**Action:** Execute `python -m pytest tests/ -v`

**Verification:** All tests pass (no regressions).

---

## Prohibited Actions

The following actions are explicitly prohibited during execution of this Work Statement:

1. **Do not modify other document type routes or templates** - Only `epic_backlog` is in scope
2. **Do not add ActionVM or workflow-driven actions** - Out of scope for this Work Statement
3. **Do not change database schema** - No migrations in this Work Statement
4. **Do not modify domain services** - BFF calls existing services, does not change them
5. **Do not remove the generic document handling** - Epic Backlog is a special case, not a replacement
6. **Do not access ORM models or document.content in templates** - ViewModel boundary must be enforced
7. **Do not skip the empty/error state handling** - `exists=False` path must be implemented
8. **Do not infer missing steps** - If unclear, STOP and escalate
9. **Do not replicate the `_get_document_by_type` import pattern** - This WS permits importing `_get_document_by_type` from `document_routes` as a transitional measure. Future WSs must source document retrieval from domain/core services. This dependency should be refactored in a subsequent WS.

---

## Verification Checklist

Before closing this Work Statement, verify:

- [ ] `app/web/viewmodels/__init__.py` exists and exports all ViewModels
- [ ] `app/web/viewmodels/epic_backlog_vm.py` exists with all required ViewModels
- [ ] `app/web/bff/__init__.py` exists and exports `get_epic_backlog_vm`
- [ ] `app/web/bff/epic_backlog_bff.py` exists with BFF function and helpers
- [ ] `document_routes.py` special-cases `epic_backlog` to use BFF
- [ ] `_epic_backlog_content.html` accesses `vm.*` only (no `document`, `content`)
- [ ] `_epic_card.html` accesses ViewModel fields only
- [ ] `tests/web/test_epic_backlog_bff.py` exists with required test cases
- [ ] All new tests pass
- [ ] All existing tests pass (no regression)
- [ ] HTMX partial load works
- [ ] Full page refresh works
- [ ] All Epic Backlog UI features render correctly

---

## Definition of Done

This Work Statement is complete when:

1. All procedure steps (1-10) have been executed in order
2. All verification checklist items are checked
3. No prohibited actions were taken
4. The Epic Backlog view functions identically to before (no regression)
5. Templates access only `vm.*` (ADR-030 compliance verified)

---

## Closure

| Field | Value |
|-------|-------|
| Completed | 2026-01-06 |
| Verified By | Product Owner |
| Deviations | None |
| Notes | 21 BFF tests, 999 total tests passing. UI verified via screenshots. |

---

*End of Work Statement*
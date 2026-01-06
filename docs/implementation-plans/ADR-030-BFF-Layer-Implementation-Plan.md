# ADR-030 Implementation Plan: BFF Layer and ViewModel Boundary

**Created:** 2026-01-06  
**ADR Version:** 1.0  
**Status:** Ready for Work Statement

---

## Summary

Introduce a Backend-for-Frontend (BFF) layer with explicit ViewModel boundary for the Epic Backlog view as proof of the ADR-030 pattern.

**Goal:** Templates consume ViewModels only; no access to ORM models or raw `document.content`.

---

## Reuse Analysis

Per the Reuse-First Rule:

| Option | Artifact | Decision | Rationale |
|--------|----------|----------|-----------|
| Create | `app/web/viewmodels/` | **Required** | New layer, nothing to reuse |
| Create | `app/web/bff/` | **Required** | New layer, nothing to reuse |
| Modify | `app/web/routes/public/document_routes.py` | **Modify** | Route exists, needs to call BFF |
| Modify | `_epic_backlog_content.html` | **Modify** | Template exists, needs vm.* access |
| Modify | `_epic_card.html` | **Modify** | Template exists, needs vm.* access |

---

## Design Decision: ViewModel Completeness

Current `_epic_card.html` uses these fields from raw JSON:

| Field | Required in VM |
|-------|----------------|
| `epic_id` | Yes |
| `name` / `title` | Yes |
| `intent` / `summary` | Yes |
| `business_value` | Yes |
| `in_scope` (list) | Yes |
| `out_of_scope` (list) | Yes |
| `primary_outcomes` (list) | Yes |
| `open_questions` (list with blocking flag) | Yes |
| `dependencies` (list) | Yes |
| `architecture_attention_points` (list) | Yes |
| `related_discovery_items` (nested) | Yes |

**Decision:** Full ViewModel - all fields required to maintain current UI functionality.

---

## Phase 1: Create ViewModel Layer

**New Directory:** `app/web/viewmodels/`

**New Files:**

### `app/web/viewmodels/__init__.py`

Exports: EpicBacklogVM, EpicBacklogSectionVM, EpicCardVM, OpenQuestionVM, DependencyVM, RelatedDiscoveryVM

### `app/web/viewmodels/epic_backlog_vm.py`

Pydantic models for:
- `OpenQuestionVM` - epic open question
- `DependencyVM` - epic dependency
- `RelatedDiscoveryVM` - related discovery items
- `EpicCardVM` - single epic card with all display fields
- `EpicBacklogSectionVM` - section of epics (MVP, Later)
- `EpicSetSummaryVM` - epic set summary
- `RiskVM` - risk overview item
- `EpicBacklogVM` - top-level view model

Key properties:
- All fields from current template usage included
- `exists: bool` and `message: str` for empty/error states
- Computed properties for counts

---

## Phase 2: Create BFF Layer

**New Directory:** `app/web/bff/`

**New Files:**

### `app/web/bff/__init__.py`

Exports: get_epic_backlog_vm

### `app/web/bff/epic_backlog_bff.py`

**Main function:** `async def get_epic_backlog_vm(db, project_id, project_name, base_url) -> EpicBacklogVM`

**Responsibilities:**
1. Fetch document via existing helper
2. Handle not-found case with `exists=False`
3. Classify epics into MVP/Later sections
4. Map raw JSON to ViewModels
5. Return presentation-safe ViewModel

**Helper functions:**
- `_map_epic_to_card_vm()` - map single epic
- `_empty_sections()` - return empty structure
- `_format_dt()` - format datetime for display

---

## Phase 3: Update Route

**File:** `app/web/routes/public/document_routes.py`

**Changes:**
1. Import `get_epic_backlog_vm` from BFF
2. Special-case `epic_backlog` doc_type
3. Call BFF function
4. Pass `vm` to template context (not `document`/`content`)

---

## Phase 4: Update Templates

### `_epic_backlog_content.html`

**Key changes:**
- Replace `content.epics` with `vm.sections`
- Replace Jinja filters (`selectattr`) with pre-classified sections
- Use `vm.exists` for empty state
- Access `vm.epic_set_summary`, `vm.risks_overview`, etc.

### `_epic_card.html`

**Key changes:**
- Field names preserved in VM, minimal changes needed
- Access `epic.open_questions` as list of `OpenQuestionVM`
- Access `epic.dependencies` as list of `DependencyVM`
- Access `epic.related_discovery_items` as `RelatedDiscoveryVM`

---

## Phase 5: Tests

**New File:** `tests/web/test_epic_backlog_bff.py`

| Category | Tests |
|----------|-------|
| **Happy Path** | `test_get_epic_backlog_vm_with_content` |
| **Empty State** | `test_get_epic_backlog_vm_no_document` |
| **Classification** | `test_epic_classification_mvp`, `test_epic_classification_later` |
| **Mapping** | `test_open_questions_mapping`, `test_dependencies_mapping` |
| **Edge Cases** | `test_empty_epics_list`, `test_missing_fields` |

---

## Implementation Order

| Step | Files | Est. Time | Depends On |
|------|-------|-----------|------------|
| 1 | `app/web/viewmodels/__init__.py`, `epic_backlog_vm.py` | 30 min | - |
| 2 | `app/web/bff/__init__.py`, `epic_backlog_bff.py` | 45 min | Step 1 |
| 3 | `app/web/routes/public/document_routes.py` | 30 min | Step 2 |
| 4 | `_epic_backlog_content.html`, `_epic_card.html` | 45 min | Step 3 |
| 5 | `tests/web/test_epic_backlog_bff.py` | 30 min | Steps 1-2 |
| 6 | Integration test, fix issues | 30 min | All |

**Total Estimated Time:** ~3.5 hours

---

## Files to Create/Modify

| Action | File |
|--------|------|
| Create | `app/web/viewmodels/__init__.py` |
| Create | `app/web/viewmodels/epic_backlog_vm.py` |
| Create | `app/web/bff/__init__.py` |
| Create | `app/web/bff/epic_backlog_bff.py` |
| Modify | `app/web/routes/public/document_routes.py` |
| Modify | `app/web/templates/public/pages/partials/_epic_backlog_content.html` |
| Modify | `app/web/templates/public/pages/partials/_epic_card.html` |
| Create | `tests/web/test_epic_backlog_bff.py` |

---

## Verification Checklist

- [ ] Templates only access `vm.*`
- [ ] No `document`, `content`, or ORM fields in templates
- [ ] Route does not instantiate domain services directly
- [ ] Empty/not-found state renders correctly
- [ ] MVP/Later classification works
- [ ] All epic card fields display correctly
- [ ] HTMX partial swap works
- [ ] Full page refresh works
- [ ] Tests pass

---

## Definition of Done

- [ ] All phases complete
- [ ] All verification checks pass
- [ ] Existing UI functionality preserved (no regression)
- [ ] Work Statement completed and closed

---

_Last updated: 2026-01-06_
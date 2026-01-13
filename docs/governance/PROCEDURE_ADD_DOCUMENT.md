# Procedure: Add Document

**Status:** Frozen  
**Effective:** 2026-01-09  
**WS:** WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS

## Purpose

Step-by-step procedure for adding a new document definition (docdef) to The Combine.

## Prerequisites

- Document is a **view** over existing canonical schema(s), not "the record"
- All required components already exist (no new components in this procedure)
- Clear purpose: Detail view, Summary view, or Backlog view

---

## Step 1: Identify Canonical Record

**Question:** What canonical data does this document project?

| Document Type | Source Data | Example |
|---------------|-------------|---------|
| Detail View | Single record | `EpicV1` → `EpicDetailView` |
| Summary View | Single record (lossy) | `EpicV1` → `EpicSummaryView` |
| Backlog View | Collection | `EpicV1[]` → `EpicBacklogView` |

**Rule:** Documents project data. They do not define canonical schema.

---

## Step 2: Create DocDef

**File:** `app/domain/registry/seed_component_artifacts.py`

```python
XXX_VIEW_DOCDEF = {
    "document_def_id": "docdef:XxxView:1.0.0",
    "document_schema_id": None,  # Optional, nullable for MVP
    "prompt_header": {
        "role": "You are producing a Xxx View document.",
        "constraints": [
            "Constraint 1.",
            "Constraint 2.",
        ]
    },
    "sections": [
        {
            "section_id": "section_name",
            "title": "Section Title",
            "order": 10,
            "component_id": "component:XxxBlockV1:1.0.0",
            "shape": "single",  # or "container"
            "source_pointer": "/field_name",
            "context": {"title": "Section Title"},
        },
    ],
    "status": "accepted"
}
```

Add to `INITIAL_DOCUMENT_DEFINITIONS` list.

---

## Step 3: Choose Shape Semantics

| Shape | Use When | Blocks Produced |
|-------|----------|-----------------|
| `single` | One block from one source | 1 |
| `container` | List of items | 1 (with items[]) |
| `container` + `repeat_over` | Grouped lists | N (one per group) |

**Frozen rules (see RENDER_SHAPES_SEMANTICS.md):**
- `single`: exactly 1 block, omit if source empty
- `container`: exactly 1 block with `data.items[]`, omit if empty
- `container` + `repeat_over`: N blocks, one per iteration

---

## Step 4: Summary View Requirements

If creating a **Summary View**, additional rules apply:

**Per SUMMARY_VIEW_CONTRACT.md:**
- [ ] Must include `exclude_fields` to strip heavy data
- [ ] Must NOT carry typed arrays (risks, dependencies, stories, questions)
- [ ] Must include `detail_ref` (DocumentRefV1)
- [ ] Field limit: 3-5 fields maximum
- [ ] Must use `detail_ref_template` in section config

**Example:**
```python
{
    "section_id": "summary",
    "component_id": "component:EpicSummaryBlockV1:1.0.0",
    "shape": "single",
    "source_pointer": "/",
    "exclude_fields": ["stories", "risks", "dependencies", "open_questions"],
    "detail_ref_template": {
        "document_type": "EpicDetailView",
        "params": {"epic_id": "/id"}
    },
}
```

---

## Step 5: Prompt Assembly Check

**Verify:**
- DocDef only includes components whose `generation_guidance` should be in prompt
- Summary views use summary components (not detail components)
- No duplicate component references unless intentional

**Test:**
```bash
curl http://localhost:8000/api/admin/composer/preview/prompt/docdef:XxxView:1.0.0
```

Review `component_bullets` — should contain only relevant guidance.

---

## Step 6: Render Check

**Verify:**
- Data-only payload (no HTML in response)
- Correct block counts per shape semantics
- Block types match expected schemas
- Context populated correctly

**Test:**
```bash
curl -X POST http://localhost:8000/api/admin/composer/preview/render/docdef:XxxView:1.0.0 \
  -H "Content-Type: application/json" \
  -d '{"document_data": {...}}'
```

---

## Step 7: Golden Traces

**File:** `tests/integration/test_docdef_golden_traces.py`

Add test class:
```python
class TestXxxViewGoldenTrace:
    """Golden-trace tests for docdef:XxxView:1.0.0"""
    
    @pytest.mark.asyncio
    async def test_full_data_produces_expected_blocks(self, ...):
        """INVARIANT: Full data → expected block structure."""
        ...
    
    @pytest.mark.asyncio
    async def test_empty_optional_section_omitted(self, ...):
        """INVARIANT: Empty optional data → block omitted."""
        ...
```

**Required variants:**
- [ ] "With all sections present" fixture
- [ ] "With optional sections omitted" fixture
- [ ] For summaries: "detail_ref present" assertion

---

## Step 8: Navigation (Summary Views Only)

If this is a summary view, verify navigation:

- [ ] `detail_ref` links to correct detail view
- [ ] `detail_ref.params` correctly populated from source data
- [ ] Detail view docdef exists and is seeded

---

## Verification Checklist

- [ ] DocDef in `INITIAL_DOCUMENT_DEFINITIONS`
- [ ] Uses only existing components (no new components)
- [ ] Shape semantics match intended behavior
- [ ] Summary contract enforced (if summary view)
- [ ] Prompt preview returns expected bullets
- [ ] Render preview returns expected blocks
- [ ] Golden trace tests added
- [ ] Navigation links correct (if summary view)
- [ ] All tests pass

# Summary View Contract (Frozen)

| | |
|---|---|
| **Status** | Frozen |
| **Effective** | 2026-01-08 |
| **Governing ADR** | ADR-034 |

> ⚠️ **Governance Requirement**
>
> Summary views are intentionally lossy projections.
> Changes require explicit governance approval.

---

## Purpose

Summary views (e.g., `EpicSummaryView`, `StorySummaryView`) are lightweight projections optimized for scanning, not understanding. They must remain small, fast, and focused.

---

## Mandatory Requirements

### 1. Must include `exclude_fields`

Every summary docdef section with `source_pointer: "/"` **must** specify `exclude_fields` to strip heavy data:

```python
{
    "section_id": "epic_summaries",
    "source_pointer": "/",
    "exclude_fields": ["risks", "open_questions", "requirements", ...],
    ...
}
```

### 2. Must NOT carry typed arrays

Summary block data must never contain:

| Excluded Type | Reason |
|---------------|--------|
| `risks[]` | Use derived `risk_level` instead |
| `dependencies[]` | Use derived `dependency_count` or indicator |
| `stories[]` | Use derived `story_count` instead |
| `open_questions[]` | Use derived `question_count` or indicator |
| `requirements[]` | Use `requirement_count` instead |
| `acceptance_criteria[]` | Belongs in detail view only |

### 3. Must include `detail_ref` (DocumentRefV1)

Every summary must provide an explicit reference to the detail view.

**Schema:** `schema:DocumentRefV1` (frozen)

```json
{
  "document_type": "EpicDetailView",
  "params": {"epic_id": "AUTH-100"}
}
```

**DocDef config:**

```python
"detail_ref_template": {
    "document_type": "EpicDetailView",
    "params": {"epic_id": "/epic_id"}  # JSON pointers resolved at render time
}
```

The builder produces `block.data.detail_ref` conforming to `DocumentRefV1`.

### 4. Field limit

Summary views should contain **3-5 fields maximum**:

| Recommended Fields | Purpose |
|--------------------|---------|
| `title` | Primary identifier |
| `intent` / `vision` | One-line purpose |
| `phase` | MVP indicator |
| `risk_level` | Derived indicator |
| `detail_ref` | Link to full view |

---

## Anti-Patterns

- ❌ Adding "just one more field" to summaries
- ❌ Embedding typed arrays for "convenience"
- ❌ Duplicating detail view content
- ❌ Omitting `exclude_fields` from container sections
- ❌ Missing `detail_ref_template`

---

## Validation

Golden-trace tests enforce this contract:
- `tests/integration/test_docdef_golden_traces.py`

PRs modifying summary docdefs must pass these tests.

---

*Last updated: 2026-01-08*


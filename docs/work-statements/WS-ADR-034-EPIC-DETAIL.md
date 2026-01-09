# WS-ADR-034-EPIC-DETAIL: Epic Detail DocDef Migration

| | |
|---|---|
| **Work Statement** | WS-ADR-034-EPIC-DETAIL |
| **Title** | Epic Detail View DocDef Migration |
| **Related ADRs** | ADR-034, ADR-034-B |
| **Predecessor** | WS-ADR-034-DISCOVERY |
| **Status** | Complete |
| **Expected Scope** | Small (component reuse focused) |
| **Owner** | Tom |
| **Created** | 2026-01-08 |

> Migration follows [DOCUMENT_MIGRATION_CHECKLIST.md](../governance/DOCUMENT_MIGRATION_CHECKLIST.md)

---

## Purpose

Migrate Epic Detail (single epic) to ADR-034 document composition. This validates **component reuse across document types** — most components already exist from Project Discovery.

Epic Detail comes before Epic Backlog because:
1. Epic Detail is where semantics get exercised (reuse validation)
2. Epic Backlog should reference Epic Detail, not duplicate its composition
3. Preserves "documents as memory" principle

---

## Step 1: Section Inventory

### Expected Epic Detail Sections (from CanonicalEpicV1)

| Section | Data Shape | Existing Component? |
|---------|------------|---------------------|
| `epic_id` | `string` | Header, not a section |
| `title` | `string` | Header, not a section |
| `vision` | `string` (paragraph) | New: `ParagraphBlockV1` or inline in SummaryBlockV1 |
| `problem` | `string` (paragraph) | Reuse pattern |
| `business_goals` | `[string]` | ✅ `StringListBlockV1` |
| `in_scope` | `[string]` | ✅ `StringListBlockV1` |
| `out_of_scope` | `[string]` | ✅ `StringListBlockV1` |
| `requirements` | `[string]` or `[{id, description, priority}]` | ✅ `StringListBlockV1` or new if typed |
| `risks` | `[{description, likelihood, impact}]` | ✅ `RisksBlockV1` |
| `acceptance_criteria` | `[string]` | ✅ `StringListBlockV1` |
| `dependencies` | `[{target, type, description}]` | Maybe: `DependenciesBlockV1` |
| `open_questions` | `[{id, text, blocking, why_it_matters}]` | ✅ `OpenQuestionsBlockV1` |

---

## Step 2: Archetype Mapping

| Section | Archetype | Component |
|---------|-----------|-----------|
| `vision` | Paragraph | New: `ParagraphBlockV1` |
| `problem` | Paragraph | Reuse: `ParagraphBlockV1` |
| `business_goals` | List | ✅ Reuse: `StringListBlockV1` |
| `in_scope` | List | ✅ Reuse: `StringListBlockV1` |
| `out_of_scope` | List | ✅ Reuse: `StringListBlockV1` |
| `requirements` | List | ✅ Reuse: `StringListBlockV1` |
| `risks` | Container | ✅ Reuse: `RisksBlockV1` |
| `acceptance_criteria` | List | ✅ Reuse: `StringListBlockV1` |
| `open_questions` | Container | ✅ Reuse: `OpenQuestionsBlockV1` |

**New components needed: 1** (ParagraphBlockV1 for simple text blocks)

---

## Step 3: Components to Create

### New Schema (1)

| Schema ID | Kind | Notes |
|-----------|------|-------|
| `schema:ParagraphBlockV1` | type | Simple text content block |

### New Component (1)

| Component ID | Maps To |
|--------------|---------|
| `component:ParagraphBlockV1:1.0.0` | schema:ParagraphBlockV1 |

### Reuse Existing (5)

| Component | Reuse Count in Epic Detail |
|-----------|---------------------------|
| `StringListBlockV1` | 5x (goals, in_scope, out_scope, requirements, acceptance_criteria) |
| `RisksBlockV1` | 1x |
| `OpenQuestionsBlockV1` | 1x |

---

## Step 4: DocDef Structure

```python
docdef:EpicDetailView:1.0.0 = {
    "sections": [
        {"section_id": "vision", "shape": "single", "source_pointer": "/vision", "component_id": "component:ParagraphBlockV1:1.0.0", "context": {"title": "Vision"}},
        {"section_id": "problem", "shape": "single", "source_pointer": "/problem", "component_id": "component:ParagraphBlockV1:1.0.0", "context": {"title": "Problem/Opportunity"}},
        {"section_id": "business_goals", "shape": "container", "source_pointer": "/business_goals", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Business Goals"}},
        {"section_id": "in_scope", "shape": "container", "source_pointer": "/in_scope", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "In Scope", "style": "check"}},
        {"section_id": "out_of_scope", "shape": "container", "source_pointer": "/out_of_scope", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Out of Scope"}},
        {"section_id": "requirements", "shape": "container", "source_pointer": "/requirements", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Requirements", "style": "numbered"}},
        {"section_id": "acceptance_criteria", "shape": "container", "source_pointer": "/acceptance_criteria", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Acceptance Criteria", "style": "check"}},
        {"section_id": "risks", "shape": "container", "source_pointer": "/risks", "component_id": "component:RisksBlockV1:1.0.0", "context": {"title": "Risks"}},
        {"section_id": "open_questions", "shape": "container", "source_pointer": "/open_questions", "component_id": "component:OpenQuestionsBlockV1:1.0.0", "context": {"title": "Open Questions"}},
    ]
}
```

---

## Step 5: Acceptance Criteria

1. `schema:ParagraphBlockV1` exists and accepted
2. `component:ParagraphBlockV1:1.0.0` exists with fragment binding
3. `docdef:EpicDetailView:1.0.0` exists
4. Preview renders all sections with correct context
5. Existing components (StringListBlockV1, RisksBlockV1, OpenQuestionsBlockV1) work without modification
6. No HTML in JSON responses
7. Full test suite passes

---

## Findings

### Components Created

| Type | ID | Purpose |
|------|-----|---------|
| Schema | `schema:ParagraphBlockV1` | Simple text paragraph block |
| Component | `component:ParagraphBlockV1:1.0.0` | Narrative content rendering |
| Fragment | `ParagraphBlockV1Fragment` | Renders text with optional title |
| DocDef | `docdef:EpicDetailView:1.0.0` | Epic detail rendering projection |

### Component Reuse Validated

| Component | Reuse Count | Sections |
|-----------|-------------|----------|
| `StringListBlockV1` | 5x | goals, in_scope, out_scope, requirements, acceptance_criteria |
| `RisksBlockV1` | 1x | risks |
| `OpenQuestionsBlockV1` | 1x | open_questions |
| `ParagraphBlockV1` | 2x | vision, problem |

**Total: 9 sections, only 1 new component needed.**

### Builder Enhancement

Fixed: `shape: "single"` now receives static context from section config (same fix as containers).

### Naming Convention Established

- `docdef:XxxView:1.0.0` = rendering projection over canonical record
- `CanonicalXxxV1` = data authority (Pydantic schema)

This prevents accidental evolution of docdefs becoming data authorities.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial inventory and mapping |

---

*End of Work Statement*



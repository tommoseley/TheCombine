# Document Migration Checklist (Canonical)

| | |
|---|---|
| **Status** | Canonical |
| **Effective** | 2026-01-08 |
| **Governing ADR** | ADR-034 |
| **Validated By** | WS-ADR-034-DISCOVERY |

> ⚠️ **Governance Requirement**
>
> All document type migrations MUST follow this checklist.
> PRs adding new docdefs should reference this document.

---
This checklist guides migration of existing document types to the ADR-034 document composition system.

**Validated by:** WS-ADR-034-DISCOVERY (Project Discovery migration)

---

## Pre-Migration

- [ ] Identify existing handler file and schema definition
- [ ] Review current render output (what HTML does it produce?)
- [ ] Collect sample payload (real or fixture data)

---

## Step 1: Section Inventory

- [ ] List all sections from existing handler
- [ ] Document current data shapes for each section
- [ ] Note which sections are required vs optional

**Output:** Section inventory table

| Section | Data Shape | Required | Notes |
|---------|------------|----------|-------|
| ... | ... | ... | ... |

---

## Step 2: Archetype Mapping

Classify each section:

| Archetype | When to Use | Shape | Example |
|-----------|-------------|-------|---------|
| **Paragraph** | Single text block or multi-field object | `single` | Summary, description |
| **List** | Simple string array | `container` | Constraints, assumptions |
| **Container (typed)** | Array of structured objects | `container` | Risks, questions, stories |

- [ ] Map each section to an archetype
- [ ] Identify reusable existing components
- [ ] List new components needed

---

## Step 3: Create Schemas

For each new schema needed:

- [ ] Define JSON Schema with `$id: "schema:XxxV1"`
- [ ] Add to `seed_schema_artifacts.py` (both definition and list entry)
- [ ] Update schema count test

**Container schemas** should have:
- `items` array (required)
- Optional `title` override
- Optional `meta` for derived counts

---

## Step 4: Create Components

For each new component:

- [ ] Define component with `component_id: "component:XxxV1:1.0.0"`
- [ ] Add generation guidance bullets
- [ ] Add view binding to fragment
- [ ] Add to `seed_component_artifacts.py`
- [ ] Add fragment alias to `fragment_registry_service.py`

---

## Step 5: Create Fragments

For each new fragment:

- [ ] Create Jinja2 template
- [ ] Handle both direct data and `{"value": ...}` wrapped strings
- [ ] Include empty state handling
- [ ] Use context for titles/styles
- [ ] Add to `seed_fragment_artifacts.py`

---

## Step 6: Create DocDef

- [ ] Define `docdef:DocumentType:1.0.0`
- [ ] Set `prompt_header` with role and constraints
- [ ] Define sections in order:
  - `section_id` — unique within docdef
  - `title` — display name
  - `order` — sort order (10, 20, 30...)
  - `component_id` — component reference
  - `shape` — single, list, nested_list, or container
  - `source_pointer` — JSON pointer to data
  - `context` — static context (titles, styles)
- [ ] Add to `INITIAL_DOCUMENT_DEFINITIONS`

---

## Step 7: Test

- [ ] Run unit tests (schema count, etc.)
- [ ] Run full test suite
- [ ] Seed database artifacts
- [ ] Test prompt preview endpoint
- [ ] Test render preview endpoint with sample payload
- [ ] Verify all blocks have correct type, data, context

---

## Step 8: Document

- [ ] Update work statement with findings
- [ ] Note reusable patterns discovered
- [ ] Note any builder enhancements needed
- [ ] Commit with descriptive message

---

## Common Patterns

### Reusing StringListBlockV1

Any `string[]` section can use `StringListBlockV1`:

```python
{
    "section_id": "constraints",
    "component_id": "component:StringListBlockV1:1.0.0",
    "shape": "container",
    "source_pointer": "/known_constraints",
    "context": {"title": "Known Constraints", "style": "bullet"}
}
```

Styles: `bullet` (default), `numbered`, `check`

### Static Context for Titles

For containers without `repeat_over`, use static context:

```python
"context": {"title": "Section Title"}
```

This flows directly to the fragment.

### Typed Container Items

For structured arrays (risks, questions, stories), create:
1. Item schema (`schema:XxxV1`)
2. Block schema (`schema:XxxBlockV1`) with `items` array
3. Item fragment (for nested rendering)
4. Block fragment (iterates items)

---

## Anti-Patterns to Avoid

- ❌ Don't create item-specific components when `StringListBlockV1` works
- ❌ Don't use `shape: "list"` for arrays that should render as a single block
- ❌ Don't hardcode titles in fragments — use context
- ❌ Don't duplicate fragment logic — extract to shared partials if needed

---

*Last validated: 2026-01-08 (WS-ADR-034-DISCOVERY)*



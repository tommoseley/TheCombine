# Render Shape Semantics (Frozen)

| | |
|---|---|
| **Status** | Frozen |
| **Effective** | 2026-01-08 |
| **Governing ADR** | ADR-034, ADR-034-B |
| **Validated By** | WS-ADR-034-EXP, WS-ADR-034-EXP2, WS-ADR-034-EXP3 |

---

This document defines the **authoritative semantics** for DocumentDefinition section shapes and how they map to RenderModel blocks.

**Changes to these semantics require explicit governance approval.**

---

## Terms

| Term | Definition |
|------|------------|
| **DocumentDefinition** | Declarative composition of sections into a document |
| **RenderModel** | Data-only structure emitted for channel rendering |
| **RenderBlock** | A single renderable unit with type, key, data, and context |
| **repeat_over** | Parent iteration pointer (single-level only) |
| **source_pointer** | Pointer resolved against root or current parent (depending on repeat_over) |

---

## Shape Semantics (Authoritative)

### 1. `shape = "single"`

- Produces exactly **1 RenderBlock** for the section
- `source_pointer` resolves against the **document root**

### 2. `shape = "list"`

- Produces exactly **N RenderBlocks**, one per item in the resolved list
- `source_pointer` resolves against the **document root**

### 3. `shape = "nested_list"`

- Produces **N RenderBlocks**, one per item, for each parent in `repeat_over`
- `repeat_over` **must** point to a list
- `source_pointer` resolves **relative to each repeat_over parent**
- Each block receives context from its parent

### 4. `shape = "container"`

| `repeat_over` | Output |
|---------------|--------|
| absent | Exactly **1 RenderBlock** containing all items |
| present | Exactly **N RenderBlocks**, one per parent, each containing that parent's items |

- `source_pointer` resolves **relative to each repeat_over parent** (if present) or **document root** (if absent)
- Each produced container block contains items under `data.items`
- Each block receives context from its parent (if repeat_over present)

---

## Quick Reference Table

| Shape | `repeat_over` | Output | Pointer Resolution |
|-------|---------------|--------|-------------------|
| `single` | — | 1 block | Root |
| `list` | — | N blocks (per item) | Root |
| `nested_list` | required | N blocks (per item across parents) | Relative to parent |
| `container` | no | 1 block (all items) | Root |
| `container` | yes | N blocks (per parent) | Relative to parent |

---

## Pointer Resolution Rules (Frozen)

1. If `repeat_over` is **present**: `source_pointer` is resolved relative to each parent item
2. If `repeat_over` is **absent**: `source_pointer` is resolved against the document root

---

## Documented Boundary (Intentional)

- Only **one level** of parent iteration is supported via `repeat_over`
- No nested wildcard traversal is supported (e.g., `/epics/*/capabilities/*/...`)
- No nested `repeat_over` is supported
- This boundary is **by design**, not a limitation to be fixed

---

## Non-Features (By Design)

The following are explicitly **not supported** and require governance approval to add:

| Feature | Status | Rationale |
|---------|--------|-----------|
| `filter` semantics in docdef | ❌ Not supported | DSL creep |
| Wildcard pointers in docdef | ❌ Not supported | DSL creep |
| Nested `repeat_over` | ❌ Not supported | Complexity explosion |
| Expression language / conditional logic | ❌ Not supported | DSL creep |
| Absolute pointer resolution with repeat_over | ❌ Not supported | Ambiguity |

**DocDef is not a DSL. Keep it declarative and mechanical.**

---

## Validation Evidence

| Assertion | Test Coverage |
|-----------|---------------|
| `container` without `repeat_over` → 1 block | `test_render_shapes_semantics.py::test_container_no_repeat_over` |
| `container` + `repeat_over` → N blocks per parent | `test_render_shapes_semantics.py::test_container_with_repeat_over` |
| `nested_list` → N blocks per item | `test_render_shapes_semantics.py::test_nested_list_blocks_per_item` |
| Deep nesting → empty (boundary) | `test_render_shapes_semantics.py::test_deep_nesting_boundary` |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-08 | Initial freeze based on EXP1-EXP3 validation |

---

*End of Specification*


---

## Metadata Semantics

### `section_count`

**Definition:** Number of docdef sections evaluated, including those omitted due to empty data.

**NOT:** Number of blocks rendered.

```
docdef sections: 3 (summary, constraints, risks)
source data: summary present, constraints present, risks empty
section_count: 3
blocks emitted: 2
```

This distinction is frozen. If "blocks rendered" is needed, it requires a new metadata field (out of scope for current semantics).

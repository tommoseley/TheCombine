---
name: ia-validation
description: Validate Information Architecture contracts per ADR-054. Use when authoring or reviewing IA sections in package.yaml, checking render_as declarations, or enforcing coverage levels.
---

# IA Validation (ADR-054)

## Coverage Levels

**Level 0 — Pointer Only (Forbidden for Tier-1)**
- Section binds to schema path with no `render_as` declaration

**Level 1 — Render Type Declared (Forbidden for Tier-1)**
- Every bind includes `render_as` but complex types don't enumerate internal fields

**Level 2 — Fully Specified (Required for Tier-1)**
- Complex types (object/array) must declare internal field mapping:
  - `table` requires `columns` with field paths and headers
  - `card-list` requires `card` with `title` and `fields` (each with `path` and `render_as`)
  - `nested-object` requires `fields` with explicit sub-fields and their `render_as` types

## Pinned render_as Vocabulary (v1)

| render_as | Typical Schema Type | Description |
|-----------|-------------------|-------------|
| `paragraph` | string | Plain text block |
| `list` | array of strings | Unordered bullet list |
| `ordered-list` | array of strings | Numbered list |
| `table` | array of objects | Rows and columns with column definitions |
| `key-value-pairs` | object with scalar values | Label: value layout |
| `card-list` | array of objects | Cards with title + sub-field rendering |
| `nested-object` | object | Named properties as labeled sub-sections |

## No-Guessing Rule (Mandatory for Tier-1)

- `render_as: paragraph` default applies **only to scalar string fields**
- For complex types (schema type `object` or `array`):
  - `render_as` MUST be explicitly declared
  - `render_as: paragraph` on a complex type is INVALID (test failure)
  - Missing `render_as` on a complex type is INVALID (test failure)

## Authoring IA in package.yaml

```yaml
information_architecture:
  version: 2
  sections:
    overview:
      label: "Overview"
      binds:
        - path: architecture_summary
          render_as: nested-object
          fields:
            - path: title
              render_as: paragraph
            - path: style
              render_as: paragraph
            - path: key_decisions
              render_as: list
        - path: risks
          render_as: table
          columns:
            - field: risk
              label: "Risk"
            - field: impact
              label: "Impact"
            - field: mitigation
              label: "Mitigation"
```

## Validation Checklist

1. Every bind path resolves to a valid schema field
2. Every schema-required field appears in at least one IA section
3. All `render_as` values are in pinned vocabulary
4. Complex types have explicit `render_as` (not paragraph, not missing)
5. `table` binds have `columns` with `field` + `label`
6. `card-list` binds have `card` with `title` and `fields` (each with `path` + `render_as`)
7. `nested-object` binds have `fields` with `path` + `render_as`
8. Rendering targets only reference declared section IDs

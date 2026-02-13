# Fragment Standards

**Status:** Frozen  
**Effective:** 2026-01-09  
**WS:** WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS

## Purpose

Defines mandatory requirements for all fragments in `INITIAL_FRAGMENT_ARTIFACTS`.

## Core Principle: Data-Only Guarantee

**Fragments are lenses, not sources.**

No fragment may introduce semantic meaning not present in `block.data` or `context`.

Fragments:
- ✅ Render data from `block.data.*` and `block.context.*`
- ✅ Apply presentation styling (colors, layout, icons)
- ✅ Conditionally show/hide based on data presence
- ❌ Must NOT compute derived values
- ❌ Must NOT add content not in the data
- ❌ Must NOT reference fields not in the schema

## Required Fields

Every fragment MUST have:

| Field | Requirement |
|-------|-------------|
| `fragment_id` | Format: `fragment:XxxV1:web:1.0.0` |
| `version` | Semantic version string |
| `schema_type_id` | Matches schema name (e.g., `ParagraphBlockV1`) |
| `status` | One of: `draft`, `accepted`, `deprecated` |
| `fragment_markup` | Valid Jinja2 template |

## Variable Naming Convention

| Context | Variable | Example |
|---------|----------|---------|
| Block rendering | `block.data.*` | `{{ block.data.value }}` |
| Block context | `block.context.*` | `{{ block.context.title }}` |
| Item in container | `item.*` | `{{ item.text }}` |
| Loop iteration | `item` or descriptive | `{% for item in block.data.items %}` |

## Fragment ID Format

All fragment IDs MUST use canonical format:

```
fragment:{SchemaName}:web:{version}
```

Examples:
- `fragment:OpenQuestionV1:web:1.0.0`
- `fragment:StringListBlockV1:web:1.0.0`

## Styling Guidelines

- Use Tailwind CSS utility classes
- Follow "Calm Authority" design system
- No inline styles
- No hardcoded colors (use Tailwind palette)

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `{{ computed_value }}` | Fragments don't compute |
| Hardcoded text not in data | Fragments are lenses |
| `block.foo` without schema field | Schema drift |
| Direct database queries | Fragments are render-only |

## Enforcement

Tests in `tests/domain/test_component_completeness.py` enforce these standards:
- `test_all_fragment_ids_resolve`
- `test_all_fragments_compile`
- `test_all_fragments_use_canonical_ids`
- `test_all_component_fragments_exist`

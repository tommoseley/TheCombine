# Component Completeness Standards

**Status:** Frozen  
**Effective:** 2026-01-09  
**WS:** WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS

## Purpose

Defines mandatory requirements for all components in `INITIAL_COMPONENT_ARTIFACTS`.

## Required Fields

Every component MUST have:

| Field | Requirement |
|-------|-------------|
| `component_id` | Format: `component:XxxV1:1.0.0` |
| `schema_id` | Format: `schema:XxxV1` |
| `generation_guidance.bullets` | Non-empty array |
| `view_bindings.web.fragment_id` | Format: `fragment:XxxV1:web:1.0.0` |
| `status` | One of: `draft`, `accepted`, `deprecated` |

## Generation Guidance Style Guide

Bullets MUST be:
- **Declarative** — state facts, not instructions
- **Imperative** — command form ("Produce...", "Include...", "Set...")
- **Role-agnostic** — no "you", no UI instructions

Bullets MUST NOT contain:
- "you should", "you must", "you can"
- UI instructions ("click", "select", "button")
- Implementation details (class names, endpoints)

### Good Examples

```
"Produce a stable question id (e.g., Q-001)."
"Set blocking=true only if work cannot proceed responsibly."
"Keep each field under 2-3 sentences for readability."
```

### Bad Examples

```
"You should provide a stable question id."  ❌ (contains "you")
"Click the submit button to save."  ❌ (UI instruction)
"Use the QuestionService.create() method."  ❌ (implementation detail)
```

### Field-Specific Bullets

Field-specific bullets (e.g., `problem_understanding: What is the core problem?`) are permitted **only** when:
- The schema explicitly defines those fields
- The component is a typed block (not a generic container)

Field-specific bullets are **NOT** permitted for:
- Generic containers (`StringListBlockV1`, `RisksBlockV1`, etc.)
- Render-only blocks where items are provided upstream

### Container Component Guidance

Container components (those with `items[]`) must use this standard bullet:

```
"Render-only container. Do not generate this block; items are provided upstream."
```

Containers must NOT include:
- Rendering instructions (`style`, `context.title`, `order`)
- Schema name references (`conforming to XxxV1`)
- Field-specific guidance

## Fragment ID Format

All fragment IDs MUST use canonical format:

```
fragment:{SchemaName}:web:{version}
```

Examples:
- `fragment:OpenQuestionV1:web:1.0.0`
- `fragment:ParagraphBlockV1:web:1.0.0`

Legacy short-form IDs (e.g., `OpenQuestionV1Fragment`) are NOT permitted.

## Enforcement

Tests in `tests/domain/test_component_completeness.py` enforce these standards:
- `test_all_components_have_guidance_bullets`
- `test_all_components_have_web_binding`
- `test_all_fragment_ids_use_canonical_format`
- `test_guidance_bullets_are_declarative`


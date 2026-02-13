# ADR-034 Amendment A: Clarifications & Contract Completion

| | |
|---|---|
| **Amendment ID** | ADR-034-A |
| **Date** | 2026-01-06 |
| **Status** | Accepted |
| **Applies To** | ADR-034 v3 |

---

## A.1 Section Definition Completeness

The Document Composition Manifest section definition is clarified and completed.

Each section definition MUST include the following fields:

```json
{
  "section_id": "string",
  "title": "string",
  "description": "string",

  "order": 10,

  "component_id": "component:<SchemaType>:<component_semver>",

  "shape": "single | list | nested_list",

  "source_pointer": "/path/to/data",
  "repeat_over": "/path/to/parent/container",

  "context": {
    "<context_key>": "<json_pointer>"
  }
}
```

### Field Semantics

- **shape**: Explicitly defines how data is rendered. Shape MUST NOT be inferred.
- **source_pointer**: JSON Pointer relative to the current iteration context indicating where component data is found.
- **repeat_over**: JSON Pointer indicating a parent collection to iterate (used only for nested_list).
- **context**: Optional mapping of parent data into block-level render context (e.g., propagating epic_id to child OpenQuestion blocks).

Flattening domain data to satisfy rendering is explicitly prohibited.

---

## A.2 Canonical Component ID Convention

Component identifiers MUST follow this format:

```
component:<SchemaType>:<component_semver>
```

Example:
```
component:OpenQuestionV1:1.0.0
```

Rules:
- `<SchemaType>` MUST match the referenced schema's major version
- `<component_semver>` governs generation guidance and view bindings
- Schema evolution requires a new component tied to the new schema version

This prevents accidental reuse of incompatible components.

---

## A.3 Fragment Identifier Canonical Format

Fragment identifiers MUST follow this canonical format:

```
fragment:<SchemaType>:<channel>:<semver>
```

Example:
```
fragment:OpenQuestionV1:web:1.0.0
```

Existing fragment artifacts created under ADR-032 using legacy identifiers (e.g., `OpenQuestionV1Fragment`) MUST be migrated to this format via a governed Work Statement.

---

## A.4 RenderBlock Context Propagation (ADR-033 Alignment)

RenderBlockV1 is amended to support optional parent context:

```json
{
  "type": "schema:OpenQuestionV1",
  "key": "Q-201",
  "data": { /* validated block data */ },
  "context": { /* parent-supplied metadata */ }
}
```

Rules:
- `data` MUST conform to the canonical schema
- `context` is read-only and not validated by the block schema
- Context is used exclusively for rendering or UX behavior
- Context MUST NOT alter validation or generation semantics

This enables nested composition without schema pollution.

---

## A.5 Generation Guidance Scope

For ADR-034 v3:
- `generation_guidance.bullets` is defined as `string[]`
- Bullets are authoritative, ordered instructions
- Conditional or structured guidance is out of scope for this version

Future extensions may introduce structured guidance under a new version.

---

## A.6 Schema Commitment Clause

ADR-034 defines required structure and semantics.

The following full JSON schemas MUST be committed as part of the first implementation Work Statement:
- `schema:CanonicalComponentV1`
- `schema:DocumentDefinitionV2`

These schemas SHALL conform to the requirements specified in ADR-034 and this amendment.

---

## A.7 No Other Changes

All other sections, rules, and decisions in ADR-034 v3 remain unchanged and in force.
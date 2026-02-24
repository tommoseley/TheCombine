# ADR-054 -- Governed Information Architecture with HTML and PDF Targets

**Status:** Accepted
**Date:** 2026-02-22
**Related:** ADR-051, ADR-052, ADR-053

---

## Context

During the ontology migration (seed -> combine-config), document presentation drifted. Tabs and layout structure were lost because Information Architecture (IA) was not governed.

The Combine already governs:

- Schema (structure)
- LLM prompts (generation)
- Workflow ordering (production)

It does not govern:

- How document meaning is organized and presented.

Additionally, PDF export is now a near-term requirement.

Without a shared IA layer:

- HTML layout drifts.
- PDF linearization becomes ad hoc.
- Schema, prompt, and rendering fall out of alignment.

---

## Decision

### 1. The Document Semantics Triad

Every document type release SHALL align three contracts:

**Schema Contract** -- Defines fields and structural constraints.

**LLM Contract** -- Defines how required fields are populated. Must enforce schema-required fields.

**Information Architecture Contract** -- Defines canonical sections and reading order. Lives in package.yaml. Governs rendering.

A document release is valid only if these are aligned.

### 2. Canonical Section Model with Block Rendering

Each document type release SHALL define canonical sections in:

`combine-config/document_types/<doc_type>/releases/<version>/package.yaml`

Sections declare not only which schema fields they bind to, but how each field renders. Without render type declarations, renderers must guess at structure, producing raw JSON dumps or flat text for complex nested objects.

#### Section Structure

```yaml
information_architecture:
  version: 1

  sections:
    - id: plan.summary
      label: Plan Summary
      binds:
        - path: plan_summary.overall_intent
          render_as: paragraph
          label: Overall Intent
        - path: plan_summary.mvp_definition
          render_as: paragraph
          label: MVP Definition
        - path: plan_summary.key_constraints
          render_as: list
          label: Key Constraints
        - path: plan_summary.sequencing_rationale
          render_as: paragraph
          label: Sequencing Rationale
```

#### Complex Object Example (Card List)

```yaml
    - id: architecture.workflows
      label: Workflows
      binds:
        - path: workflows
          render_as: card-list
          card:
            title: name
            fields:
              - path: description
                render_as: paragraph
              - path: triggers
                render_as: list
              - path: steps
                render_as: ordered-list
              - path: outputs
                render_as: list
```

#### Pinned render_as Vocabulary

The following render types are the complete set for v1. Renderers MUST support all of them. No ad-hoc types may be introduced without an ADR amendment.

| render_as | Description | Typical schema type |
|-----------|-------------|---------------------|
| `paragraph` | Plain text block | string |
| `list` | Unordered bullet list | array of strings |
| `ordered-list` | Numbered list | array of strings |
| `table` | Rows and columns (requires column definitions) | array of objects |
| `key-value-pairs` | Label: value layout | object with scalar values |
| `card-list` | Array of objects, each as a card with sub-fields | array of objects |
| `nested-object` | Object with named properties as labeled sub-sections | object |

#### Table Column Definitions

When `render_as: table`, a `columns` array is required:

```yaml
        - path: dependencies
          render_as: table
          columns:
            - field: name
              label: Dependency
            - field: version
              label: Version
            - field: purpose
              label: Purpose
```

#### Rules

- `id` is stable and versioned.
- `path` in binds MUST reference a valid schema path (dot-notation for nested fields).
- `render_as` MUST be one of the pinned vocabulary values.
- `label` on a bind is the rendered heading or field label.
- Sections are target-agnostic -- render types apply to both HTML and PDF.
- `card-list` requires a `card` definition with `title` and `fields`.
- `table` requires a `columns` definition.
- If `render_as` is omitted, the renderer MUST treat the field as `paragraph` (safe default, never raw JSON).

### 3. Rendering Targets (Two Only)

The Combine SHALL support two rendering targets:

**A. detail_html**

- May use tabs.
- May group sections into tabs.
- Must only reference declared section IDs.

```yaml
rendering:
  detail_html:
    layout: tabs
    tabs:
      - id: overview
        sections:
          - overview.summary
          - scope.in
          - scope.out
```

**B. pdf**

- Must linearize sections.
- No tab concept.
- Must define deterministic order.

```yaml
  pdf:
    linear_order:
      - overview.summary
      - scope.in
      - scope.out
    toc: true
```

Rules:

- Both targets may only reference declared section IDs.
- Neither target may introduce new binds.
- If `pdf.linear_order` is absent, section declaration order is used.
- No other targets (mobile, floor unification) are defined in this ADR.

### 4. Golden Contract Tests

For each Tier-1 document type:

Tests SHALL validate:

- All binds paths exist in the schema.
- All schema-required fields appear in at least one section.
- All detail_html sections reference declared section IDs.
- All pdf.linear_order entries reference declared section IDs.

Tests SHALL fail on IA drift.

### 5. PDF as First-Class Output

PDF export SHALL:

- Use canonical sections.
- Use declared linear order.
- Generate deterministic headings.
- Optionally generate a TOC if enabled.

PDF generation SHALL NOT invent structure absent from IA.

### 6. Scope Limitations

This ADR explicitly does NOT:

- Introduce a layout DSL.
- Introduce mobile rendering.
- Introduce floor unification under projection model.
- Introduce UX AI layout generation.
- Replace existing view system immediately.

These may be addressed in future ADRs when required.

---

## Consequences

### Positive

- Prevents silent HTML layout drift.
- Enables deterministic PDF export.
- Aligns schema, generation, and presentation.
- Keeps scope bounded to real needs.

### Negative

- Adds configuration responsibility per document type.
- Requires test coverage to maintain alignment.

---

## Migration Plan

### Phase 1A -- Govern IA + Restore HTML

- Add `information_architecture` + `rendering.detail_html` to Tier-1 document types (starting with TA).
- Update SPA to render tabs/sections from `package.yaml`.
- Add golden contract tests (IA <-> schema <-> HTML sections).
- Deliverable: Tabs are back and governed; drift is caught.

### Phase 1B -- PDF Export MVP

- Implement PDF generation consuming the same IA sections and `rendering.pdf.linear_order`.
- Decide PDF approach (server-side vs client-side; CSS-to-PDF vs direct PDF lib).
- Add tests (deterministic section order; basic snapshot/fixture on generated PDF).
- Deliverable: PDF exports exist and follow IA.

---

## Summary

ADR-054 establishes governed Information Architecture for document types, with two supported rendering targets:

- detail_html (tabs allowed)
- pdf (linearized)

Documents are not only structured data -- they are structured decisions.
That structure must be versioned and enforced.


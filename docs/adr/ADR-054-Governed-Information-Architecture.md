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

### 2. Canonical Section Model (Minimal)

Each document type release SHALL define canonical sections in:

`combine-config/document_types/<doc_type>/releases/<version>/package.yaml`

Structure:

```yaml
information_architecture:
  version: 1

  sections:
    - id: overview.summary
      label: Summary
      binds:
        - summary

    - id: scope.in
      label: Scope In
      binds:
        - scope_in

    - id: scope.out
      label: Scope Out
      binds:
        - scope_out
```

Rules:

- `id` is stable and versioned.
- `binds` must reference valid schema paths.
- Sections define semantic units of meaning.
- Sections are target-agnostic.
- No DSL for density, importance, or mobile behavior is introduced at this stage.

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

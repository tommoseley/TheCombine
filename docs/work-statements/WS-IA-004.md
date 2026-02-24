# WS-IA-004: Block Rendering Model for Remaining Tier-1 Document Types

## Status: Accepted

## Governing References

- ADR-054 -- Governed Information Architecture with HTML and PDF Targets
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- combine-config/document_types/
- spa/src/
- tests/

---

## Objective

Apply the block rendering model proven by WS-IA-003 (Technical Architecture) to the remaining Tier-1 document types: Project Discovery (PD), Implementation Plan Primary (IPP), and Implementation Plan (IPF). Each gets Level 2 coverage (ADR-054 Section 2a) with full block rendering definitions, `rendering.detail_html`, and `rendering.pdf.linear_order` in its package.yaml. The generic block renderer built in WS-IA-003 renders all three without type-specific code.

---

## Preconditions

- WS-IA-002 complete (PD, IPP, IPF have simple IA binds and tabs from config)
- WS-IA-003 complete (TA has full block model IA, generic block renderer built and proven)
- Pattern established: schema audit -> IA definition -> golden contract tests -> config-driven rendering
- SPA block renderer supports all 7 render_as types

---

## Scope

### In Scope

- Schema audit for PD, IPP, IPF (catalog every field, type, nesting)
- Add full `information_architecture` with block model to each package.yaml:
  - Every field mapped to a section with `render_as` type
  - Complex objects use card-list, table, nested-object as appropriate
  - No field left unmapped (no raw JSON rendering)
- Add `rendering.detail_html` with tab structure appropriate to each type
- Add `rendering.pdf.linear_order` for future PDF consumption
- Golden contract tests for each (same pattern as TA)
- Verify SPA renders all three from generic block renderer (no type-specific code)

### Out of Scope

- Technical Architecture block model (done in WS-IA-003)
- PDF rendering implementation (WS-PDF-001)
- Concierge Intake (not a Tier-1 production document)
- Work Package / Work Statement document types (future)
- Floor view changes
- Block renderer changes (should not need modification -- if it does, that is a WS-IA-003 gap)

---

## Tier 1 Verification Criteria

All new Tier-1 tests written for this WS must fail prior to implementation and pass after.

Per document type (PD, IPP, IPF):

1. **Binds exist in schema**: Every `path` in IA binds resolves to a valid schema field
2. **Required fields covered**: Every schema-required field appears in at least one IA section
3. **HTML sections valid**: Every section in `rendering.detail_html` tabs references a declared section ID
4. **No orphaned sections**: No IA section is unreferenced by any rendering target
5. **PDF linear order valid**: Every entry in `rendering.pdf.linear_order` references a declared section ID
6. **render_as values valid**: All render_as values in pinned vocabulary
7. **card-list has card definition**: Every card-list bind includes card with title and fields, each field with `path` and `render_as`
8. **table has columns**: Every table bind includes columns array with `field` and `label`
9. **nested-object has fields**: Every nested-object bind includes explicit fields enumeration

### No-Guessing Tests (ADR-054 Section 2b)

10. **Complex types have render_as**: For every bind, if schema type at path is object or array, `render_as` MUST be present
11. **No paragraph on complex types**: `render_as: paragraph` on an object or array type is a test failure
12. **card-list sub-fields specified**: Every field inside a `card.fields` array has its own `render_as` declaration
13. **Level 2 coverage achieved**: IA coverage report shows 100% of binds at Level 2 for PD, IPP, and IPF

### Coverage Report

14. **Coverage report generated**: Golden contract tests produce a coverage report artifact per document type

### Cross-cutting

15. **SPA renders all four types from config**: PD, IPP, IPF, and TA all render via generic block renderer with no type-specific components
16. **Contract tests pass for all four**: Golden contract test suite covers TA + PD + IPP + IPF
17. **No block renderer modifications needed**: If renderer changes are required, they indicate a WS-IA-003 gap (document and flag)

---

## Procedure

### Phase 1: Schema Audits

For each of PD, IPP, IPF:
- Catalog every field: name, type, nesting depth, sub-fields
- Classify each as: paragraph, list, ordered-list, table, key-value-pairs, card-list, nested-object
- Identify appropriate tab groupings for each document type

### Phase 2: Write Failing Tests (Intent-First)

Extend golden contract test suite to cover PD, IPP, IPF (criteria 1-9 per type, criteria 10-12 cross-cutting). Verify all fail.

### Phase 3: Implement

1. Write `information_architecture` with full block model for PD package.yaml
2. Write `rendering.detail_html` and `rendering.pdf` for PD
3. Repeat for IPP
4. Repeat for IPF
5. Verify SPA renders all three from config (no new components needed)

### Phase 4: Verify

1. All Tier 1 tests pass
2. All four document types render with correct tabs and block types in browser
3. No raw JSON displayed for any field in any document type
4. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify TA IA (that is WS-IA-003)
- Do not implement PDF rendering (that is WS-PDF-001)
- Do not modify document schemas or LLM prompts
- Do not add type-specific rendering components (use generic block renderer)
- Do not add new render_as types without ADR-054 amendment

---

## Verification Checklist

- [ ] Schema audits complete for PD, IPP, IPF
- [ ] All new Tier-1 tests fail before implementation
- [ ] IA with full block model added to PD package.yaml
- [ ] IA with full block model added to IPP package.yaml
- [ ] IA with full block model added to IPF package.yaml
- [ ] detail_html and pdf specs added to all three
- [ ] Every field in every type has declared render_as
- [ ] No raw JSON rendered for any field
- [ ] SPA renders all three from generic block renderer
- [ ] No new type-specific components created
- [ ] Golden contract tests pass for all four Tier-1 types
- [ ] All new Tier-1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-IA-004_



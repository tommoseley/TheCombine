# WS-IA-003: Block Rendering Model for Technical Architecture

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

Add the block rendering model (ADR-054 Section 2) to the Technical Architecture document type's existing `information_architecture`, including the block rendering model (ADR-054 Section 2). Every schema field that the TA produces must have a declared `render_as` type so the SPA never guesses at structure. Update the SPA to render tabs, sections, and blocks from package.yaml configuration. Add golden contract tests.

Deliverable: TA fields render with declared block types (paragraph, list, card-list, table, etc.) instead of raw JSON. Extends the simple binds (Level 1) established by WS-IA-001 to Level 2 coverage per ADR-054 Section 2a.

---

## Preconditions

- WS-IA-001 complete (TA has simple IA binds, tabs render from config, golden contract tests pass)
- ADR-054 accepted (with block rendering model)
- TA schema exists and defines the full field structure
- SPA renders TA tabs from config

---

## Scope

### In Scope

- Audit TA schema to catalog every field and its type (string, array, object, nested)
- Add `information_architecture` to TA package.yaml with full block model:
  - Every field mapped to a section
  - Every field assigned a `render_as` type from the pinned vocabulary
  - Complex objects (workflows, components, data models, API interfaces) use `card-list` or `nested-object` with sub-field definitions
  - Tables use `columns` definitions
- Add `rendering.detail_html` with tab structure:
  - Workflows tab
  - Components tab
  - Data Models tab
  - API Interfaces tab
  - Overview tab (summary, constraints, decisions)
- Add `rendering.pdf.linear_order` for future PDF consumption
- Build SPA block renderer that maps `render_as` values to React components:
  - `paragraph` -> text block
  - `list` -> `<ul>` with `<li>` items
  - `ordered-list` -> `<ol>` with `<li>` items
  - `table` -> `<table>` with column headers from definition
  - `key-value-pairs` -> label/value pairs
  - `card-list` -> card components with title and sub-field rendering
  - `nested-object` -> labeled sub-sections
- Update SPA document detail view to consume IA config instead of hardcoded view definitions
- Golden contract tests

### Out of Scope

- Other document types (PD, IPP, IPF -- that is WS-IA-002)
- PDF rendering (WS-PDF-001)
- Floor view changes
- Mobile rendering
- New document types or schema changes

---

## Tier 1 Verification Criteria

All new Tier-1 tests written for this WS must fail prior to implementation and pass after.

### Golden Contract Tests

1. **Binds exist in schema**: Every `path` in IA section binds resolves to a valid TA schema field
2. **Required fields covered**: Every schema-required field appears in at least one IA section
3. **HTML sections valid**: Every section referenced in `rendering.detail_html` tabs exists in IA sections
4. **No orphaned sections**: No IA section is unreferenced by any rendering target
5. **PDF linear order valid**: Every entry in `rendering.pdf.linear_order` references a declared section ID
6. **render_as values valid**: Every `render_as` value is in the pinned vocabulary (paragraph, list, ordered-list, table, key-value-pairs, card-list, nested-object)
7. **card-list has card definition**: Every `card-list` bind includes a `card` with `title` and `fields`, each field with `path` and `render_as`
8. **table has columns**: Every `table` bind includes a `columns` array with `field` and `label`
9. **nested-object has fields**: Every `nested-object` bind includes explicit `fields` enumeration

### No-Guessing Tests (ADR-054 Section 2b)

10. **Complex types have render_as**: For every bind, if schema type at path is object or array, `render_as` MUST be present
11. **No paragraph on complex types**: `render_as: paragraph` on an object or array type is a test failure
12. **card-list sub-fields specified**: Every field inside a `card.fields` array has its own `render_as` declaration
13. **Level 2 coverage achieved**: IA coverage report shows 100% of binds at Level 2 for TA

### Coverage Report

14. **Coverage report generated**: Golden contract tests produce a coverage report artifact for TA showing total binds, Level 2 count, percentage, and any violations

### TA-Specific

9. **TA has correct tabs**: detail_html defines tabs for Overview, Workflows, Components, Data Models, API Interfaces
10. **Workflows tab uses card-list**: Workflows section binds with `render_as: card-list` including sub-fields for description, triggers, steps, outputs
11. **Components tab uses card-list**: Components section binds with `render_as: card-list` with appropriate sub-fields
12. **Data Models tab structured**: Data models section uses `card-list` or `table` with field definitions
13. **API Interfaces tab structured**: API interfaces section uses appropriate block types for endpoints

### SPA Renderer

14. **Block renderer exists**: SPA has a component that maps `render_as` to React components
15. **Config-driven tabs**: SPA reads tab structure from IA config, not hardcoded view definitions
16. **All seven render types supported**: Block renderer handles paragraph, list, ordered-list, table, key-value-pairs, card-list, nested-object
17. **Fallback to paragraph**: If `render_as` is omitted, renderer treats field as paragraph (never raw JSON)
18. **card-list renders cards**: card-list fields render as individual cards with title and sub-fields
19. **table renders columns**: table fields render with column headers from definition

---

## Procedure

### Phase 1: Schema Audit

Catalog every field in the TA schema:
- Field name, type (string/array/object), nesting depth
- For arrays: element type (string vs object, and if object, its sub-fields)
- For objects: property names and types
- Classify each as: paragraph, list, ordered-list, table, key-value-pairs, card-list, or nested-object

This audit drives the IA definition. Do not write IA without completing it.

### Phase 2: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-19. Verify all fail.

For criteria 1-8: unit tests that load package.yaml and validate against schema.
For criteria 9-13: assertions on TA package.yaml content.
For criteria 14-19: Mode B acceptable if no React test harness (grep-based source inspection for component existence and render_as mapping).

### Phase 3: Implement

1. Write `information_architecture` section in TA package.yaml with full block model for every field
2. Write `rendering.detail_html` with tab definitions (Overview, Workflows, Components, Data Models, API Interfaces)
3. Write `rendering.pdf.linear_order` for future consumption
4. Build SPA block renderer component that maps `render_as` -> React component
5. Build SPA section renderer that iterates section binds and invokes block renderer
6. Build SPA tab renderer that groups sections into tabs from config
7. Wire document detail view to consume IA config from API response (rendering_config)
8. Remove or bypass hardcoded TechnicalArchitectureViewer in favor of config-driven rendering

### Phase 4: Verify

1. All Tier 1 tests pass
2. TA renders in browser with correct tabs and all fields using declared block types
3. No raw JSON displayed for any field
4. Tier 0 returns zero

---

## Prohibited Actions

- Do not implement PDF rendering (that is WS-PDF-001)
- Do not modify TA schema or LLM prompts
- Do not add render_as types beyond the pinned vocabulary without ADR-054 amendment
- Do not modify floor view rendering
- Do not hardcode TA-specific rendering logic (the block renderer must be generic)

---

## Verification Checklist

- [ ] Schema audit complete -- all TA fields cataloged with types and nesting
- [ ] All new Tier-1 tests fail before implementation
- [ ] IA added to TA package.yaml with full block model
- [ ] Every TA field has a declared render_as type
- [ ] detail_html rendering spec with 5 tabs
- [ ] pdf linear_order defined
- [ ] SPA block renderer supports all 7 render types
- [ ] SPA renders TA tabs from config (no hardcoded view)
- [ ] No raw JSON displayed for any field
- [ ] Golden contract tests pass for TA
- [ ] All new Tier-1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-IA-003_



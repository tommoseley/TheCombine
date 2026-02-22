# WS-IA-001: Information Architecture Definitions + SPA Tab Restoration

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

Add `information_architecture` and `rendering.detail_html` definitions to Tier-1 document types, starting with Technical Architecture. Update the SPA to render tabs and sections from package.yaml instead of hardcoded view definitions. Add golden contract tests that enforce alignment between IA, schema, and rendered HTML sections.

Deliverable: Tabs are back and governed. Drift is caught by tests.

---

## Preconditions

- ADR-054 accepted
- Tier-1 document types exist in combine-config/document_types/
- SPA renders document detail views

---

## Scope

### In Scope

- Add `information_architecture` section to package.yaml for Technical Architecture
- Add `rendering.detail_html` section to package.yaml for Technical Architecture
- Extend to other Tier-1 document types (PD, IPP, IPF) after TA proves the pattern
- Update SPA renderer to consume IA from package.yaml (or API-served config)
- Restore TA tabs: workflows, components, data models, API interfaces
- Golden contract tests: IA binds exist in schema, required fields covered, HTML sections reference declared IDs

### Out of Scope

- PDF rendering (WS-PDF-001)
- Floor view changes
- Mobile rendering
- UX AI integration
- New document types

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

### Golden Contract Tests (per document type)

1. **Binds exist in schema**: Every `binds` path in IA sections resolves to a valid schema field
2. **Required fields covered**: Every schema-required field appears in at least one IA section
3. **HTML sections valid**: Every section referenced in `rendering.detail_html` tabs exists in IA sections
4. **No orphaned sections**: No IA section is unreferenced by any rendering target

### TA-Specific

5. **TA has four tabs**: detail_html defines tabs for workflows, components, data models, API interfaces
6. **TA tabs render**: SPA produces tab elements matching declared tab IDs when rendering TA document

### SPA Renderer

7. **Config-driven tabs**: SPA reads tab structure from IA config, not hardcoded view definitions
8. **Section content bound**: Each tab section renders content from the bound schema fields

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-8. Verify all fail.

For criteria 1-4: unit tests that load package.yaml and validate against schema.
For criteria 5-6: assertions on TA package.yaml content.
For criteria 7-8: Mode B acceptable if no React test harness (grep-based source inspection).

### Phase 2: Implement

1. Add `information_architecture` and `rendering.detail_html` to TA package.yaml
2. Define TA tabs: workflows, components, data models, API interfaces with correct binds
3. Update SPA document detail renderer to consume IA config
4. Remove or bypass hardcoded TA view definition in favor of config-driven rendering
5. Repeat for PD, IPP, IPF if time permits (or defer to follow-up WS)

### Phase 3: Verify

1. All Tier 1 tests pass
2. TA renders with correct tabs in browser
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not implement PDF rendering (that is WS-PDF-001)
- Do not modify document schemas
- Do not modify LLM prompts
- Do not introduce a layout DSL beyond what ADR-054 defines
- Do not modify floor view rendering

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] IA added to TA package.yaml
- [ ] detail_html rendering spec added to TA package.yaml
- [ ] SPA renders TA with four tabs from config
- [ ] Golden contract tests pass for TA
- [ ] No hardcoded TA tab structure remains in SPA
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-IA-001_

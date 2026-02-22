# WS-IA-002: Extend Information Architecture to Remaining Tier-1 Document Types

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

Apply the IA pattern proven by WS-IA-001 (Technical Architecture) to the remaining Tier-1 document types: Project Discovery, Implementation Plan Primary (IPP), and Implementation Plan (IPF). Each gets `information_architecture` and `rendering.detail_html` in its package.yaml. SPA renders all four from config. Golden contract tests cover all four.

---

## Preconditions

- WS-IA-001 complete (TA has IA, SPA renders tabs from config, golden contract tests pass)
- Pattern proven: package.yaml structure, SPA consumption, test approach all established

---

## Scope

### In Scope

- Add `information_architecture` + `rendering.detail_html` to:
  - Project Discovery (project_discovery)
  - Implementation Plan Primary (implementation_plan_primary)
  - Implementation Plan (implementation_plan)
- Golden contract tests for each (same pattern as TA)
- SPA renders tabs/sections from config for all three
- Add `rendering.pdf.linear_order` to each (consumed by WS-PDF-001 when it executes)

### Out of Scope

- Technical Architecture (done in WS-IA-001)
- PDF rendering implementation (WS-PDF-001)
- Concierge Intake (not a Tier-1 production document)
- Work Package / Work Statement document types (future)
- Floor view changes

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

Per document type (PD, IPP, IPF):

1. **Binds exist in schema**: Every `binds` path in IA sections resolves to a valid schema field
2. **Required fields covered**: Every schema-required field appears in at least one IA section
3. **HTML sections valid**: Every section in `rendering.detail_html` tabs references a declared section ID
4. **No orphaned sections**: No IA section is unreferenced by any rendering target
5. **PDF linear order valid**: Every entry in `rendering.pdf.linear_order` references a declared section ID

Cross-cutting:

6. **SPA renders all four types from config**: PD, IPP, IPF, and TA all render tabs from package.yaml (no hardcoded view definitions for any of the four)
7. **Contract tests pass for all four**: Golden contract test suite covers TA + PD + IPP + IPF

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Extend golden contract test suite to cover PD, IPP, IPF (criteria 1-5 per type). Verify all fail.

### Phase 2: Implement

1. Refactor FullDocumentViewer to render tabs from `rendering_config` when present in the render model response. Extract the config-driven rendering logic from TechnicalArchitectureViewer.jsx into the generic path. After this step, any document type with `rendering_config.detail_html` in its render model response gets tabbed rendering automatically -- no per-type SPA code required.
2. Define IA sections for Project Discovery (identify tabs, map binds to schema fields). Add `information_architecture`, `rendering.detail_html`, and `rendering.pdf` to package.yaml.
3. Define IA sections for IPP (identify tabs, map binds). Add `information_architecture`, `rendering.detail_html`, and `rendering.pdf` to package.yaml.
4. Define IA sections for IPF (identify tabs, map binds). Add `information_architecture`, `rendering.detail_html`, and `rendering.pdf` to package.yaml.

### Phase 3: Verify

1. All Tier 1 tests pass
2. All four document types render with correct tabs in browser
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify TA IA (that is WS-IA-001)
- Do not implement PDF rendering (that is WS-PDF-001)
- Do not modify document schemas or LLM prompts
- Do not hardcode view definitions for these types

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] IA added to PD package.yaml
- [ ] IA added to IPP package.yaml
- [ ] IA added to IPF package.yaml
- [ ] detail_html and pdf rendering specs added to all three
- [ ] SPA renders all three from config
- [ ] Golden contract tests pass for all four Tier-1 types
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-IA-002_

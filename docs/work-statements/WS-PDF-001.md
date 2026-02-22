# WS-PDF-001: PDF Export Pipeline (IA-Driven)

## Status: Accepted

## Governing References

- ADR-054 -- Governed Information Architecture with HTML and PDF Targets
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- combine-config/document_types/
- app/api/
- app/domain/services/
- spa/src/
- tests/

---

## Objective

Implement PDF export for Combine documents, consuming the same IA sections and `rendering.pdf.linear_order` defined in package.yaml. PDF output must follow declared section ordering with deterministic headings and optional TOC. No invented structure.

Deliverable: PDF exports exist and follow IA.

---

## Preconditions

- ADR-054 accepted
- WS-IA-001 complete (IA definitions exist in package.yaml for at least TA)
- `rendering.pdf` section defined in package.yaml for target document types

---

## Scope

### In Scope

- Decide PDF generation approach (server-side vs client-side; CSS-to-PDF vs direct PDF library)
- Add `rendering.pdf` section to package.yaml for TA (and other Tier-1 types if IA exists)
- Implement PDF generation endpoint or client-side export
- Linearize sections per `pdf.linear_order`
- Generate deterministic heading structure from section labels
- Optional TOC when `toc: true`
- Basic styling (readable, professional, not elaborate)
- API endpoint: `GET /api/v1/documents/{id}/export/pdf` (or equivalent)
- UI affordance: export/download button on document detail view

### Out of Scope

- Elaborate PDF styling or branding
- Project Binder (multi-document aggregation)
- Mobile rendering
- Floor view changes
- Custom fonts or complex layout

---

## Design Decision: PDF Approach

To be determined during implementation. Options:

**A. Server-side with WeasyPrint or similar**
- Render HTML from IA sections, convert to PDF server-side
- Pro: consistent output regardless of browser
- Con: additional server dependency

**B. Server-side with reportlab or fpdf2**
- Build PDF directly from section data
- Pro: no HTML intermediate, full control
- Con: more code for layout

**C. Client-side with browser print / jsPDF**
- Generate from rendered HTML in browser
- Pro: no server dependency
- Con: browser-dependent output, harder to test

Recommendation: decide during Phase 2 based on what produces acceptable output fastest. Document choice in session log.

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

### PDF Contract Tests

1. **PDF linear order matches IA**: Generated PDF section order matches `rendering.pdf.linear_order` from package.yaml
2. **All sections present**: Every section in `linear_order` appears in the PDF output
3. **No invented sections**: PDF contains no sections absent from IA declaration
4. **TOC present when enabled**: If `toc: true`, PDF includes a table of contents
5. **Deterministic headings**: Section headings in PDF match section labels from IA

### Integration

6. **Export endpoint exists**: `GET /api/v1/documents/{id}/export/pdf` returns PDF content type
7. **UI export button**: Document detail view includes a PDF export/download affordance
8. **Golden contract**: `rendering.pdf.linear_order` entries all reference declared section IDs (reuse WS-IA-001 pattern)

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-8. Verify all fail.

For criteria 1-5: unit tests that generate PDF from test data and validate structure.
For criterion 6: route test asserting endpoint exists and returns correct content type.
For criterion 7: Mode B acceptable (grep-based SPA inspection) if no React test harness.
For criterion 8: unit test loading package.yaml and validating references.

### Phase 2: Implement

1. Add `rendering.pdf` section to TA package.yaml (linear_order, toc flag)
2. Choose PDF generation approach and document decision
3. Implement PDF generation service consuming IA sections
4. Implement API endpoint for PDF export
5. Add export button to SPA document detail view
6. Style PDF for readability (headings, spacing, page breaks between major sections)

### Phase 3: Verify

1. All Tier 1 tests pass
2. Export a TA document to PDF -- verify sections, order, headings
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not invent PDF structure beyond what IA declares
- Do not modify document schemas or LLM prompts
- Do not build Project Binder (multi-document export) -- future scope
- Do not implement elaborate branding or custom fonts for MVP
- Do not modify IA definitions (consume what WS-IA-001 established)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] PDF approach chosen and documented
- [ ] rendering.pdf added to TA package.yaml
- [ ] PDF generation service implemented
- [ ] API endpoint returns PDF
- [ ] PDF sections match linear_order
- [ ] TOC present when enabled
- [ ] No invented sections in PDF
- [ ] UI export button exists
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-PDF-001_

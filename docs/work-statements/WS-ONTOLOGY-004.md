# WS-ONTOLOGY-004: Replace IPP Epic Output with Work Package Candidates

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A (with Mode B clause for semantic quality)

---

## Decision Pinned

Epics removed from IPP. IPP outputs only `work_package_candidates[]`. No dual pipeline.

---

## Objective

Update the IPP (Implementation Plan Primary) document type to emit Work Package candidates instead of Epic candidates. Update schema, prompt, and validation accordingly.

---

## Preconditions

- WS-ONTOLOGY-001 complete (Work Package document type exists)
- Current IPP schema and prompt are known and accessible
- Tier 0 harness operational

---

## Scope

### Includes

- Update IPP output schema: replace `epic_candidates[]` with `work_package_candidates[]`
- Update IPP task prompt to produce WP candidates
- Define required WP candidate fields
- Schema validation enforcement
- Golden trace test (structural)

### Excludes

- IPF reconciliation changes (WS-ONTOLOGY-005)
- Epic removal from runtime (WS-ONTOLOGY-006)
- Semantic quality tuning of WP candidate generation (tracked as Mode B)

---

## Tier 1 Verification Criteria (Mode A)

All tests must fail before implementation and pass after.

1. **Schema updated**: IPP output schema defines `work_package_candidates[]` with required fields:
   - `candidate_id` (string, e.g., "WPC-001")
   - `title` (string, non-empty)
   - `rationale` (string, non-empty)
   - `scope_in[]` (list of strings)
   - `scope_out[]` (list of strings)
   - `dependencies[]` (list of candidate_id references)
   - `definition_of_done[]` (list of strings)
   - `governance_notes[]` (list of strings, optional)
2. **No epic_candidates field**: IPP output schema does not contain `epic_candidates` at any level
3. **Schema validation passes**: A representative IPP output with valid WP candidates passes schema validation
4. **Schema validation rejects invalid**: An IPP output with missing required WP candidate fields fails validation
5. **Golden trace test**: Given a fixed representative input, the IPP prompt produces output containing at least one WP candidate with all required fields populated (structural check only -- content quality is Mode B)

---

## Mode B Clause (Semantic Quality)

The quality of WP candidate content (rationale depth, scope precision, DoD measurability) requires human review until sufficient outputs have been evaluated.

- Human approval required before WP candidates proceed to IPF reconciliation
- Approval decision recorded in Project Logbook
- This Mode B clause has a mechanization plan: after N successful human approvals (suggested: 5), evaluate whether a semantic validation rubric can replace human review

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all five Mode A Tier 1 criteria. Verify all tests fail.

### Phase 2: Implement

1. Update IPP output schema:
   - Remove `epic_candidates[]`
   - Add `work_package_candidates[]` with all required fields
2. Update IPP task prompt:
   - Replace epic generation instructions with WP candidate generation
   - Include field definitions and examples in prompt
3. Update schema validation logic
4. Update any handler code that processes IPP output

### Phase 3: Verify

1. All Mode A Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not retain `epic_candidates` in any form (no fallback, no dual output)
- Do not modify IPF schema or prompt (that is WS-ONTOLOGY-005)
- Do not remove Epic document types from runtime (that is WS-ONTOLOGY-006)
- Do not attempt to tune prompt for semantic quality (Mode B -- handle through human review)

---

## Verification Checklist

- [ ] All Mode A Tier 1 tests fail before implementation
- [ ] IPP schema defines `work_package_candidates[]` with all required fields
- [ ] No `epic_candidates` field exists in schema
- [ ] Schema validation passes for valid WP candidate output
- [ ] Schema validation rejects invalid output
- [ ] Golden trace produces structurally valid WP candidates
- [ ] All Mode A Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero
- [ ] Mode B clause documented: human approval required for semantic quality

---

_End of WS-ONTOLOGY-004_

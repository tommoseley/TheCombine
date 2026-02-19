# WS-ONTOLOGY-005: Update IPF to Reconcile and Commit Work Packages

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A (with Mode B clause for reconciliation quality)

---

## Objective

Update the IPF (Implementation Plan Final) document type to accept WP candidates from IPP and reconcile them into committed Work Package documents using the existing kept/split/merge/dropped pattern.

---

## Preconditions

- WS-ONTOLOGY-001 complete (Work Package document type exists)
- WS-ONTOLOGY-004 complete (IPP outputs `work_package_candidates[]`)
- Current IPF schema and prompt are known and accessible
- Tier 0 harness operational

---

## Scope

### Includes

- Update IPF input expectations to accept WP candidates
- Update IPF output schema to produce `work_packages[]` and `candidate_reconciliation[]`
- Update IPF task prompt for WP reconciliation
- Implement governance pinning on WP instantiation
- Reconciliation supports kept/split/merge/dropped with traceability

### Excludes

- Epic removal (WS-ONTOLOGY-006)
- Production Floor rendering (WS-ONTOLOGY-007)
- Advanced governance mutation automation

---

## Tier 1 Verification Criteria (Mode A)

All tests must fail before implementation and pass after.

1. **IPF accepts WP candidates**: IPF input schema expects `work_package_candidates[]` from IPP
2. **IPF produces committed WPs**: Output contains `work_packages[]` with each WP having a unique ID, title, and all fields from the WP document schema
3. **Reconciliation entries**: Output contains `candidate_reconciliation[]` with entries of type `kept`, `split`, `merged`, or `dropped`, each referencing source `candidate_id`(s)
4. **Bidirectional traceability**: Every committed WP traces back to source WP candidate(s); every WP candidate traces forward to its reconciliation outcome
5. **Governance pinning**: Each committed WP includes `governance_pins` with at least `ta_version_id` populated (adr_ids[] may be empty initially)
6. **Committed WPs are instantiated**: Reconciliation produces actual WP documents in the document store (not just schema output)

---

## Mode B Clause (Reconciliation Quality)

The quality of reconciliation decisions (whether to keep, split, merge, or drop candidates) requires human review.

- Human approval required before committed WP state moves to READY
- Approval decision recorded in Project Logbook
- Mechanization plan: after N successful reconciliations (suggested: 5), evaluate whether reconciliation logic can be validated by schema rules or deterministic checks

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all six Mode A Tier 1 criteria. Verify all tests fail.

Test approach for reconciliation: use synthetic WP candidate inputs representing each scenario (straight keep, split one into two, merge two into one, drop one). Assert output structure and traceability.

### Phase 2: Implement

1. Update IPF input schema to expect `work_package_candidates[]`
2. Update IPF output schema:
   - `work_packages[]` (committed WPs)
   - `candidate_reconciliation[]` (kept/split/merged/dropped entries)
3. Update IPF task prompt for WP reconciliation
4. Implement governance pinning on WP document creation:
   - Capture current TA version ID
   - Capture applicable ADR IDs (may be empty initially)
5. Implement WP document instantiation from reconciliation output
6. Ensure bidirectional traceability fields populated

### Phase 3: Verify

1. All Mode A Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not retain epic reconciliation logic or schema fields
- Do not modify IPP schema or prompt (that was WS-ONTOLOGY-004)
- Do not remove Epic document types (that is WS-ONTOLOGY-006)
- Do not implement advanced reconciliation heuristics beyond the existing pattern
- Do not skip governance pinning

---

## Verification Checklist

- [ ] All Mode A Tier 1 tests fail before implementation
- [ ] IPF accepts WP candidates as input
- [ ] IPF produces `work_packages[]` and `candidate_reconciliation[]`
- [ ] Reconciliation supports kept/split/merge/dropped
- [ ] Bidirectional traceability preserved
- [ ] Governance pins populated on committed WPs
- [ ] Committed WPs instantiated as documents
- [ ] All Mode A Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero
- [ ] Mode B clause documented: human approval before WP moves to READY

---

_End of WS-ONTOLOGY-005_

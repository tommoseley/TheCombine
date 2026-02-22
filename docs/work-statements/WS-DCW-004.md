# WS-DCW-004: Remove Remaining Epic/Feature References from Runtime

## Status: Accepted

## Parent Work Package: WP-DCW-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-052 -- Document Pipeline WP/WS Integration

## Verification Mode: A

## Allowed Paths

- app/
- seed/
- tests/
- spa/src/

---

## Objective

Audit the entire runtime codebase and eliminate all remaining references to Epic and Feature as document types, entity types, or ontology concepts. WS-ONTOLOGY-006 removed handlers and registrations but the POW definition and potentially other code still carried references. After WS-DCW-003 rewrites the POW, this WS cleans up anything that survived.

---

## Preconditions

- WS-DCW-003 complete (POW rewritten to WP/WS)
- WS-ONTOLOGY-006 complete (epic/feature handlers, BFF, templates deleted)

---

## Scope

### In Scope

- Grep-based audit of app/, seed/, spa/src/, tests/ for "epic", "feature", "Epic", "Feature"
- Remove or replace references that pertain to the old document type ontology
- Preserve references that are legitimate domain vocabulary (e.g., "feature" as a product capability in prose, BCP hierarchy level names)

### Out of Scope

- docs/ (ADRs, session logs, work statements reference epics historically -- that is correct)
- recycle/ (already deprecated)
- BCP pipeline hierarchy level names using "epic"/"feature" as vocabulary (intentional per WS-ONTOLOGY-006 decision)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **No epic document type references**: grep of app/ and seed/ for "epic" as a document type, handler, or entity type returns zero matches (excluding BCP hierarchy level vocabulary)
2. **No feature document type references**: grep of app/ and seed/ for "feature" as a document type, handler, or entity type returns zero matches (excluding BCP hierarchy level vocabulary)
3. **No SPA epic references**: grep of spa/src/ for Epic/Feature component names, CSS classes, or constant names returns zero matches
4. **No stale imports**: No import statements reference deleted epic/feature modules
5. **Existing tests pass**: No regressions

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write grep-based audit tests asserting criteria 1-4. Verify they fail (references still exist).

### Phase 2: Audit

Run comprehensive grep across codebase. Classify each hit as:
- **Remove**: old ontology reference
- **Keep**: legitimate domain vocabulary (BCP hierarchy, prose, comments)

Report classification for review before removing.

### Phase 3: Implement

Remove all references classified as "Remove". Do not touch "Keep" references.

### Phase 4: Verify

1. All Tier 1 tests pass
2. Existing tests pass
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not remove BCP hierarchy level names that legitimately use "epic"/"feature" as vocabulary
- Do not modify docs/ (historical references are correct)
- Do not modify recycle/ (already deprecated)
- Do not change handler logic beyond removing dead references

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] Audit report produced with classification
- [ ] All "Remove" references eliminated
- [ ] All "Keep" references justified
- [ ] No stale imports
- [ ] All Tier 1 tests pass after implementation
- [ ] Existing tests pass
- [ ] Tier 0 returns zero

---

_End of WS-DCW-004_

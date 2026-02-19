# WS-ONTOLOGY-006: Remove Epic/Feature Pipeline Entirely

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A

---

## Objective

Remove all Epic and Feature document types, schemas, and references from the Combine runtime. After this WS, the system has no concept of Epics or Features. Work Packages and Work Statements are the only execution hierarchy.

---

## Preconditions

- WS-ONTOLOGY-004 complete (IPP outputs WP candidates, not epic candidates)
- WS-ONTOLOGY-005 complete (IPF reconciles WP candidates, not epic candidates)
- Tier 0 harness operational

---

## Scope

### Includes

- Remove Epic document type registration
- Remove Feature document type registration (if it exists as separate type)
- Remove Epic/Feature schemas from seed/schemas/
- Remove Epic/Feature references from IPP/IPF schemas and prompts
- Remove any Epic/Feature-specific API endpoints or handlers
- Remove Epic/Feature-specific test files
- Guard tests ensuring no Epic/Feature references remain

### Excludes

- Production Floor UI changes (WS-ONTOLOGY-007)
- Historical data migration (existing Epic documents remain in database as historical artifacts)
- Modification of session logs or ADR documents that reference Epics historically

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Epic doc type rejected**: Attempting to create a document with `doc_type_id = epic` fails with a clear error
2. **Feature doc type rejected**: Attempting to create a document with `doc_type_id = feature` fails (if feature was a registered type)
3. **No Epic schemas in seed**: No files in `seed/schemas/` reference epic or feature document types
4. **No Epic references in IPP/IPF**: IPP and IPF schemas, prompts, and handler code contain no references to `epic_candidates`, `epic`, or `feature` as document types
5. **No Epic-specific API endpoints**: No route registrations for Epic/Feature-specific operations
6. **Regression guard**: A grep-based test confirms no source files in `app/` or `seed/` contain epic document type registrations or epic-specific handler logic (excluding comments, logs, and historical documentation)

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all six Tier 1 criteria. Verify all tests fail because Epic types still exist.

Note: Some tests may partially pass if Epic was never a formally registered document type. In that case, the test confirms the condition is already met, and the test serves as a regression guard.

### Phase 2: Implement

1. Remove Epic document type registration (if registered)
2. Remove Feature document type registration (if registered)
3. Remove Epic/Feature schema files from seed/schemas/
4. Remove any Epic/Feature references from IPP/IPF handler code
5. Remove any Epic/Feature-specific API routes
6. Remove any Epic/Feature-specific test files (not the guard tests -- those stay)
7. Clean up any imports referencing removed modules

### Phase 3: Verify

1. All Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not delete historical Epic documents from the database (they are historical artifacts)
- Do not modify session logs or ADR documents that reference Epics historically
- Do not modify Production Floor UI (that is WS-ONTOLOGY-007)
- Do not modify Work Package or Work Statement document types

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation (or confirm condition already met for regression guards)
- [ ] Epic document type cannot be created
- [ ] Feature document type cannot be created
- [ ] No Epic/Feature schemas in seed/
- [ ] No Epic/Feature references in IPP/IPF code
- [ ] No Epic-specific API endpoints
- [ ] Regression guard passes (no epic type references in app/ or seed/)
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-ONTOLOGY-006_

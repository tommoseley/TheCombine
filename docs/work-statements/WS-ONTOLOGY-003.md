# WS-ONTOLOGY-003: Project Logbook MVP + Transactional Auto-Append on WS Acceptance

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A

---

## Decision Pinned

Project Logbook is a document in the existing document store. Logbook append occurs in the WS acceptance service as an atomic operation. If the append fails, the WS acceptance rolls back. No eventual consistency.

---

## Objective

Introduce Project Logbook as a first-class document type. Auto-append a structured entry whenever a Work Statement transitions to ACCEPTED. The logbook is append-only and serves as the project's auditable record of verified state transitions.

---

## Preconditions

- WS-ONTOLOGY-001 complete (Work Package document type exists)
- WS-ONTOLOGY-002 complete (Work Statement document type exists with acceptance lifecycle)
- Tier 0 harness operational

---

## Scope

### Includes

- Register `doc_type_id = project_logbook` in the document type system
- Define logbook document schema with structured header and entry list
- Implement transactional append on WS acceptance
- Rollback WS acceptance if logbook append fails
- Append-only enforcement (no update/delete on entries)

### Excludes

- Logbook rendering in Production Floor UI (WS-ONTOLOGY-007 or future WS)
- Advanced analytics derived from logbook entries
- Program-level logbooks

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Document type registration**: `project_logbook` is a registered document type
2. **Logbook header fields**: Header includes:
   - `schema_version` (string, e.g., "1.0")
   - `project_id` (reference to owning project)
   - `mode_b_rate` (float, computed or cached)
   - `verification_debt_open` (integer count)
   - `program_ref` (nullable, for future program-level grouping)
3. **Auto-append on WS acceptance**: When a WS transitions to ACCEPTED, a logbook entry is appended containing:
   - `timestamp` (ISO 8601)
   - `ws_id` (reference to accepted WS)
   - `parent_wp_id` (reference to parent WP)
   - `result` (ACCEPTED)
   - `mode_b_list[]` (any Mode B items in this WS)
   - `tier0_json` (Tier 0 JSON summary blob or pointer)
4. **Atomicity**: If logbook append fails, WS acceptance is rolled back (WS remains IN_PROGRESS)
5. **Append-only**: No API endpoint allows updating or deleting logbook entries
6. **Logbook created on project bootstrap**: Each project gets a logbook document when it is created (or on first WS acceptance, whichever is simpler -- implementer decides)

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all six Tier 1 criteria. Verify all tests fail.

### Phase 2: Implement

1. Register `project_logbook` document type
2. Define schema with header fields and entries list
3. Implement logbook creation (on project bootstrap or lazy on first append)
4. Modify WS acceptance service to:
   a. Transition WS to ACCEPTED
   b. Append logbook entry
   c. Wrap both in a transaction -- rollback on failure
5. Ensure no update/delete endpoints exist for logbook entries
6. Update WP ws_done rollup (from WS-ONTOLOGY-002) remains part of the same transaction

### Phase 3: Verify

1. All Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not allow logbook entry modification or deletion
- Do not implement eventual consistency -- append must be transactional with WS acceptance
- Do not create separate logbook rendering UI (future scope)
- Do not modify IPP/IPF schemas or prompts
- Do not modify WP or WS document type schemas (beyond what is needed for the acceptance flow)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] `project_logbook` document type registered
- [ ] Header fields present and correct
- [ ] WS acceptance appends logbook entry with all required fields
- [ ] Logbook append failure rolls back WS acceptance
- [ ] No update/delete endpoints for logbook entries
- [ ] Logbook created for project
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-ONTOLOGY-003_

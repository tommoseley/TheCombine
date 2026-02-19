# WS-ONTOLOGY-002: Add Work Statement Document Type + Parent Enforcement

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A

---

## Decision Pinned

Work Statement is a document in the existing document store. Every WS must reference a parent Work Package. No orphan Work Statements.

---

## Objective

Introduce Work Statement as a first-class document type with parent WP enforcement, lifecycle state machine, and automatic WP rollup updates on registration.

---

## Preconditions

- WS-ONTOLOGY-001 complete (Work Package document type exists)
- Tier 0 harness operational

---

## Scope

### Includes

- Register `doc_type_id = work_statement` in the document type system
- Define WS document schema with parent_wp_id as required field
- Implement WS lifecycle state machine
- Registration logic: creating a WS updates parent WP rollup and child refs
- Governance pin inheritance from parent WP at creation time

### Excludes

- Project Logbook integration (WS-ONTOLOGY-003)
- IPP/IPF changes (WS-ONTOLOGY-004/005)
- Production Floor rendering (WS-ONTOLOGY-007)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Document type registration**: `work_statement` is a registered document type
2. **Parent required**: Creating a WS without `parent_wp_id` fails with a clear error
3. **Parent must exist**: Creating a WS with a non-existent `parent_wp_id` fails
4. **WP rollup updated on registration**: Creating a WS increments parent WP `ws_total` and appends to `ws_child_refs[]`
5. **Valid lifecycle transitions accepted**:
   - DRAFT ? READY
   - READY ? IN_PROGRESS
   - IN_PROGRESS ? ACCEPTED
   - IN_PROGRESS ? REJECTED
   - IN_PROGRESS ? BLOCKED
   - BLOCKED ? IN_PROGRESS (unblock)
6. **Invalid lifecycle transitions rejected**:
   - DRAFT ? ACCEPTED (skip)
   - ACCEPTED ? anything (terminal)
   - REJECTED ? anything (terminal)
7. **Governance pins inherited**: WS created under a WP inherits the WP's `governance_pins` (ta_version_id, adr_ids[])
8. **WP progress reflects WS states**: When a WS transitions to ACCEPTED, parent WP `ws_done` increments

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all eight Tier 1 criteria. Verify all tests fail.

### Phase 2: Implement

1. Register `work_statement` document type
2. Define schema with `parent_wp_id` as required field
3. Implement parent existence validation on create
4. Implement WP rollup update on WS creation (increment ws_total, append child ref)
5. Implement lifecycle state machine with transition validation
6. Implement governance pin inheritance from parent WP
7. Implement ws_done increment on WS acceptance

### Phase 3: Verify

1. All Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not allow WS creation without a parent WP
- Do not modify the Work Package document type schema (beyond rollup field updates)
- Do not implement Project Logbook logic (WS-ONTOLOGY-003)
- Do not modify IPP/IPF schemas or prompts
- Do not add Production Floor rendering

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] `work_statement` document type registered
- [ ] Parent WP required and validated
- [ ] WP rollup updates on WS creation
- [ ] Lifecycle state machine enforces valid/invalid transitions
- [ ] Governance pins inherited from parent WP
- [ ] WP ws_done increments on WS acceptance
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-ONTOLOGY-002_

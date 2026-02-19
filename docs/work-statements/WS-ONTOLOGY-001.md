# WS-ONTOLOGY-001: Add Work Package Document Type (Document-Native)

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A

---

## Decision Pinned

Work Package is a document in the existing document store. It uses the same document infrastructure as all other Combine artifacts (Project Discovery, Technical Architecture, etc.). No parallel domain layer.

---

## Objective

Introduce Work Package as a first-class document type with identity, state machine, dependency tracking, governance pins, and child WS references.

---

## Preconditions

- Existing document store and document type registration infrastructure operational
- Tier 0 harness operational

---

## Scope

### Includes

- Register `doc_type_id = work_package` in the document type system
- Define WP document schema
- Implement state machine with transition enforcement
- API endpoints for create/read/update via existing document APIs

### Excludes

- Work Statement document type (WS-ONTOLOGY-002)
- Progress rollup calculation (deferred until WS registration in 002)
- Production Floor rendering (WS-ONTOLOGY-007)
- IPP/IPF integration (WS-ONTOLOGY-004/005)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Document type registration**: `work_package` is a registered document type
2. **Schema fields present**: WP document includes all required fields:
   - `wp_id` (unique identifier)
   - `title` (string, non-empty)
   - `rationale` (string)
   - `scope_in[]` (list of strings)
   - `scope_out[]` (list of strings)
   - `dependencies[]` (list of WP references)
   - `definition_of_done[]` (list of strings, mechanically evaluable)
   - `state` (enum, default PLANNED)
   - `ws_child_refs[]` (list of WS references, initially empty)
   - `governance_pins` (object with `ta_version_id`, `adr_ids[]`)
3. **Valid state transitions accepted**:
   - PLANNED ? READY
   - READY ? IN_PROGRESS
   - IN_PROGRESS ? AWAITING_GATE
   - AWAITING_GATE ? DONE
4. **Invalid state transitions rejected**:
   - PLANNED ? IN_PROGRESS (skip)
   - DONE ? anything (terminal)
   - IN_PROGRESS ? PLANNED (backward)
5. **CRUD via document APIs**: Can create, read, and update a WP through existing document API patterns
6. **Default rollup fields**: New WP has `ws_total=0`, `ws_done=0`, `mode_b_count=0`

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all six Tier 1 criteria. Verify all tests fail because the work_package document type does not yet exist.

### Phase 2: Implement

1. Register `work_package` document type
2. Define schema with all required fields
3. Implement state machine with transition validation
4. Wire into existing document API endpoints
5. Set default values for rollup fields

### Phase 3: Verify

1. All Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not create a parallel domain layer outside the document store
- Do not implement WS registration logic (that is WS-ONTOLOGY-002)
- Do not modify existing document types
- Do not add Production Floor rendering
- Do not change IPP/IPF schemas or prompts

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] `work_package` document type registered
- [ ] Schema includes all required fields
- [ ] State machine enforces valid transitions and rejects invalid ones
- [ ] CRUD operations work via existing document APIs
- [ ] Default rollup fields correct
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-ONTOLOGY-001_

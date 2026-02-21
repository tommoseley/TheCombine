# WS-SDP-001: Reorder software_product_development POW

## Status: Accepted

## Governing References

- ADR-053 -- Planning Before Architecture in Software Product Development
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- seed/workflows/
- tests/

---

## Purpose

Align `software_product_development` POW node order with ADR-053.

---

## Scope

Modify workflow definition only. No behavioral changes beyond node sequencing.

### Target Order

1. project_discovery
2. implementation_plan_primary
3. implementation_plan
4. technical_architecture
5. (Existing execution fan-out / WS execution nodes)

---

## Constraints

- No schema changes
- No handler modifications
- No prompt changes
- No new document types
- Preserve existing entry/exit edges where possible

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Node execution order**: Assert IPP precedes TA in graph definition
2. **Node execution order**: Assert IPF precedes TA in graph definition
3. **Regression guard**: TA does not precede IPF in graph definition
4. **Existing tests pass**: No regressions introduced
5. **No new workflow validation warnings**: Workflow validates clean

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-3. Verify all fail.

### Phase 2: Implement

Reorder nodes in `software_product_development` workflow definition.

### Phase 3: Verify

1. All Tier 1 tests pass
2. Existing tests pass
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify handlers, schemas, or prompts
- Do not create new document types
- Do not change DCW definitions

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] POW node order matches ADR-053 canonical sequence
- [ ] All Tier 1 tests pass after implementation
- [ ] No workflow validation warnings introduced
- [ ] Existing tests pass
- [ ] Tier 0 returns zero

---

## Expected Blast Radius

Low. Definition-level change only.

---

_End of WS-SDP-001_

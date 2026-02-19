# WS-AWS-DB-005: Destructive Action Guardrails

## Status: Accepted

## Parent Work Package: WP-AWS-DB-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- ops/scripts/
- ops/db/
- tests/

---

## Objective

Prevent accidental destructive database operations (DROP, TRUNCATE, reset, downgrade) by requiring explicit confirmation tied to the target environment. No "oops, nuked dev" moments.

---

## Preconditions

- WS-AWS-DB-003 complete (COMBINE_ENV profiles exist)
- WS-AWS-DB-004 complete (migration/seed scripts exist)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Destructive actions require confirmation**: Any script that performs DROP, TRUNCATE, downgrade, or full reset requires `CONFIRM_ENV=<env_name>` (e.g., `CONFIRM_ENV=dev`) to proceed
2. **Wrong confirmation rejected**: `CONFIRM_ENV=test` when running a dev-targeted script ? fails with clear error
3. **Missing confirmation rejected**: Running a destructive script without CONFIRM_ENV ? fails with clear error explaining what is required
4. **CI guard**: If `CI=true`, destructive commands on dev fail unless explicitly overridden
5. **Non-destructive operations unaffected**: Normal migrations (upgrade) and reads do not require CONFIRM_ENV

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-5. Verify all fail.

### Phase 2: Implement

1. Add guard function/module used by all destructive scripts
2. Guard checks CONFIRM_ENV matches target env
3. Guard checks CI flag for additional protection
4. Integrate guard into migration downgrade, reset, seed-with-truncate, and any future destructive scripts

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not weaken guards for convenience
- Do not allow blanket CONFIRM_ENV=* or CONFIRM_ENV=all
- Do not modify non-destructive script behavior
- Do not change database schemas

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] CONFIRM_ENV required for destructive actions
- [ ] Wrong CONFIRM_ENV rejected
- [ ] Missing CONFIRM_ENV rejected
- [ ] CI guard active
- [ ] Non-destructive operations unaffected
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AWS-DB-005_

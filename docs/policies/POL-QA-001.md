# POL-QA-001: Testing & Verification Standard

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-03-06 |
| **Applies To** | All human and AI contributors executing governed work in The Combine |
| **Related Artifacts** | CLAUDE.md (Bug-First Testing Rule, Testing Strategy), ADR-010, POL-WS-001 |

---

## 1. Purpose

This policy formalizes the testing and verification rules that govern all implementation work in The Combine. These rules ensure that defects are understood before modification, fixes are causally linked to observed failures, and regressions are prevented by construction.

---

## 2. Bug-First Testing Rule

When a runtime error, exception, or incorrect behavior is observed, the following sequence **MUST** be followed:

1. **Reproduce First** -- A failing automated test MUST be written that reproduces the observed behavior. The test must fail for the same reason the runtime behavior failed.
2. **Verify Failure** -- The test MUST be executed and verified to fail before any code changes are made.
3. **Fix the Code** -- Only after the failure is verified may code be modified to correct the issue.
4. **Verify Resolution** -- The test MUST pass after the fix. No fix is considered complete unless the reproducing test passes.

### Constraints

- Tests MUST NOT be written after the fix to prove correctness.
- Code MUST NOT be changed before a reproducing test exists.
- If a bug cannot be reliably reproduced in a test, the issue MUST be escalated rather than patched heuristically.
- Vibe-based fixes are explicitly disallowed.

This rule applies to all runtime defects including: exceptions, incorrect outputs, state corruption, and boundary condition failures.

*Source: CLAUDE.md "Bug-First Testing Rule (Mandatory)"*

---

## 3. Money Tests

Bug fixes MUST include a "money test" that reproduces the exact root-cause scenario:

- The money test MUST fail before the fix is applied.
- The money test MUST pass after the fix is applied.
- The money test serves as the regression guard for that specific defect.

*Source: Established session practice (WS-RING0-001, WP-CRAP-001/002)*

---

## 4. Testing Tiers

All tests operate within the following tier structure:

| Tier | Scope | Dependencies | Purpose |
|------|-------|-------------|---------|
| Tier-1 | In-memory repositories, no DB | None | Pure business logic verification (fast unit tests) |
| Tier-2 | Spy repositories | None | Call contract verification (wiring tests) |
| Tier-3 | Real PostgreSQL | Test DB infrastructure | Integration verification (**deferred**) |

### Tier Constraints

- Tier-3 tests are not currently required. Infrastructure does not yet exist.
- Do NOT suggest SQLite as a substitute for PostgreSQL testing.
- Tier-1 and Tier-2 tests MUST pass before any work is considered complete.

*Source: CLAUDE.md "Testing Strategy (Current)"*

---

## 5. Verification Before Completion

- Work is not complete until all tests pass and acceptance criteria are verified.
- Never mark a task complete without proving it works.
- The standard is "does Tier 0 pass?" -- not "does this look right?"
- Tier 0 verification (`ops/scripts/tier0.sh`) is the mandatory baseline for all work.
- When executing a Work Statement, Tier 0 MUST be invoked in WS mode with `--scope` derived from the WS's `allowed_paths[]`.

*Source: CLAUDE.md "Planning Discipline - Verification Before Done", POL-WS-001 Section 6*

---

## 6. Regression Protection

- Fixes MUST NOT reduce existing test coverage.
- Tests MUST be deterministic -- they MUST NOT depend on external services or non-deterministic inputs.
- Every autonomous bug fix MUST include the test name and root cause in its report.

*Source: CLAUDE.md "Bug-First Testing Rule", "Autonomous Bug Fixing"*

---

## 7. Governance Boundary

This policy formalizes rules already enforced through CLAUDE.md, ADR-010, and established session practices. It does not introduce new rules or enforcement mechanisms. Mechanical enforcement is out of scope and deferred to future quality gate work.

---

*End of Policy*

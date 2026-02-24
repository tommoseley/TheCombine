---
name: autonomous-bug-fix
description: Fix runtime bugs autonomously using the Bug-First Testing Rule. Use when encountering exceptions, incorrect outputs, state corruption, or boundary failures during execution.
---

# Autonomous Bug Fixing

## Bug-First Testing Rule (Mandatory)

When a runtime error, exception, or incorrect behavior is observed, the following sequence **MUST** be followed:

1. **Reproduce First**
   A failing automated test **MUST** be written that reproduces the observed behavior.
   The test must fail for the same reason the runtime behavior failed.

2. **Verify Failure**
   The test **MUST** be executed and verified to fail before any code changes are made.

3. **Fix the Code**
   Only after the failure is verified may code be modified to correct the issue.

4. **Verify Resolution**
   The test **MUST** pass after the fix.
   No fix is considered complete unless the reproducing test passes.

### Constraints

- Tests **MUST NOT** be written after the fix to prove correctness.
- Code **MUST NOT** be changed before a reproducing test exists.
- If a bug cannot be reliably reproduced in a test, the issue **MUST** be escalated rather than patched heuristically.

### Rationale

This rule ensures:

- The defect is understood before modification
- Fixes are causally linked to observed failures
- Regressions are prevented by construction
- Vibe-based fixes are explicitly disallowed

This rule is **non-negotiable** and applies to all runtime defects, including:

- Exceptions
- Incorrect outputs
- State corruption
- Boundary condition failures

## Autonomous Fix Procedure

When a runtime error or incorrect behavior is encountered during WS execution:

- **Do not stop and ask for instructions.** Fix it.
- Follow the Bug-First Testing Rule (see above) autonomously — the same reproduce-first sequence applies.
- **Report what you fixed, not what you found.** Include the test name and root cause.

Escalate only when:

- The bug cannot be reproduced in a test
- The fix would require changes outside the WS `allowed_paths`
- The fix would violate a WS prohibition
- The root cause is ambiguous and multiple fixes are plausible

If the fix is non-trivial (architectural impact, touches multiple modules), write a remediation WS (see WS-DCW-003-RS001 for the pattern) and present it for acceptance before executing.

---
name: ws-execution
description: Execute Work Statements per POL-WS-001. Use when running a WS, starting WS phases, performing Do No Harm audits, or enforcing WS execution discipline.
---

# Work Statement Execution

## POL-WS-001 Enforcement

Per POL-WS-001, AI agents MUST:

1. **Do No Harm audit first**: Before executing any WS, verify its assumptions about the codebase match reality. If assumptions are materially wrong, STOP and report mismatches before touching anything.
2. **Follow Work Statements exactly**: Execute steps in order; do not skip, reorder, or merge
3. **Stop on ambiguity**: If a step is unclear, STOP and escalate rather than infer
4. **Respect prohibited actions**: Each Work Statement defines what is NOT permitted
5. **Verify before proceeding**: Complete verification for each step before moving to the next

## Do No Harm Audit

Before executing any WS:

1. Read the WS in full — preconditions, scope, procedure, prohibited actions
2. Check every file path mentioned in `allowed_paths` — do they exist?
3. Check preconditions — are they met?
4. Check assumptions — does the codebase look like what the WS expects?
5. If any assumption is materially wrong, **STOP and report** before touching code

## Phase Execution Model

Every WS follows this execution pattern:

### Phase 1: Write Failing Tests
- Write tests asserting all Tier 1 verification criteria
- Run tests — all must fail before implementation
- This proves the tests are testing the right thing

### Phase 2: Implement
- Execute the WS procedure steps in order
- Each step must be completed and verified before the next
- If a step fails, stop and assess — do not push through

### Phase 3: Verify
- All Tier 1 tests must pass
- Tier 0 must return zero
- No regressions in existing test suite

## Planning Discipline

### Plan Before Executing

For any non-trivial task (3+ steps or architectural decisions):

- Enter plan mode before writing code
- Write the plan as a WS or remediation WS if one does not already exist
- Get acceptance before executing

If something goes wrong during execution, **STOP and re-plan**. Do not push through a failing approach. Re-planning means escalating to Tom, not silently changing strategy.

### Simplicity First

- Make every change as simple as possible
- Find root causes, not symptoms
- No temporary fixes. No "we'll clean this up later" without a tech debt entry.
- Changes should only touch what is necessary
- If a fix feels hacky, pause and find the elegant solution

### Verification Before Done

- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- The question is not "does this look right?" but "does Tier 0 pass?"

# WS-TIER0-SCOPE-001: Enforce Tier 0 Scope for Work Statement Runs

## Status: Accepted

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- ops/scripts/
- tests/infrastructure/
- docs/policies/
- CLAUDE.md

---

## Purpose

Prevent "false green" Tier 0 runs by requiring and enforcing file-scope boundaries during Work Statement execution. Closes the gap where scope checks exist but are never invoked, producing clean signals when Tier 0 did not validate containment. Also updates execution protocol documentation so executors know to use it.

---

## Preconditions

- Tier 0 harness exists at ops/scripts/tier0.sh
- Tier 0 emits JSON output (schema_version, checks, mode_b, etc.)
- Existing scope logic checks changed files against allowed path prefixes

---

## Scope

### Includes

- WS mode trigger (--ws flag and/or COMBINE_WS_ID env var)
- Mandatory scope enforcement in WS mode
- JSON output includes ws_mode, declared_scope_paths, scope result
- CI guard for WS mode
- Documentation updates: POL-WS-001, WS template format, CLAUDE.md

### Excludes

- Changes to non-scope Tier 0 checks
- Changes to non-WS mode behavior (beyond new JSON fields)
- allowed_paths[] enforcement at WS authoring time (future)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

### Harness Behavior

1. **WS mode requires scope (flag)**: Invoke tier0 with `--ws` and no `--scope` ? exit code non-zero, stderr contains actionable error instructing how to pass scope
2. **WS mode requires scope (env var)**: Invoke tier0 with env `COMBINE_WS_ID=WS-123` and no scope ? fail
3. **WS mode scope PASS**: With scope paths covering the changed-file set, tier0 returns success and JSON shows `checks.scope=PASS`
4. **WS mode scope FAIL**: With at least one changed file outside scope, tier0 fails and JSON shows `checks.scope=FAIL`, stderr lists out-of-scope files
5. **Non-WS mode scope remains SKIPPED**: Run tier0 without `--ws` and without scopes ? does not fail due to scope; JSON includes `ws_mode=false` and `checks.scope=SKIPPED`
6. **JSON contract**: JSON output includes `ws_mode` (boolean), `declared_scope_paths` (array), and `checks.scope` (PASS/FAIL/SKIPPED) in all modes
7. **CI guard**: If `CI=true` and WS mode is active, scope is mandatory with no override unless `ALLOW_SCOPE_SKIP_IN_CI=1` is set

### Documentation

8. **POL-WS-001 updated**: Contains normative requirement: "When executing a Work Statement, Tier 0 MUST be invoked in WS mode with `--scope` prefixes derived from the Work Statement's `allowed_paths[]`."
9. **WS template updated**: `allowed_paths[]` is a standard field in the WS format with instruction tying it to Tier 0 `--scope`
10. **CLAUDE.md updated**: Execution protocol includes required invocation pattern (`--ws` + `--scope` from `allowed_paths`) with concrete example

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-7 in `tests/infrastructure/`. Verify all fail.

Testing tip: Use a deterministic test seam (e.g., `TIER0_CHANGED_FILES_OVERRIDE` env var) to control which files appear as "changed" without depending on real git state. This seam is test-only and must not affect normal behavior unless explicitly set.

### Phase 2: Implement Harness Changes

1. Add `--ws` flag detection
2. Add `COMBINE_WS_ID` env var detection
3. When WS mode active and no scope provided ? FAIL with actionable message
4. When WS mode active, scope check result is always PASS or FAIL (never SKIPPED)
5. Add `ws_mode`, `declared_scope_paths` to JSON output in all modes
6. Add CI guard: `CI=true` + WS mode + no scope ? FAIL unless `ALLOW_SCOPE_SKIP_IN_CI=1`
7. Normalize scope prefixes (consistent trailing `/` handling)

### Phase 3: Verify Harness

1. All tests for criteria 1-7 pass
2. Run Tier 0 in non-WS mode -- must return zero (existing behavior preserved)

### Phase 4: Update Documentation

1. **POL-WS-001**: Add to execution requirements section: "When executing a Work Statement, Tier 0 MUST be invoked in WS mode (e.g., `--ws`) and MUST include `--scope` prefixes derived from the Work Statement's `allowed_paths[]`."
2. **WS template** (in AI.md or canonical format location): Add `allowed_paths[]` as a required field with instruction: "These prefixes are passed to Tier 0 as `--scope` arguments during WS execution."
3. **CLAUDE.md**: Add to execution protocol: "After completing a WS, run: `./ops/scripts/tier0.sh --ws --scope <each allowed_paths prefix>`. If Tier 0 is run in WS mode without `--scope`, it will FAIL by design." Include concrete example with multiple `--scope` entries.

### Phase 5: Final Verification

1. All criteria 1-10 satisfied
2. Run Tier 0 in non-WS mode -- must return zero

---

## Prohibited Actions

- Do not weaken existing Tier 0 checks
- Do not change non-WS mode behavior beyond adding new JSON fields
- Do not silently convert "missing scope" to Mode B in WS mode -- this is a hard fail
- Do not introduce background services or event buses

---

## Verification Checklist

- [ ] All harness tests (criteria 1-7) fail before implementation
- [ ] Harness changes implemented
- [ ] All harness tests pass after implementation
- [ ] Tier 0 non-WS mode returns zero
- [ ] POL-WS-001 contains scope enforcement requirement
- [ ] WS template contains `allowed_paths[]` as standard field
- [ ] CLAUDE.md contains WS execution protocol with `--ws` + `--scope`
- [ ] Tier 0 returns zero (final run)

---

## Demo Package Requirements

Include:
- Tier 0 JSON output from WS mode run with scope (PASS)
- Tier 0 JSON output from WS mode run without scope (FAIL)
- List of files changed
- Confirmation that tests were written first and initially failed

---

_End of WS-TIER0-SCOPE-001_

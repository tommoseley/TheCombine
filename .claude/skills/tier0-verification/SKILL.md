---
name: tier0-verification
description: Run and interpret Tier 0 verification harness results. Use when running tier0.sh, checking test results, or verifying WS completion with scope validation.
---

# Tier 0 Verification

## Commands

```bash
# Standard Tier 0 (pytest + lint + typecheck)
ops/scripts/tier0.sh

# With frontend build check (auto-detects spa/ changes)
ops/scripts/tier0.sh --frontend

# With file scope validation
ops/scripts/tier0.sh --scope app/ tests/

# WS mode — mandatory for Work Statement execution
# Use --scope from the WS's allowed_paths[]:
ops/scripts/tier0.sh --ws --scope ops/scripts/ tests/infrastructure/ docs/policies/ CLAUDE.md

# If Tier 0 is run in WS mode without --scope, it will FAIL by design.
```

## WS Mode

When executing a Work Statement, Tier 0 MUST be run in WS mode:

- `--ws` flag activates Work Statement scope enforcement
- `--scope` must list the WS's `allowed_paths[]`
- If `--ws` is used without `--scope`, Tier 0 fails immediately
- This prevents accidental modifications outside WS boundaries

## Interpreting Results

### Exit Code 0
All checks passed. Safe to proceed.

### Exit Code Non-Zero
One or more checks failed. Review output for:
- **pytest failures**: Test names and assertion errors
- **lint failures**: File paths and rule violations
- **typecheck failures**: Type annotation issues
- **scope violations**: Files modified outside allowed_paths

### Common Issues

- **Frontend build failure**: Run `cd spa && npm run build` to debug
- **Scope violation in WS mode**: You modified files outside the WS `allowed_paths[]` — revert the change
- **Import errors in tests**: Check for circular imports or missing dependencies

## When to Run

- After every WS phase completion
- Before declaring any work complete
- After autonomous bug fixes
- Before session close (final check)

**The question is not "does this look right?" but "does Tier 0 pass?"**

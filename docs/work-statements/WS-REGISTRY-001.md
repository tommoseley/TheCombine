# WS-REGISTRY-001: Canonical Paths & Integrity Gate

## Status: Complete

## Parent Work Package
WP-REGISTRY-001: Registry Integrity & Audit Remediation

## Audit Mapping
| Audit # | Finding | Remediation |
|---------|---------|-------------|
| 1 | Missing task prompt dirs (work_package, work_statement) | Steps 1-2 |
| 2 | Missing global schema dirs (work_package, work_statement) | Steps 3-4 |

## Problem Statement

`active_releases.json` declares `work_package` and `work_statement` in both `tasks` and `schemas` sections, but no global directories exist at:
- `combine-config/prompts/tasks/work_package/`
- `combine-config/prompts/tasks/work_statement/`
- `combine-config/schemas/work_package/` (as released versioned artifacts)
- `combine-config/schemas/work_statement/` (as released versioned artifacts)

The artifacts exist only as package-local files under `combine-config/document_types/{type}/releases/1.0.0/`.

Calling `PackageLoader.get_task("work_package")` or `PackageLoader.get_schema("work_package")` will raise `VersionNotFoundError` at runtime. The system silently relies on the package-local fallback path in `assemble_prompt()` and `resolve_schema_for_package()`.

No gate exists to detect this drift.

## Resolution Design

1. **Populate canonical global paths** by copying from the authoritative package-local artifacts. No semantic changes -- identical content, different location.

2. **Add a Tier-0 integrity check** (Check 6 in `tier0.sh`) that verifies every entry in `active_releases` resolves to an existing artifact at its canonical global path. Missing asset = deterministic HARD_STOP. This runs on every tier0 invocation.

3. **Write Tier-1 tests** that verify `PackageLoader.get_task()` and `PackageLoader.get_schema()` succeed for `work_package` and `work_statement` without fallback.

## Scope

### In Scope
- Create global task prompt directories and populate for work_package and work_statement
- Create global schema directories and populate for work_package and work_statement
- Add Tier-0 integrity check (Check 6) to tier0.sh
- Write Tier-1 tests for resolution success
- Verify all active_releases entries pass integrity check

### Out of Scope
- Removing the package-local fallback in `resolve_schema_for_package()` (future WS -- other doc types still depend on it)
- Semantic changes to task prompts or schemas
- Prompt version bumps
- Changes to other doc types beyond work_package and work_statement

### Prohibited Actions
- Do NOT modify task prompt content (copy only)
- Do NOT modify schema content (copy only)
- Do NOT remove or modify the package-local resolution path yet
- Do NOT bump versions (these are 1.0.0 canonicalization)
- Do NOT run tests -- provide instructions only

---

## Execution Steps

### Step 1: Create global task prompt directories

Create:
```
combine-config/prompts/tasks/work_package/releases/1.0.0/task.prompt.txt
combine-config/prompts/tasks/work_statement/releases/1.0.0/task.prompt.txt
```

Source files:
```
combine-config/document_types/work_package/releases/1.0.0/prompts/task.prompt.txt
combine-config/document_types/work_statement/releases/1.0.0/prompts/task.prompt.txt
```

**Action:** Copy content verbatim. Verify byte-identical with `diff`.

**Verification:** `diff` returns no output for both files.

### Step 2: Create optional meta.yaml for task prompts

Create minimal `meta.yaml` alongside each `task.prompt.txt`:

For work_package:
```yaml
name: "Work Package Task"
intent: "Generate a work package document"
tags: ["work_package"]
```

For work_statement:
```yaml
name: "Work Statement Task"
intent: "Generate a work statement document"
tags: ["work_statement"]
```

These follow the convention used by existing task prompts (e.g., `project_discovery`, `technical_architecture`).

**Verification:** `PackageLoader.get_task("work_package")` and `PackageLoader.get_task("work_statement")` return `TaskPrompt` objects with correct metadata.

### Step 3: Create global schema directories

Create:
```
combine-config/schemas/work_package/releases/1.0.0/schema.json
combine-config/schemas/work_statement/releases/1.0.0/schema.json
```

Source files:
```
combine-config/document_types/work_package/releases/1.0.0/schemas/output.schema.json
combine-config/document_types/work_statement/releases/1.0.0/schemas/output.schema.json
```

**Note:** Source filename is `output.schema.json`, target filename is `schema.json` (matching `StandaloneSchema.from_path()` convention).

**Action:** Copy content verbatim.

**Verification:** `diff` confirms content identical (ignoring filename difference). `json.load()` succeeds on both target files.

### Step 4: Verify PackageLoader resolution

Before writing tests, manually verify resolution succeeds:

```python
from app.config.package_loader import get_package_loader, reset_package_loader

reset_package_loader()
loader = get_package_loader()

# These should now succeed (previously raised VersionNotFoundError)
wp_task = loader.get_task("work_package")
ws_task = loader.get_task("work_statement")
wp_schema = loader.get_schema("work_package")
ws_schema = loader.get_schema("work_statement")

assert wp_task.content, "work_package task prompt is empty"
assert ws_task.content, "work_statement task prompt is empty"
assert wp_schema.content, "work_package schema is empty"
assert ws_schema.content, "work_statement schema is empty"

print(f"work_package task: {len(wp_task.content)} chars")
print(f"work_statement task: {len(ws_task.content)} chars")
print(f"work_package schema: {len(wp_schema.content)} keys")
print(f"work_statement schema: {len(ws_schema.content)} keys")
```

**Verification:** All four assertions pass. No `VersionNotFoundError`.

### Step 5: Implement Tier-0 integrity check

Create `ops/scripts/check_registry_integrity.py`:

```python
"""
Registry Integrity Check -- Tier-0 gate.

Verifies every entry in active_releases.json resolves to an existing
artifact at its canonical global path. Missing asset = HARD_STOP.

Exit codes:
  0 = all assets present and valid
  1 = one or more assets missing or invalid
"""
```

The script must:
1. Load `active_releases.json`
2. For each entry in `tasks`: verify `combine-config/prompts/tasks/{id}/releases/{version}/task.prompt.txt` exists and is non-empty
3. For each entry in `schemas`: verify `combine-config/schemas/{id}/releases/{version}/schema.json` exists and parses as valid JSON
4. For each entry in `roles`: verify `combine-config/prompts/roles/{id}/releases/{version}/role.prompt.txt` exists and is non-empty
5. For each entry in `document_types`: verify `combine-config/document_types/{id}/releases/{version}/package.yaml` exists and parses as valid YAML
6. Print summary table (asset type, id, version, status)
7. Exit 1 if any asset missing or invalid

**Output format:**
```
=== Registry Integrity Check ===
  tasks/work_package:1.0.0              PASS
  tasks/work_statement:1.0.0            PASS
  tasks/intake_gate:1.0.0               PASS
  ...
  schemas/work_package:1.0.0            PASS
  ...
  RESULT: ALL 87 ASSETS VERIFIED
```

Or on failure:
```
  tasks/some_missing_thing:1.0.0        FAIL (directory not found)
  ...
  RESULT: FAILED (3 of 87 assets missing)
```

**Verification:** Script runs and reports all assets. Known-missing assets (to be fixed by WS-PIPELINE-001 and WS-CLEANUP-EFS-001) are documented as expected failures.

### Step 6: Wire integrity check into tier0.sh

Add Check 6 to `tier0.sh` between Check 5 (scope) and the summary:

```bash
# ---------------------------------------------------------------------------
# Check 6: Registry integrity
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 6: Registry Integrity ==="

if is_check_skipped "registry"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[registry]="SKIP"
else
    python3 ops/scripts/check_registry_integrity.py 2>&1
    RESULTS[registry]=$?
    if [[ ${RESULTS[registry]} -ne 0 ]]; then
        echo "FAIL: registry integrity"
        OVERALL_EXIT=1
    else
        echo "PASS: registry integrity"
    fi
fi
```

Update the summary section to include `registry` in the check list.
Update the JSON output to include `registry` in the checks object.
Add `registry` to the `--skip-checks` documentation in the header comment.

**Verification:** `ops/scripts/tier0.sh --skip-checks pytest,lint,typecheck` runs and includes Check 6. Check 6 passes for work_package and work_statement.

### Step 7: Document expected failures

The integrity check will report failures for artifacts that are:
- Orphaned (in active_releases but shouldn't be) -- addressed by WS-PIPELINE-001 and WS-CLEANUP-EFS-001
- Missing global paths (other doc types that only have package-local) -- future work

Create `docs/audits/2026-02-26-registry-integrity-baseline.md` listing:
- All PASS results
- All FAIL results with reason and which WS will fix them
- Timestamp and branch

This baseline establishes the "before" state so subsequent WSs can show measurable improvement.

**Verification:** Baseline document exists and matches check_registry_integrity.py output.

### Step 8: Write Tier-1 tests

Create `tests/tier1/config/test_registry_integrity.py`:

Tests:
1. `test_work_package_task_resolves` -- `get_task("work_package")` returns TaskPrompt with non-empty content
2. `test_work_statement_task_resolves` -- `get_task("work_statement")` returns TaskPrompt with non-empty content
3. `test_work_package_schema_resolves` -- `get_schema("work_package")` returns StandaloneSchema with non-empty content
4. `test_work_statement_schema_resolves` -- `get_schema("work_statement")` returns StandaloneSchema with non-empty content
5. `test_work_package_task_matches_package_local` -- content from `get_task()` matches `package.get_task_prompt()`
6. `test_work_statement_task_matches_package_local` -- content from `get_task()` matches `package.get_task_prompt()`
7. `test_all_active_tasks_have_global_directory` -- for every key in `active_releases.tasks`, directory exists at `combine-config/prompts/tasks/{key}/`
8. `test_all_active_schemas_have_global_directory` -- for every key in `active_releases.schemas`, directory exists at `combine-config/schemas/{key}/`

Tests 7-8 will have known failures for types not yet canonicalized. Use `pytest.mark.xfail` with `reason="Addressed by WS-PIPELINE-001"` or `WS-CLEANUP-EFS-001` so the test suite stays green while documenting the gap.

**Verification:** Human runs `python -m pytest tests/tier1/config/test_registry_integrity.py -v`. Tests 1-6 pass. Tests 7-8 xfail as expected.

---

## Files Created
- `combine-config/prompts/tasks/work_package/releases/1.0.0/task.prompt.txt`
- `combine-config/prompts/tasks/work_package/releases/1.0.0/meta.yaml`
- `combine-config/prompts/tasks/work_statement/releases/1.0.0/task.prompt.txt`
- `combine-config/prompts/tasks/work_statement/releases/1.0.0/meta.yaml`
- `combine-config/schemas/work_package/releases/1.0.0/schema.json`
- `combine-config/schemas/work_statement/releases/1.0.0/schema.json`
- `ops/scripts/check_registry_integrity.py`
- `tests/tier1/config/test_registry_integrity.py`
- `docs/audits/2026-02-26-registry-integrity-baseline.md`

## Files Modified
- `ops/scripts/tier0.sh` (add Check 6)

## Files NOT Modified
- `app/config/package_loader.py` (no loader changes in this WS)
- `app/config/package_model.py` (no model changes)
- `combine-config/_active/active_releases.json` (no entry changes)
- Package-local artifacts under `document_types/` (preserved as-is)

---

## Acceptance Criteria

1. `PackageLoader.get_task("work_package")` succeeds without error
2. `PackageLoader.get_task("work_statement")` succeeds without error
3. `PackageLoader.get_schema("work_package")` succeeds without error
4. `PackageLoader.get_schema("work_statement")` succeeds without error
5. Global task prompt content is byte-identical to package-local source
6. Global schema content is identical to package-local source
7. `check_registry_integrity.py` exits 0 for work_package and work_statement entries
8. `tier0.sh` includes registry integrity as Check 6
9. Tier-1 tests pass for resolution (tests 1-6), xfail for completeness (tests 7-8)
10. Baseline audit document records current state

---

## Proposed Commit Message

```
feat(registry): canonical global paths + Tier-0 integrity gate (WS-REGISTRY-001)

- Create global task prompt dirs for work_package, work_statement
- Create global schema dirs for work_package, work_statement
- Add check_registry_integrity.py (Tier-0 gate)
- Wire as Check 6 in tier0.sh
- Add Tier-1 resolution tests
- Establish integrity baseline document

Resolves audit findings #1, #2 from 2026-02-26-audit-summary.md
```

---

_End of WS-REGISTRY-001_
# WS-IAV-003 — Add Tier-1 Information Architecture for `work_package`

**Status:** ACCEPTED

## Overview

The `work_package` doc type currently has no ADR-054 Information Architecture (IA) contract in its active `package.yaml`.
This causes unstable renderings and prevents Tier-1 IA verification from applying to `work_package`.

This WS adds an ADR-054 Level-2 IA definition to `work_package` and includes it in the Tier-1 IA verification test suite.

## Intent

1. Add `information_architecture` to the active `work_package` `package.yaml` using the existing ADR-054 format.
2. Define Level-2 coverage for all complex fields (arrays, objects, arrays of objects).
3. Add `work_package` to the Tier-1 IA verification test parametrization.
4. IA verification must pass.

## Non-Goals

- No changes to any `work_package` JSON schema.
- No SPA/UI changes.
- No prompt changes.
- No handler behavior changes.

## Inputs (Authoritative)

CC MUST read and use these as the only authoritative sources:

1. Active release pointer:
   - `combine-config/_active/active_releases.json`
2. Active work_package package.yaml:
   - `combine-config/document_types/work_package/releases/{active}/package.yaml`
3. Active work_package schema(s):
   - Global: `combine-config/schemas/work_package/releases/{active}/schema.json` (or equivalent)
   - Package-local: `combine-config/document_types/work_package/releases/{active}/schemas/*.json` (if present)
4. Reference IA implementation (format + vocabulary):
   - `combine-config/document_types/technical_architecture/releases/{active}/package.yaml` (or another Tier-1 doc type that already passes IA verification)

No field paths may be invented. All paths must exist in the active schema.

## ADR-054 Format Requirements (Hard)

### IA block structure

IA must follow the existing repo pattern (sections + binds). Example ONLY of structure (NOT field names):

```yaml
information_architecture:
  version: 2
  sections:
    - id: overview
      label: "Overview"
      binds:
        - path: <schema_field_or_subfield_path>
          render_as: <approved_render_as>
```

### Approved render_as vocabulary

CC MUST ONLY use render types already accepted by ADR-054 and currently used in passing Tier-1 IA doc types.
CC MUST NOT introduce new render_as values (e.g., markdown, heading, badge, checklist, datetime, artifact_ref, object, section).

### Level-2 "No guessing" rule

For any field in the schema whose type is object, array, or array of object:

- IA MUST specify render_as
- If object: MUST enumerate subfields (via nested-object binds pattern used in the repo)
- If array of objects: MUST specify table/card-list columns/fields (repo pattern)
- Raw JSON rendering is forbidden.

## Scope: Fields Requiring Explicit Level-2 Treatment

CC MUST compute this list by scanning the active schema, but the WS expects that at minimum the following categories will be covered:

- Arrays of primitives (render as list/ordered-list)
- Arrays of objects (render as table or card-list with explicit columns/fields)
- Nested objects (render as nested-object or key-value-pairs with explicit subfields)

NOTE: Do not assume field names. Derive from schema.

## Implementation Steps

1. Locate active `work_package` release version from `active_releases.json`.
2. In `work_package` `package.yaml`, add:
   - `information_architecture:` block using repo-standard structure
   - any associated rendering config blocks required by existing doc types (ONLY if they are part of the established pattern and verified by tests)
3. Author IA sections/binds to cover ALL complex fields in the schema.
4. Update Tier-1 IA verification test harness:
   - Add `work_package` to the Tier-1 doc type parametrization list.
5. Bug-First Rule:
   - Write failing Tier-1 tests that assert IA exists and meets Level-2 no-guessing requirements.
   - Implement IA until tests pass.
6. Run IA verification and Tier-1 tests:
   - Expect 0 FAIL for `work_package` IA verification.

## Acceptance Criteria

- `work_package` active `package.yaml` contains `information_architecture` with `version: 2`.
- All complex schema fields have Level-2 render definitions (no guessing).
- No IA field path is present that does not exist in schema.
- `work_package` is included in Tier-1 IA verification parametrization.
- Tier-1 IA tests pass.
- No schema files were modified.

## Rollback

- Revert `package.yaml` and test harness changes.
- No DB migrations.

End of WS-IAV-003.

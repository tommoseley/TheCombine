# WS-WB-021: Fix WP Schema Drift — Declare ws_index[] and Version Bump

**Parent:** WP-WB-002
**Dependencies:** None

## Problem

Code relies on `ws_index[]` but schema may not declare it (phantom field risk). IA verification should pass.

## Deliverables

- Update global WP schema to include `ws_index[]` with the correct shape
- Bump schema release version as required
- Add schema tests confirming:
  - `ws_index[]` is allowed and validated
  - `additionalProperties: false` is preserved

## Acceptance

- IA verification passes for WP doc type
- No runtime writes of undeclared fields remain

## Allowed Paths

- `combine-config/schemas/work_package/`
- `tests/tier1/`

## Prohibited

- Do not modify WP handler logic
- Do not change WP content structure beyond declaring `ws_index`

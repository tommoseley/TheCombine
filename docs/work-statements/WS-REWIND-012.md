# WS-REWIND-012 — Downstream Progression Guard

**Status:** Draft
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

Only current artifacts may be used for downstream processing. Prevent stale or superseded artifacts from feeding into generation, promotion, or stabilization.

## Scope

### In Scope
- Guard check before document generation: verify all input documents are current
- Guard check before WP stabilization: verify WP and all child WSs are current
- Guard check before promotion: verify source document is current
- Deterministic failure with clear error when guard fails

### Out of Scope
- QA-specific rejection (WS-REWIND-013)
- UI for guard failures (WS-REWIND-015)

## Procedure

### Step 1: Create progression guard
- Create `app/domain/services/progression_guard.py`
- `check_inputs_current(document_ids: list[UUID], db) → GuardResult`
  - Query status for each document
  - Return PASS if all are current
  - Return FAIL with list of non-current documents and their statuses

### Step 2: Wire into document generation
- Before plan_executor starts generation, call check_inputs_current on all input documents
- If any input is stale/superseded, abort generation with clear error

### Step 3: Wire into stabilization
- Before WP stabilization endpoint processes, call check_inputs_current
- If WP or any child WS is stale, reject stabilization

### Step 4: Wire into promotion
- Before any document promotion, verify source is current
- Reject if source is stale or superseded

### Step 5: Write tests
- Test: generation proceeds when all inputs current
- Test: generation blocked when input is stale
- Test: stabilization blocked when WP is stale
- Test: stabilization blocked when child WS is stale
- Test: error message identifies the stale document

## Verification Criteria
- No stale artifact can feed into downstream generation
- No stale artifact can be stabilized
- No stale artifact can be promoted
- Guard failures produce clear, actionable errors
- Tests pass

## Allowed Paths
- app/domain/services/progression_guard.py
- app/domain/workflow/plan_executor.py (add guard call)
- app/api/v1/routers/work_binder.py (add guard call)
- tests/tier1/test_progression_guard.py

## Prohibited Actions
- Do not silently skip stale artifacts (must fail explicitly)
- Do not implement automatic remediation
- Do not modify document status in the guard (read-only check)

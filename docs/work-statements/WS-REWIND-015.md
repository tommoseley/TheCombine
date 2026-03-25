# WS-REWIND-015 — Reason-Visible Failure Messages

**Status:** Draft
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

When users try to promote, evaluate, or progress stale artifacts, return deterministic, human-readable errors that identify the cause and required action.

## Scope

### In Scope
- Standardized error response model for rewind-related failures
- Error messages identify: what failed, why, what to do next
- Integration with progression guard, QA rejection, stabilization rejection
- Consistent error format across all rewind-aware endpoints

### Out of Scope
- UI rendering of errors (WP-REWIND-004)
- Automatic remediation suggestions
- Error notification via email

## Procedure

### Step 1: Define error response model
- `RewindBlockedError`:
  - error_code: str (e.g., "STALE_ARTIFACT", "UPSTREAM_REWIND_REQUIRED")
  - document_id: UUID
  - document_type: str
  - current_status: str
  - message: str (human-readable)
  - required_action: str (e.g., "Regenerate from TA stage before proceeding")
  - rewind_stage: Optional[str] (stage that caused invalidation)

### Step 2: Wire into all rewind-aware failure points
- Progression guard → returns RewindBlockedError
- QA rejection → returns RewindBlockedError
- Stabilization rejection → returns RewindBlockedError
- All return HTTP 409 Conflict (correct semantics: state conflict, not bad request)

### Step 3: Write tests
- Test: progression guard failure returns correct error format
- Test: QA rejection returns correct error format
- Test: stabilization rejection returns correct error format
- Test: error includes required_action text
- Test: all error codes are documented

## Verification Criteria
- All rewind-related failures return structured RewindBlockedError
- HTTP 409 used consistently for state conflict errors
- Error messages are human-readable and actionable
- required_action tells the user what to do next
- Tests pass

## Allowed Paths
- app/domain/models/ (error model)
- app/domain/services/ (integration)
- app/api/v1/routers/ (HTTP response)
- tests/tier1/test_rewind_errors.py

## Prohibited Actions
- Do not use generic 400/500 errors for rewind-specific failures
- Do not suppress error details
- Do not implement automatic remediation

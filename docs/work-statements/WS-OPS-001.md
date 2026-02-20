# WS-OPS-001: Transient LLM Error Recovery and Honest Gate Outcomes

## Status: Accepted

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-010 -- LLM Execution Logging

## Verification Mode: A

## Allowed Paths

- app/llm/
- app/domain/workflow/nodes/
- spa/src/
- tests/

---

## Objective

When an LLM call fails due to a retryable operational error (e.g., Anthropic 529 Overloaded), the system must:

1. Retry automatically with backoff (so most failures self-heal).
2. If retries exhaust, surface an OPERATIONAL_ERROR outcome (never degrade to needs_clarification).
3. Tell the user the truth in the UI with a simple Retry affordance.

This work explicitly avoids "platform resilience" scope (circuit breaker, provider switching, metrics suite).

---

## Scope

### In Scope

- Add retry-with-backoff to the LLM client layer for retryable failures
- Introduce/standardize an OperationalError result payload structure
- Update Intake Gate (and any other gate using LLM classification) to:
  - treat retry exhaustion as `operational_error`
  - store error payload in `context_state`
  - pause for user input with operational error prompt (not clarification prompt)
- Update UI to display:
  - "Provider temporarily unavailable. Retry?"
  - a Retry button that re-submits the user message to the same endpoint

### Out of Scope

- Circuit breaker
- Provider/model switching
- Dedicated retry endpoint
- Metrics/telemetry beyond existing logging
- Broad refactors across all workflows (only gates that currently "lie")

---

## Design Decisions

### DD-OPS-001 -- Operational error is a first-class outcome

If an LLM call fails and retries exhaust, the workflow must emit an operational error outcome, not a semantic classification.

### DD-OPS-002 -- Retry policy is small and deterministic

- max_attempts = 3
- exponential backoff (e.g., 0.5s, 2s, 8s) with jitter
- respect provider headers when available:
  - `retry-after`
  - `x-should-retry`
- retryable status codes: 429, 503, 504, 529
- retryable transport failures: timeouts, connection reset, DNS failures

---

## Data Contract

OperationalErrorPayload (stored in context_state):

```json
{
  "status": "OPERATIONAL_ERROR",
  "retryable": true,
  "provider": "anthropic",
  "http_status": 529,
  "request_id": "req_...",
  "message": "Overloaded",
  "first_seen_at": "2026-02-20T19:07:47Z"
}
```

---

## Implementation Tasks

### Task 1 -- LLM Client Retry Wrapper

- Implement `call_with_retry(...)` in the LLM client layer
- Extract headers: `retry-after` (seconds), `x-should-retry`, `request-id`
- On retryable failures: sleep(backoff), retry up to max_attempts
- On final failure: raise/return a structured `LLMOperationalError` including request_id and status

### Task 2 -- Gate Outcome Honesty (Intake Gate)

- In `intake_gate_profile` (and any similar gate):
  - on `LLMOperationalError` after retries:
    - store OperationalErrorPayload in `context_state` (e.g., key `intake_operational_error`)
    - return `needs_user_input` with `reason=operational_error`
  - DO NOT set "Classification complete -- needs_clarification" on failure paths

### Task 3 -- UI: Operational Error Panel + Retry

- If response indicates operational error:
  - show: "The AI provider is temporarily unavailable. Retry?"
  - Retry button re-posts the same message to `/api/v1/intake/{exec_id}/message`
- Do not show clarification questions when the reason is operational error

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

### Task 1 Criteria

1. **Retries on 529**: LLM client retries up to max_attempts on HTTP 529
2. **No retries on 400/401/403**: LLM client does not retry on non-retryable status codes
3. **Retry-after respected**: When `retry-after` header is present, backoff uses that value
4. **Structured error on exhaustion**: After max retries, an `LLMOperationalError` is raised with provider, status code, and request_id

### Task 2 Criteria

5. **No false classification**: Simulated 529 (after retry exhaustion) does not produce a "Classification complete" log line
6. **Error payload stored**: context_state contains OperationalErrorPayload with correct fields
7. **Outcome is operational_error**: Gate returns `needs_user_input` with `reason=operational_error`, not `reason=needs_clarification`

### Task 3 Criteria

8. **Error message shown**: When response indicates operational error, UI shows provider unavailable message (not clarification questions)
9. **Retry works**: Retry button re-submits message; when provider recovers, classification proceeds normally

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-9. Verify all fail.

For Task 1: unit tests with mocked HTTP responses.
For Task 2: unit tests with mocked LLM client raising LLMOperationalError.
For Task 3: component or route-level tests (Mode B acceptable if no React test harness).

### Phase 2: Implement

Execute Tasks 1, 2, 3 in order.

### Phase 3: Verify

1. All Tier 1 tests pass
2. Run Tier 0 harness -- must return zero

---

## Prohibited Actions

- Do not implement circuit breaker logic
- Do not add provider/model switching
- Do not create a dedicated retry API endpoint
- Do not refactor workflows beyond fixing the "lie" in gate outcomes
- Do not modify LLM execution logging (ADR-010) beyond adding error details

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] LLM client retries transient errors with backoff
- [ ] Non-retryable errors are not retried
- [ ] Gate produces operational_error outcome, not needs_clarification, on LLM failure
- [ ] OperationalErrorPayload stored in context_state
- [ ] UI shows truthful error message with retry affordance
- [ ] Retry button works when provider recovers
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

## Deferred Tech Debt

| Item | When |
|------|------|
| Circuit breaker (per provider/model) | When traffic or multi-provider warrants it |
| Provider fallback / model switching | When multiple providers are configured |
| Dedicated retry endpoint | When retry semantics need to differ from message resubmission |
| Metrics dashboard (failure rates, retry counts) | When observability infrastructure exists |

---

_End of WS-OPS-001_

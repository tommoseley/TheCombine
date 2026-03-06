# WS-RING0-002: Escalation Wiring + Cancel Endpoint

**Parent:** Ring 0 readiness (RCA 2026-03-03)
**Depends on:** WS-RING0-001 (complete — circuit breaker fixed, `is_qa_gate()` predicate shipped)
**Blocks:** Graceful failure recovery in pipeline runs

---

## Objective

Wire the escalation mechanism to the QA circuit breaker edge so that when the circuit breaker trips, the workflow pauses for operator decision (retry or abandon) instead of terminating with `end_blocked`. Add a cancel endpoint so operators can terminate stuck or unwanted workflows.

---

## Context

WS-RING0-001 fixed the circuit breaker — it now trips correctly after N QA failures on gate-type nodes. But it routes to `end_blocked`, which is terminal with no user recovery path. The RCA (2026-03-03) identified three remaining defects:

- **DEF-2:** `end_blocked` is a dead end with no user remedy. The escalation mechanism exists in code but is not wired to the QA circuit breaker edge.
- **DEF-3:** No cancel/reset endpoint. No API endpoint to cancel a running or paused workflow execution.
- **DEF-4:** No SPA UI for workflow error states. (Out of scope for this WS — future work.)

The escalation infrastructure already exists: `POST /api/v1/document-workflows/executions/{id}/escalation` and `POST /api/v1/interrupts/{id}/resolve` endpoints are in the codebase but unwired to the QA failure path.

---

## Scope

**In scope:**

- Update `qa_circuit_breaker` edge in workflow definition(s) to use escalation instead of terminal `end_blocked`
- Verify `handle_escalation_choice` correctly handles "retry" (reset retry count, re-enter QA) and "abandon" (terminal)
- Add `POST /api/v1/document-workflows/executions/{id}/cancel` endpoint
- Tier-1 tests for escalation flow and cancel endpoint

**Out of scope:**

- SPA UI for workflow error states (DEF-4, future WS)
- Changes to QA evaluation logic or prompts
- Changes to remediation logic
- Changes to the circuit breaker threshold value

---

## Prohibited

- Do not modify `QANodeExecutor` or gate executor dispatch logic
- Do not modify the `is_qa_gate()` predicate or `Node` model (shipped in WS-RING0-001)
- Do not change the circuit breaker retry threshold
- Do not add SPA components — this is backend-only

---

## Steps

### Phase 1: Tests first (must fail before implementation)

**Step 1.1: Test escalation on circuit breaker trip**

File: `tests/tier1/workflow/test_escalation_wiring.py` (new)

Tests:

- Circuit breaker trips → workflow state becomes `paused` (not `completed`/`blocked`)
- Escalation options `["retry", "abandon"]` are present on the paused execution
- Resolve escalation with "retry" → retry count resets, workflow re-enters QA gate
- Resolve escalation with "abandon" → workflow terminates with `terminal_outcome = "abandoned"`
- Escalation without prior circuit breaker trip → 409 Conflict (no escalation pending)

**Step 1.2: Test cancel endpoint**

File: `tests/tier1/api/test_cancel_endpoint.py` (new or extend existing)

Tests:

- `POST /cancel` on running execution → status becomes `cancelled`, `terminal_outcome = "cancelled"`
- `POST /cancel` on paused execution → status becomes `cancelled`
- `POST /cancel` on completed execution → 409 Conflict
- `POST /cancel` on already cancelled execution → 409 Conflict
- `POST /cancel` on non-existent execution → 404

### Phase 2: Implementation

**Step 2.1: Update workflow definition circuit breaker edge**

File(s): All workflow definitions containing a `qa_circuit_breaker` edge. At minimum: `combine-config/workflows/project_discovery/releases/2.0.0/definition.json`

Change `qa_circuit_breaker` edge from:

```json
{
  "edge_id": "qa_circuit_breaker",
  "from_node_id": "qa_gate",
  "to_node_id": "end_blocked",
  "outcome": "fail",
  "label": "Circuit breaker - max remediation attempts",
  "conditions": [{"type": "retry_count", "operator": "gte", "value": 2}]
}
```

To:

```json
{
  "edge_id": "qa_circuit_breaker",
  "from_node_id": "qa_gate",
  "to_node_id": null,
  "outcome": "fail",
  "non_advancing": true,
  "label": "Circuit breaker - escalate to operator",
  "escalation_options": ["retry", "abandon"],
  "conditions": [{"type": "retry_count", "operator": "gte", "value": 2}]
}
```

Search all workflow definitions in `combine-config/` for `qa_circuit_breaker` edges and apply the same change.

**Step 2.2: Verify escalation handler supports retry and abandon**

File: `app/domain/workflow/plan_executor.py` (or wherever `handle_escalation_choice` lives)

Verify existing escalation handling:

- "retry": resets `state.retry_counts` for the generating node, transitions back to QA gate
- "abandon": sets `terminal_outcome = "abandoned"`, transitions to terminal state

If the handler does not support these choices, implement the missing paths.

**Step 2.3: Add cancel endpoint**

File: `app/api/v1/routers/document_workflows.py`

```python
@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a running or paused workflow execution."""
    # Load execution
    # Verify status is running or paused (not completed/cancelled)
    # Set status = cancelled, terminal_outcome = "cancelled"
    # Persist
    # Return updated execution
```

Status validation rules:

- `running` → cancellable
- `paused` → cancellable
- `completed` → 409 Conflict ("Execution already completed")
- `cancelled` → 409 Conflict ("Execution already cancelled")
- Not found → 404

### Phase 3: Verify

**Step 3.1:** Run all Phase 1 tests — all must pass.

**Step 3.2:** Run full Tier-1 suite — no regressions.

---

## Allowed Paths

```
app/domain/workflow/plan_executor.py
app/api/v1/routers/document_workflows.py
combine-config/workflows/
tests/tier1/
```

---

## Verification

- [ ] Circuit breaker trips → workflow pauses with escalation options (not terminal)
- [ ] Resolve with "retry" → retry count resets, re-enters QA gate
- [ ] Resolve with "abandon" → workflow terminates with `terminal_outcome = "abandoned"`
- [ ] Cancel endpoint returns 200 for running/paused executions
- [ ] Cancel endpoint returns 409 for completed/cancelled executions
- [ ] Cancel endpoint returns 404 for non-existent executions
- [ ] All workflow definitions with `qa_circuit_breaker` edges are updated
- [ ] All existing Tier-1 tests pass (no regressions)

---

_Draft: 2026-03-06_
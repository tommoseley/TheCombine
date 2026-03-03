# RCA: Type Identity Drift — QA Gate Circuit Breaker Failure

**Date:** 2026-03-03
**Severity:** Critical (user-facing, no self-recovery, unbounded LLM cost)
**Affected execution:** `exec-22c295726290` (space `b320898a-8276-4919-ae01-a12f8756882d`)
**Status:** Root-caused. Remediation WS required before Ring0 continues.
**Classification:** Cross-layer contract violation (type identity drift)

---

## Incident Summary

A Project Discovery workflow entered an infinite QA→remediation→QA loop. QA repeatedly failed on the same constraint-language issues (3 observed cycles), remediation regenerated similar content, and the workflow never terminated. The circuit breaker — designed to stop exactly this — was dead code. The user had no mechanism to intervene, cancel, or reset. Manual DB deletion was required.

---

## This Was Not a QA Problem

The infinite loop didn't happen because QA was wrong. QA failed deterministically. Remediation executed. Edges routed correctly. State transitions persisted.

**The only failure was retry accounting.**

The workflow model defines QA as `type: "gate"` + `gate_kind: "qa"`. The executor's retry logic checks `NodeType.QA`. Those two ontologies diverged. The retry counter never incremented. The circuit breaker never activated. The system kept consuming LLM tokens.

This is a **cross-layer contract violation** between:
- **Workflow Definition Model** — uses `type: "gate"` + `gate_kind: "qa"`
- **Runtime Node Model** — has `NodeType.QA` enum but no workflow uses it
- **Execution State Accounting** — checks `NodeType.QA` for retry tracking

**The two systems have inconsistent models of what "a QA node" is.**

When different layers encode the same concept differently, circuit breakers fail silently. That is a Ring0-level integrity issue.

---

## Root Cause: Type Identity Drift

### The divergence

The QA gate node is defined in the workflow with `"type": "gate"` and `"gate_kind": "qa"`:

```json
{
  "node_id": "qa_gate",
  "type": "gate",
  "gate_kind": "qa"
}
```

At runtime, `Node.from_dict()` maps this to `NodeType.GATE`. The gate executor correctly dispatches to `QANodeExecutor` based on `gate_kind` — it knows what a QA gate is.

But the plan executor's retry logic checks `NodeType.QA` — a different answer to the same question:

| Location | Code | Purpose | Fires? |
|----------|------|---------|--------|
| L1127 | `current_node.type != NodeType.QA` | `_prepare_qa_retry_tracking` — set generating_node_id | **Never** |
| L1165 | `current_node.type == NodeType.QA` | `_handle_qa_retry_feedback` — increment retry count | **Never** |
| L1081 | `current_node.type == NodeType.QA` | `_handle_terminal_node` — circuit breaker log | **Never** |
| L352 | `current_node.type == NodeType.QA` | Load PGC answers for QA | **Never** |

The `NodeType.QA` enum value exists but is **never used by any workflow definition**. It is an orphaned concept — the runtime model carries it, but the configuration model doesn't emit it.

### The consequence

Because `_prepare_qa_retry_tracking` never fires:
- `state.generating_node_id` is never set
- `state.retry_counts` is never incremented
- EdgeRouter always sees `retry_count = 0`
- `qa_fail_remediate` condition (`retry_count < 2`) always matches
- `qa_circuit_breaker` condition (`retry_count >= 2`) never matches

**The circuit breaker is dead code for every QA gate in the system.**

### Why this wasn't caught

1. No end-to-end Tier-1 test for "QA fails N times → breaker trips." The retry logic was tested in isolation but never against a real gate-type node.
2. The WS-CRAP-008 refactoring (this session) extracted these checks into sub-methods but preserved the original logic faithfully — the bug predates the refactoring.
3. The gate executor's correct dispatch by `gate_kind` masked the fact that plan executor was checking a different predicate.

---

## Architectural Incompleteness

Even if the circuit breaker worked, the user was still trapped.

### No escalation wiring

The codebase has escalation infrastructure:
- `POST /api/v1/document-workflows/executions/{id}/escalation` endpoint
- `POST /api/v1/interrupts/{id}/resolve` endpoint
- `InterruptRegistry` with `get_pending()`, `resolve()`, `escalate()`
- `handle_escalation_choice()` in plan_executor

But the `qa_circuit_breaker` edge has no `escalation_options`. It routes directly to `end_blocked` — a terminal node. The escalation mechanism exists in code but is never triggered by QA failure.

### No cancel/reset

There is no API endpoint to cancel a running workflow or reset a blocked one for re-execution.

### No UI for intervention

The SPA has `ExecutionList` and `ExecutionDetail` admin components, but they are read-only status displays. The main project UI has no awareness of stuck or blocked workflows. No QA error display. No cancel button. No retry action.

**The system can escalate in code and store escalation metadata, but it cannot present escalation, accept user choice, or reset execution.** That's not a UX gap — it's a governance gap.

---

## Impact

- **User impact:** Workflow appears to hang. No error message, no recovery action available. Requires developer DB deletion to reset.
- **Resource impact:** Each remediation cycle consumes an LLM call (~$0.05–0.15). An unattended infinite loop would consume unbounded API credits.
- **Trust impact:** First Ring0 test of the PD workflow failed with no user recourse. Ring0 cannot proceed without this fix.

---

## Ring0 Assessment

This is the first real Ring0 failure. And it's a productive one.

Ring0 exists to surface incompleteness. This incident surfaced:
- Circuit breaker not wired (type identity drift)
- Escalation unwired (infrastructure exists, never triggered)
- No cancel endpoint
- No UI intervention

Restarting Ring0 would hide the defect. Fixing it is the test.

### What was validated (positive signal)

The execution model is correct enough that:
- QA fails deterministically
- Remediation executes
- Edges route correctly
- State transitions persist
- The only failure was retry accounting

---

## Defects

### DEF-1: Type identity drift in QA gate recognition (Critical)

**Class:** Cross-layer contract violation.

**Root cause:** No single canonical definition of "QA-ness." The gate executor resolves it via `gate_kind`. The plan executor resolves it via `NodeType.QA`. These are different answers.

**Fix:** Centralize QA gate identity into a single predicate on the `Node` model:

```python
# On Node dataclass
def is_qa_gate(self) -> bool:
    return (
        self.type == NodeType.QA
        or (self.type == NodeType.GATE and self.gate_kind == "qa")
    )
```

This requires adding `gate_kind` as a field on `Node` (parsed from raw config in `from_dict`).

Then every plan_executor check becomes `if node.is_qa_gate():` — one definition, no drift.

If you don't centralize it, this will reappear in six months.

### DEF-2: No Tier-1 test for circuit breaker end-to-end (Critical)

**Root cause:** Retry logic was tested in isolation but never against a gate-type QA node. No test proves "QA fails N times → breaker trips."

**Fix:** Write a Tier-1 test that:
1. Creates a workflow with a gate-type QA node (type=gate, gate_kind=qa)
2. Simulates N QA failures
3. Asserts retry_count increments deterministically
4. Asserts circuit breaker edge is selected after threshold

### DEF-3: `end_blocked` is a dead end with no user remedy (High)

**Root cause:** The `qa_circuit_breaker` edge routes to `end_blocked` (terminal) with no `escalation_options`. The escalation mechanism exists but is unwired.

**Fix:** Change `qa_circuit_breaker` edge to non-advancing with escalation options:
```json
{
  "edge_id": "qa_circuit_breaker",
  "from_node_id": "qa_gate",
  "to_node_id": null,
  "outcome": "fail",
  "non_advancing": true,
  "escalation_options": ["retry", "abandon"],
  "conditions": [{"type": "retry_count", "operator": "gte", "value": 2}]
}
```

### DEF-4: No cancel endpoint for stuck workflows (High)

**Root cause:** No API endpoint to cancel a running workflow or reset a blocked one.

**Fix:** Add `POST /api/v1/document-workflows/executions/{id}/cancel`. Make blocked workflows visible via API status query.

### DEF-5: No SPA UI for workflow error states (Medium)

**Root cause:** Admin views are read-only. Project UI has no awareness of workflow errors.

**Fix:** Surface workflow error state in the document creation flow. Even minimal: show blocked status + cancel button.

---

## Mandatory Before Continuing Ring0

| # | Fix | Severity | Required? |
|---|---|---|---|
| 1 | Centralized `is_qa_gate()` predicate on Node + replace all checks | Critical | **Mandatory** |
| 2 | Tier-1 test proving breaker trips after N retries with gate-type QA | Critical | **Mandatory** |
| 3 | Deterministic retry_count increment verification | Critical | **Mandatory** |
| 4 | Cancel endpoint (API-only acceptable) | High | **Strongly recommended** |
| 5 | Blocked workflows visible via API | High | **Strongly recommended** |

Without #4 and #5, automation is fragile. And Ring0 is about automation.

---

## Evidence

### Execution log (last 5 entries from deleted execution)

```
1. qa_gate fail   (22:15:30) — 3 QA errors (constraint language)
2. remediation ok (22:15:57) — regenerated document
3. qa_gate fail   (22:16:05) — same 3 QA errors
4. remediation ok (22:16:30) — regenerated document
5. qa_gate fail   (22:16:38) — same 3 QA errors
→ current_node: "remediation", status: "running" (loop continues)
```

Circuit breaker threshold is 2 retries. 3 QA failures observed, still running — confirming counter never incremented.

### Code trace

```
_prepare_qa_retry_tracking (L1127):
  if current_node.type != NodeType.QA:  ← NodeType.GATE != NodeType.QA → returns immediately
      return
  # generating_node_id never set
  # retry_count never checked

EdgeRouter._get_condition_value (L193):
  node_id = getattr(state, 'generating_node_id', None) or state.current_node_id
  # generating_node_id is None → falls back to "qa_gate"
  return state.get_retry_count("qa_gate")  → 0 (never incremented)

Edge evaluation:
  qa_fail_remediate: 0 < 2 → True → routes to remediation (ALWAYS)
  qa_circuit_breaker: 0 >= 2 → False → never selected
```

---

## Related

- WS-CRAP-008: Refactored `_handle_result` — preserved the bug faithfully during extraction
- ADR-039: Document workflow execution model
- ADR-049: No Black Boxes — workflow definitions with explicit gate internals
- Workflow definition: `combine-config/workflows/project_discovery/releases/2.0.0/definition.json`

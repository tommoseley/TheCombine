# WS-RING0-001: Fix QA Gate Type Identity Drift + Circuit Breaker

**Parent:** Ring0 readiness (RCA 2026-03-03)
**Depends on:** None
**Blocks:** All further Ring0 testing

---

## Objective

Centralize QA gate identity into a single canonical predicate on `Node`, fix the circuit breaker so it trips after N retries with gate-type QA nodes, and prove correctness with Tier-1 tests. Route circuit breaker to `end_blocked` (clean stop). Escalation wiring and cancel endpoint deferred to WS-RING0-002.

---

## Design Note

The RCA recommended option (c) — checking `result.metadata.get("gate_kind") == "qa"`. This WS diverges: it adds `gate_kind` to the `Node` dataclass and checks there. This is better because it puts identity on the entity itself rather than depending on result metadata that only exists after execution. The predicate works before, during, and after execution.

---

## Scope

**In scope:**
- Add `gate_kind` field to `Node` dataclass, parse in `from_dict`
- Add `is_qa_gate()` method to `Node`
- Replace all `NodeType.QA` checks in `plan_executor.py` with `node.is_qa_gate()`
- Tier-1 tests: predicate correctness, circuit breaker trips end-to-end, retry count increments deterministically

**Out of scope (deferred to WS-RING0-002):**
- Changing circuit breaker edge from terminal to escalation
- Cancel endpoint
- SPA UI for workflow error states

---

## Prohibited

- Do not modify QANodeExecutor or gate executor dispatch logic
- Do not change the QA evaluation criteria or prompts
- Do not modify NodeType enum values
- Do not remove `NodeType.QA` from the enum (may be used by future workflow definitions)
- Do not change the circuit breaker edge target (remains `end_blocked`)

---

## Steps

### Phase 1: Tests first (must fail before implementation)

**Step 1.1: Test `Node.is_qa_gate()` predicate**

File: `tests/tier1/workflow/test_plan_models.py` (create if needed)

Tests:
- `Node(type=NodeType.QA)` → `is_qa_gate()` returns True
- `Node(type=NodeType.GATE, gate_kind="qa")` → `is_qa_gate()` returns True
- `Node(type=NodeType.GATE, gate_kind="pgc")` → `is_qa_gate()` returns False
- `Node(type=NodeType.GATE, gate_kind=None)` → `is_qa_gate()` returns False
- `Node(type=NodeType.TASK)` → `is_qa_gate()` returns False

**Step 1.2: Test circuit breaker trips after N retries with gate-type QA node**

File: `tests/tier1/workflow/test_circuit_breaker.py` (new)

This is the money test — exact reproduction of the RCA scenario. Must fail before the fix and pass after.

Test: Simulate the exact failure scenario:
1. Create a `PlanExecutor` (via `__new__` + mocked deps, same importlib pattern as existing tests)
2. Create a workflow plan containing a gate-type QA node (`type=gate`, `gate_kind=qa`) and the standard edges (`qa_fail_remediate` with `retry_count < 2`, `qa_circuit_breaker` with `retry_count >= 2`)
3. Create `DocumentWorkflowState` with `node_history` containing a prior task node (the generating node)
4. Simulate `_prepare_qa_retry_tracking` with a failed QA result from the gate-type node
5. Assert `state.generating_node_id` is set (currently fails — the bug)
6. Simulate `_handle_qa_retry_feedback` — assert retry count increments
7. Repeat until count >= threshold
8. Assert EdgeRouter selects `qa_circuit_breaker` edge (routes to `end_blocked`)
9. Assert EdgeRouter selects `qa_fail_remediate` edge when count < threshold

### Phase 2: Implementation

**Step 2.1: Add `gate_kind` to Node and `is_qa_gate()` predicate**

File: `app/domain/workflow/plan_models.py`

```python
@dataclass
class Node:
    # ... existing fields ...
    gate_kind: Optional[str] = None  # "qa", "pgc", etc.

    @classmethod
    def from_dict(cls, raw):
        return cls(
            # ... existing fields ...
            gate_kind=raw.get("gate_kind"),
        )

    def is_qa_gate(self) -> bool:
        """Canonical definition of QA-ness. Single source of truth."""
        return (
            self.type == NodeType.QA
            or (self.type == NodeType.GATE and self.gate_kind == "qa")
        )
```

**Step 2.2: Replace all NodeType.QA checks in plan_executor.py**

File: `app/domain/workflow/plan_executor.py`

Search for all occurrences of `NodeType.QA` and replace with `node.is_qa_gate()`. Do not navigate by line number — line numbers shifted during WP-CRAP-002 refactoring. Search instead.

All 5 occurrences:

| Before | After | Context |
|--------|-------|---------|
| `current_node.type == NodeType.QA` | `current_node.is_qa_gate()` | Load PGC answers for QA |
| `current_node.type == NodeType.QA` | `current_node.is_qa_gate()` | `_handle_terminal_node` circuit breaker log |
| `current_node.type != NodeType.QA` | `not current_node.is_qa_gate()` | `_prepare_qa_retry_tracking` guard |
| `current_node.type == NodeType.QA` | `current_node.is_qa_gate()` | `_handle_qa_retry_feedback` increment |
| `current_node.type == NodeType.QA` | `current_node.is_qa_gate()` | `_handle_qa_retry_feedback` clear on success |

### Phase 3: Verify

**Step 3.1:** Run all Step 1 tests — all must pass.

**Step 3.2:** Run full Tier-1 suite — no regressions.

**Step 3.3:** Run Tier 0 verification.

---

## Allowed Paths

```
app/domain/workflow/plan_models.py
app/domain/workflow/plan_executor.py
tests/tier1/
```

---

## Verification

- [ ] `Node.is_qa_gate()` returns True for both `NodeType.QA` and `NodeType.GATE` + `gate_kind="qa"`
- [ ] `Node.from_dict()` parses `gate_kind` from raw workflow config
- [ ] `_prepare_qa_retry_tracking` fires for gate-type QA nodes (Step 1.2 test passes)
- [ ] `_handle_qa_retry_feedback` increments retry count for gate-type QA nodes
- [ ] Retry count reaches threshold → EdgeRouter selects circuit breaker edge → `end_blocked`
- [ ] All existing Tier-1 tests pass (no regressions)

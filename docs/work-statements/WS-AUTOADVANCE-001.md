# WS-AUTOADVANCE-001: DCW-Level Auto-Advance Pipeline Execution

**Parent:** Pipeline usability
**Depends on:** WS-RING0-001 (complete — circuit breaker), WS-RING0-002 (escalation wiring — should ship first)
**Blocks:** Production-scale pipeline usability

---

## Objective

Add a DCW-level `auto_advance` attribute that causes the pipeline to automatically transition between stages on the happy path, pausing only when an explicit pause condition fires. This eliminates manual stage-advancement clicks while preserving all governance gates.

---

## Context

The pipeline currently requires manual user action to advance between stages — even when no human input is needed. For a Hello World project with 5 pipeline stages and multiple documents, this means 10+ clicks just to move work through the system. For a real project with 30+ documents, this becomes 100+ clicks. Users will either button-mash (defeating governance) or quit.

The friction is not governance. The friction is manual stage advancement. The quality gates (PGC questions, QA validation, IA verification, schema checks) are mechanical and fast. The problem is that the workflow engine waits for an external trigger between stages instead of auto-advancing when no human decision is required.

The workflow engine already supports the building blocks:

- **Auto-retry on QA fail**: remediation loops run without manual intervention
- **Pause on PGC questions**: the pipeline stops and waits for operator input
- **Pause on escalation**: WS-RING0-002 wires circuit breaker → escalation pause

What's missing: the happy path (stage complete → start next stage) also waits for a manual trigger instead of auto-advancing.

---

## Scope

**In scope:**

- Add `auto_advance` boolean attribute to DCW (Document Configuration Workflow) definition schema
- Add `pause_conditions` list to DCW definition schema
- Modify the plan executor's post-completion logic: after edge routing selects the next node, evaluate whether dispatch should proceed automatically
- Define the initial set of pause conditions (PGC questions, classification confirmation, escalation pending)
- Update existing workflow definitions to set `auto_advance: true`
- Optional per-step override: `advance_mode: pause|inherit` on individual nodes (nodes may only introduce brakes, not acceleration)
- Tier-1 tests for auto-advance behavior and pause conditions
- SPA changes: replace stage action buttons with status indicators when `auto_advance` is active on the workflow
- SSE event contract for pipeline control (paused, resumed, progress)

**Out of scope:**

- "Guided mode" vs "Auto mode" toggle — there is one mode: auto-advance with pause on human-required gates
- Governance weight scaling by artifact level — governance is mechanical and consistent regardless of artifact size
- Batch approval UI (future enhancement)
- "Run to Binder" composite button (future UX — can be built on top of auto-advance)
- Changes to QA evaluation logic, remediation logic, or PGC question generation

---

## Prohibited

- Do not remove governance gates — auto-advance skips manual advancement, not quality checks
- Do not add user-facing "mode" toggles (guided vs auto) — the pipeline has one execution model
- Do not modify PGC question handling — it already pauses correctly
- Do not modify escalation handling — WS-RING0-002 covers that
- Do not change the circuit breaker threshold or QA gate logic

---

## Steps

### Phase 1: Tests first (must fail before implementation)

**Step 1.1: Test auto-advance on happy path**

File: `tests/tier1/workflow/test_auto_advance.py` (new)

Tests:

- Workflow with `auto_advance: true` → after node A completes successfully, node B dispatches immediately without waiting for external trigger
- Workflow with `auto_advance: false` (or absent) → after node A completes, workflow waits for external trigger (existing behavior, must not break)
- Chain of 3 nodes with `auto_advance: true`, no pause conditions → all 3 execute in sequence without manual intervention

**Step 1.2: Test pause conditions halt auto-advance**

Tests:

- Workflow with `auto_advance: true` and `pause_conditions: ["pgc_required"]` → pipeline pauses when the next node has unresolved PGC questions, resumes after answers submitted
- Workflow with `auto_advance: true` and `pause_conditions: ["escalation_pending"]` → pipeline pauses when escalation fires, resumes after resolution
- Workflow with `auto_advance: true` and `pause_conditions: ["classification_confirmation"]` → pipeline pauses for concierge classification review
- Multiple pause conditions: pipeline only pauses when at least one condition is true

**Step 1.3: Test per-step override**

Tests:

- Node with `advance_mode: "pause"` in an auto-advance workflow → pipeline pauses before dispatching the next node, regardless of DCW-level setting
- Node with `advance_mode: "inherit"` (or absent) → uses DCW-level `auto_advance` setting
- Node without `advance_mode` in a non-auto-advance workflow → manual behavior (unchanged)

**Step 1.4: Test backward compatibility**

Tests:

- Existing workflow definitions without `auto_advance` attribute → behavior is identical to current (manual advancement required)
- No regressions in existing workflow execution tests

**Step 1.5: Test SSE event contract**

Tests:

- When pipeline pauses due to a pause condition → `pipeline:paused` event emitted with correct `pause_reason` and `node_id`
- When pipeline resumes after operator input → `pipeline:resumed` event emitted
- When a node starts/completes during auto-advance → `pipeline:progress` events emitted
- `pause_reason` value matches the condition that triggered the pause

### Phase 2: Implementation

**Step 2.1: Add auto_advance to DCW schema**

File: The DCW/workflow definition schema (likely in `seed/schemas/` or wherever workflow definition JSON schemas live)

Add to the workflow definition schema:

```json
{
  "auto_advance": {
    "type": "boolean",
    "default": false,
    "description": "When true, the pipeline automatically advances to the next node after completion unless a pause condition fires"
  },
  "pause_conditions": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": ["pgc_required", "classification_confirmation", "escalation_pending"]
    },
    "default": ["pgc_required", "classification_confirmation", "escalation_pending"],
    "description": "Conditions that halt auto-advance and wait for operator input"
  }
}
```

**Step 2.2: Add advance_mode to node schema**

Add optional per-node override:

```json
{
  "advance_mode": {
    "type": "string",
    "enum": ["pause", "inherit"],
    "default": "inherit",
    "description": "Override DCW-level auto_advance for this specific node. Nodes may only add brakes (pause), not acceleration."
  }
}
```

Design constraint: nodes may declare `pause` to force a stop, but cannot override a manual workflow to force auto-advance. The workflow defines the run style; steps may only introduce brakes, not acceleration.

**Step 2.3: Modify plan executor post-completion logic**

File: `app/domain/workflow/plan_executor.py`

After edge routing selects the next node, evaluate whether dispatch of that next node should proceed automatically:

1. Determine effective advance mode:
   - If the next node has `advance_mode: "pause"` → wait for trigger
   - If the next node has `advance_mode: "inherit"` (or absent) → use `workflow.auto_advance`
2. If effective mode is auto-advance:
   - Evaluate pause conditions against the next node's context and current workflow state
   - If any pause condition is true → set workflow status to `paused`, emit `pipeline:paused` SSE event, wait for operator
   - If no pause condition is true → emit `pipeline:progress` SSE event, immediately dispatch the next node (no external trigger needed)
3. If effective mode is manual → existing behavior (wait for trigger)

On resume (after operator provides input for a pause condition):
- Emit `pipeline:resumed` SSE event
- Dispatch the next node

**Step 2.4: Implement pause condition evaluators**

File: `app/domain/workflow/plan_executor.py` (or a new `pause_conditions.py` if cleaner)

Each pause condition is a predicate that evaluates the next node's context and current workflow state:

| Condition | Evaluates True When |
|-----------|-------------------|
| `pgc_required` | The next node is a PGC gate with unresolved questions. A station with zero unresolved questions MUST NOT trigger a pause. |
| `classification_confirmation` | The next node requires operator confirmation of intake classification |
| `escalation_pending` | An escalation is active (circuit breaker tripped) |

Note: `pgc_required` evaluates true **only** when unresolved operator questions exist for the next node. A station with zero unresolved questions (all inherited or already answered) MUST NOT trigger a pause. Without this rule, auto-advance would still pause at every PGC gate even when all questions are resolved — defeating the purpose.

Nodes that require an explicit manual gate use `advance_mode: "pause"` on the node definition. This is a node directive, not a workflow-level pause condition.

```python
def should_pause(workflow_def, state, next_node) -> tuple[bool, str | None]:
    """Check if any pause condition is met.

    Returns (should_pause, pause_reason).
    pause_reason is None when not pausing, or one of the condition names.
    """
    # Check node-level override first
    advance_mode = next_node.get("advance_mode", "inherit")
    if advance_mode == "pause":
        return True, "manual_gate"

    # Check workflow-level auto_advance
    if not workflow_def.get("auto_advance", False):
        return True, None  # not auto-advance, always pause (backward compat)

    # Evaluate pause conditions
    pause_conditions = workflow_def.get("pause_conditions", [])
    for condition in pause_conditions:
        if evaluate_condition(condition, state, next_node):
            return True, condition
    return False, None
```

**Step 2.5: Update existing workflow definitions**

File(s): All workflow definitions in `combine-config/workflows/`

Add `auto_advance: true` and default pause conditions to each active workflow definition:

```json
{
  "auto_advance": true,
  "pause_conditions": [
    "pgc_required",
    "classification_confirmation",
    "escalation_pending"
  ],
  "nodes": [...]
}
```

Existing nodes that should always pause get `"advance_mode": "pause"`.

**Step 2.6: Update SPA production floor**

File: `spa/src/` (production floor / pipeline view components)

When the active workflow has `auto_advance: true`:

- Stage action buttons MUST NOT render when `auto_advance` is true and the pipeline is not paused
- Replace stage "Generate" / "Run" action buttons with status indicators (running / complete / paused / blocked)
- Show the input form (PGC questions, classification confirmation, escalation resolution) only when the pipeline is paused — use `pause_reason` from the `pipeline:paused` SSE event to select the appropriate input panel
- Add a "Resume" button that appears only when the pipeline is paused (after operator input is provided)
- Keep the pipeline breadcrumb as-is — it already shows stage status
- The "Start Pipeline" button replaces individual stage triggers as the primary action

When `auto_advance` is false or absent:

- Existing behavior (manual stage buttons) — no change

### Phase 3: Verify

**Step 3.1:** Run all Phase 1 tests — all must pass.

**Step 3.2:** Run full Tier-1 suite — no regressions.

**Step 3.3:** Run a Hello World project through the pipeline with `auto_advance: true`. Verify:
- Pipeline advances automatically between stages
- Pipeline pauses on PGC questions
- Pipeline resumes after PGC answers are submitted
- Pipeline completes with all documents generated and no manual stage advancement

**Step 3.4:** Run a project that triggers the QA circuit breaker. Verify:
- Pipeline pauses on escalation
- Operator can resolve (retry or abandon)
- Pipeline resumes or terminates correctly

---

## SSE Event Contract

When the workflow engine changes pipeline execution state, it emits Server-Sent Events. The SPA subscribes to these events to update the production floor UI without polling.

### `pipeline:paused`

Emitted when auto-advance halts due to a pause condition or manual gate.

```json
{
  "event": "pipeline:paused",
  "data": {
    "project_id": "<project_id>",
    "workflow_id": "<workflow_id>",
    "node_id": "<next_node_id>",
    "pause_reason": "<pause_condition>",
    "timestamp": "<iso8601>"
  }
}
```

`pause_reason` values and corresponding SPA behavior:

| `pause_reason` | UI Action |
|----------------|-----------|
| `pgc_required` | Display PGC question form |
| `classification_confirmation` | Display classification selector |
| `escalation_pending` | Display escalation resolution panel |
| `manual_gate` | Display manual approval prompt |

### `pipeline:resumed`

Emitted when the pipeline resumes after operator input satisfies the pause condition.

```json
{
  "event": "pipeline:resumed",
  "data": {
    "project_id": "<project_id>",
    "workflow_id": "<workflow_id>",
    "node_id": "<next_node_id>",
    "timestamp": "<iso8601>"
  }
}
```

### `pipeline:progress`

Emitted when a node starts or completes during auto-advance execution.

```json
{
  "event": "pipeline:progress",
  "data": {
    "project_id": "<project_id>",
    "workflow_id": "<workflow_id>",
    "node_id": "<current_node_id>",
    "status": "running|complete",
    "timestamp": "<iso8601>"
  }
}
```

---

## Allowed Paths

```
app/domain/workflow/plan_executor.py
app/domain/workflow/plan_models.py      (if Node/workflow models need updating)
combine-config/workflows/               (workflow definitions)
seed/schemas/                           (workflow definition schema, if separate)
spa/src/                                (production floor components)
tests/tier1/workflow/
```

---

## Verification

- [ ] Workflow with `auto_advance: true` auto-advances between stages without manual triggers
- [ ] Workflow with `auto_advance: false` or absent behaves identically to current (no regression)
- [ ] Pipeline pauses on PGC questions (`pgc_required` condition)
- [ ] Pipeline pauses on classification confirmation (`classification_confirmation` condition)
- [ ] Pipeline pauses on escalation (`escalation_pending` condition)
- [ ] Per-node `advance_mode: "pause"` overrides DCW-level auto-advance
- [ ] `pgc_required` does NOT pause when next node has zero unresolved questions
- [ ] SPA shows status indicators instead of action buttons when auto-advance is active
- [ ] SPA shows input form only when pipeline is paused on a pause condition
- [ ] `pipeline:paused` SSE event includes correct `pause_reason` and `node_id`
- [ ] `pipeline:resumed` SSE event emitted on resume
- [ ] `pipeline:progress` SSE events emitted during auto-advance execution
- [ ] Hello World pipeline completes with ≤3 manual interactions (classification confirmation + PGC answers only)
- [ ] All existing Tier-1 tests pass (no regressions)

---

_Draft: 2026-03-06_
_Reviewed: 2026-03-08 (Claude + GPT-4 — tightened advance_mode, pause_conditions, dispatch semantics, SSE contract)_

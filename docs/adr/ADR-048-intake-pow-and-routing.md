# ADR-048: Intake POW and Workflow Routing

**Status:** Draft
**Created:** 2026-02-07
**Deciders:** Tom Moseley
**Context:** Concierge Intake architecture, POW spawning model

---

## Context

Currently, Concierge Intake is implemented as a Document Creation Workflow (DCW) that produces an intake artifact. Follow-on workflows (like `project_discovery`) declare `requires_inputs: ["concierge_intake"]` and consume this artifact.

This model has several limitations:

1. **Implicit routing**: The "what happens next" decision is buried in workflow graph edges, not an explicit governed step
2. **No universal front door**: Each workflow could theoretically have its own intake pattern
3. **DCW purity violation**: Intake isn't really "creating a document" — it's starting a project and deciding where to route it
4. **Lineage gaps**: No explicit record of "this POW was spawned from that intake"

The Concierge is the factory's front door. It should be modeled as such.

---

## Decision

### 1. Intake becomes a dedicated POW

Create a system-level Project Orchestration Workflow:

```
POW: intake_and_route
│
├── [1] DCW Step: Concierge Intake
│       Type: dcw_run
│       Ref: dcw:concierge_intake@1.0.0
│       Produces: artifact:intake_record@1.0.0
│
├── [2] Mechanical: Route Selection
│       Type: mechanical_op
│       Op: op:intake_route@1.0.0
│       Inputs: artifact:intake_record@1.0.0
│       Produces: artifact:routing_decision@1.0.0
│       Config:
│         min_confidence_to_auto_route: medium
│         routes:
│           explore_problem: pow:problem_discovery@1.0.0
│           plan_work: pow:software_product_delivery@1.0.0
│           change_existing: pow:migration_change@1.0.0
│           integrate_systems: pow:integration_delivery@1.0.0
│           unknown: pow:problem_discovery@1.0.0
│
├── [2b] (Optional) Entry: Confirm Route
│        Type: entry_op
│        Op: op:confirm_route@1.0.0
│        Condition: decision.confidence == "low"
│        Inputs: artifact:routing_decision@1.0.0
│        Produces: artifact:routing_decision@1.0.0 (with operator_confirmed: true)
│
├── [3] Mechanical: Spawn POW Instance
│       Type: mechanical_op
│       Op: op:spawn_pow_instance@1.0.0
│       Inputs: artifact:routing_decision@1.0.0, artifact:intake_record@1.0.0
│       Produces: artifact:spawn_receipt@1.0.0
│       Returns: child_execution_id
│       Emits: POW_SPAWNED project event
│
└── [4] Terminal
        Type: end
        Outcome: routed
```

This POW:
- Takes raw operator intent as input
- Produces a canonical intake artifact (traced, replayable)
- Makes an explicit routing decision (which follow-on POW to spawn)
- Optionally pauses for operator confirmation if confidence is low
- Spawns the follow-on POW instance and completes

### 2. Complete-and-handoff spawning model

The Intake POW **completes** when it spawns the follow-on. It does not suspend or transform.

Lineage is maintained via references:

```
Project
├── executions: [exec-001, exec-002, ...]
│
├── exec-001 (Intake POW)
│   ├── workflow_ref: intake_and_route
│   ├── terminal_outcome: routed
│   └── produced: intake_artifact, routing_decision
│
└── exec-002 (Follow-on POW)
    ├── workflow_ref: software_product_development
    ├── spawned_from_execution_id: exec-001
    ├── spawned_by_operation_id: spawn_pow_instance
    └── initial_inputs:
        ├── intake_artifact_ref: doc-xxx
        └── routing_decision_ref: doc-yyy
```

**Forward references**: Follow-on POW's `initial_inputs` point to intake artifacts
**Backward references**: `spawned_from_execution_id` and `spawned_by_operation_id`
**Timeline**: Project's `executions[]` array maintains order

### 3. Routing decision schema

The `routing_decision.v1` artifact captures the decision with full audit trail:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://thecombine.dev/schemas/routing_decision.v1.json",
  "title": "RoutingDecisionV1",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "correlation_id", "source_intake_ref", "decision", "candidates", "qa"],
  "properties": {
    "schema_version": { "type": "string", "const": "routing_decision.v1" },
    "correlation_id": { "type": "string", "format": "uuid" },
    "source_intake_ref": {
      "type": "string",
      "description": "Artifact ref/id for the intake_record used to produce this decision."
    },
    "decision": {
      "type": "object",
      "required": ["next_pow_ref", "confidence", "reason"],
      "properties": {
        "next_pow_ref": { "type": "string", "minLength": 3, "maxLength": 160 },
        "confidence": { "type": "string", "enum": ["low", "medium", "high"] },
        "reason": { "type": "string", "minLength": 3, "maxLength": 240 },
        "operator_confirmed": { "type": "boolean", "default": false },
        "confirmation_note": { "type": ["string", "null"], "maxLength": 240 }
      }
    },
    "candidates": {
      "type": "array",
      "minItems": 1,
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": ["pow_ref", "score", "why"],
        "properties": {
          "pow_ref": { "type": "string" },
          "score": { "type": "number", "minimum": 0, "maximum": 1 },
          "why": { "type": "string", "maxLength": 180 }
        }
      }
    },
    "qa": {
      "type": "object",
      "required": ["has_winner", "winner_in_candidates"],
      "properties": {
        "has_winner": { "type": "boolean", "const": true },
        "winner_in_candidates": { "type": "boolean", "const": true }
      }
    }
  }
}
```

**Design notes:**
- Keeps decision defensible (reason + candidates list)
- Mechanically checkable (qa.winner_in_candidates must be true)
- Avoids premature taxonomy fields
- Leaves room for operator confirmation without forcing it

### 4. Spawn operation

A new mechanical operation type: `pow_spawner`

```yaml
op_id: spawn_pow_instance
type: pow_spawner
config:
  seed_inputs:
    - name: intake_record
      from_artifact: source_intake_ref
    - name: routing_decision
      from_artifact: self
  write_project_event: true
```

This operation:
1. Resolves the target POW reference from `routing_decision.decision.next_pow_ref`
2. Creates a new POW execution instance in the database
3. Wires initial inputs (intake_record + routing_decision)
4. Records lineage references
5. Emits project event: `POW_SPAWNED`
6. **Returns `child_execution_id`** so UI can immediately jump to spawned POW

The spawned POW execution begins in `pending` state, ready for the next `execute_step` call.

### 5. UX: Intake receipt

In the project history view, completed Intake POW appears as a collapsed receipt:

```
┌─────────────────────────────────────────────────────────┐
│ ✓ Intake & Routing                                      │
│   → spawned Software Product Development v1.0.0         │
│   2026-02-07 14:32                              [expand] │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ● Software Product Development                   [active] │
│   Step 3 of 8: Project Discovery                        │
│   ...                                                   │
└─────────────────────────────────────────────────────────┘
```

Expanding the receipt shows:
- Intake summary (what the operator described)
- Routing decision (which POW and why)
- Candidates considered (with scores)
- Link: "Open spawned workflow"

**Transition UX**: Because `spawn_pow_instance` returns `child_execution_id`, the UI can immediately jump to the spawned POW without a second lookup. The receipt → active workflow transition feels instant while preserving execution separation.

---

## Consequences

### Positive

1. **Explicit routing**: Routing is a governed mechanical operation, not implicit graph traversal
2. **Universal front door**: One intake POW for all projects, routes to N specialized POWs
3. **Clean DCWs**: Document workflows consume known inputs, don't make routing decisions
4. **Full lineage**: Every project has traced, replayable intake record with spawn chain
5. **Scalable**: Add new follow-on POWs without touching intake logic (just routing rules)

### Negative

1. **Two executions per project minimum**: Intake + follow-on (but this is correct — they are distinct)
2. **New operation type**: `pow_spawner` must be implemented
3. **Routing logic location**: Must decide where routing rules live (LLM? mechanical? config?)

### Neutral

1. **Existing intake DCW reused**: The `concierge_intake` DCW (with Gate Profile) becomes the first step of the Intake POW
2. **Project model extension**: Need `executions[]` array and lineage fields on POW instances

---

## Alternatives Considered

### A. Intake as embedded gate in every POW

Current implicit model. Rejected because:
- No universal intake record
- Routing is implicit
- Each POW could invent its own intake pattern

### B. Intake POW suspends while child runs

Intake POW stays "active" as parent, awaits child completion. Rejected because:
- Complicates execution state management
- Two active executions for one project
- Intake has nothing to do while waiting

### C. Intake POW transforms into follow-on

Graph replacement — Intake POW "becomes" the follow-on. Rejected because:
- Loses intake execution as distinct audit record
- Complex state transformation
- Confusing execution identity

---

## Implementation Notes

### Phase 1: Foundation
- Add `spawned_from_execution_id` and `spawned_by_operation_id` fields to POW execution model
- Add `executions[]` to Project model
- Create `routing_decision` schema

### Phase 2: Spawn Operation
- Implement `pow_spawner` mechanical operation type
- Wire lineage tracking
- Handle initial_inputs mapping

### Phase 3: Intake POW Definition
- Create `intake_and_route` POW definition
- Include existing `concierge_intake` DCW as first step
- Add routing decision step (LLM or mechanical TBD)
- Add spawn step

### Phase 4: UX
- Implement collapsed receipt view in project history
- Show spawn chain visualization
- Link between intake and spawned POW

---

## Resolved Questions

1. **Routing logic**: Mechanical (config-driven mapping table). Routes map `intent_class` → `next_pow_ref`. Confidence thresholds trigger optional operator confirmation.

2. **Multiple follow-on POWs**: No. One intake → one follow-on. Additional POWs spawn from the follow-on if needed.

3. **Re-routing**: Abandon current POW, spawn new one from same immutable intake artifact. Chain is recorded.

4. **Spawn handoff model**: Complete-and-handoff (Option 1). Intake POW completes with `routed` outcome, spawned POW is distinct execution.

## Open Questions

1. **Route confirmation threshold**: What confidence level triggers the optional `confirm_route` entry op?
   - Proposal: `low` triggers confirmation, `medium` and `high` auto-proceed

2. **POW catalog**: Where do available POW refs live? Hard-coded in op config or dynamic lookup?
   - Proposal: Start with config, add registry later if needed

---

## References

- ADR-039: Document Interaction Workflow Plans
- ADR-047: Mechanical Operations Framework
- WS-ADR-047-005: Concierge Intake Gate Refactoring (Gate Profile implementation)

---

*End of ADR-048*

# ADR-038 - Workflow Plan Schema

**Status:** Accepted
**Date:** 2026-01-15
**Decision Type:** Architectural / Governance

**Related ADRs:**
- ADR-037 - Concierge-Constrained Workflow Routing
- ADR-036 - Document Lifecycle & Staleness
- ADR-035 - Durable LLM Threaded Queue (Draft)

---

## Context

The Combine executes work via multi-step pipelines (workflows) that:

- Coordinate Concierge interactions
- Invoke reusable role tasks
- Enforce QA, consent, and lifecycle rules
- Support branching and governed conversational loops

Earlier implementations encoded workflow logic:

- directly in code
- implicitly inside role tasks
- or weakly via each step decides what is next

This caused:

- tight coupling between tasks and workflows
- inconsistent routing behavior
- difficulty enforcing ADR-037 constraints
- poor auditability and reuse

A data-driven workflow plan is required to define the legal execution graph, expose allowed transitions as options, and keep routing authority engine-owned.

---

## Decision

The Combine SHALL represent workflows as explicit data-defined graphs, called Workflow Plans.

Workflow Plans:

- are stored in the database
- are versioned
- are immutable once active
- define legality, not behavior

The filesystem is not the system of record for workflow plans.

---

## Core Principles

**Workflow Plans define legality, not behavior**
They declare what may happen, not how it happens.

**Steps do not route**
Steps emit outcomes; plans define where those outcomes may lead.

**Concierge chooses only from plan-derived options**
Per ADR-037, the plan is the source of truth for possible next actions.

**Minimal expressiveness**
- No scripting
- No embedded code
- No content inspection
- No LLM reasoning inside conditions

**Sequential execution only**
Workflow Plans define sequential execution graphs. Parallel or concurrent node execution is not supported.

---

## Workflow Plan Storage (Explicit Decision)

### Authoritative Storage

Workflow Plans SHALL be stored in the database.

Database storage is the sole authoritative source for runtime workflow plans.

Filesystem-based JSON representations MAY exist only for:
- bootstrap
- migration
- testing
- documentation

They MUST NOT be used at runtime.

### Versioning and Immutability

- Each Workflow Plan is versioned.
- A project references a specific workflow_plan_id.
- Once a workflow plan version is marked active, it MUST be treated as immutable.
- Changes require creation of a new workflow plan version.
- No in-place mutation of active plans is permitted.

### Database Table Sketch (Reference)

**workflow_plan**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| workflow_key | TEXT | Logical identifier (e.g., project_discovery) |
| version | TEXT or INT | Version identifier |
| status | ENUM | draft, active, deprecated |
| entry_node_ids | JSONB | Array of node IDs |
| plan_json | JSONB | Full workflow graph definition |
| created_at | TIMESTAMP | |
| created_by | TEXT / UUID | |
| notes | TEXT | Optional |
| hash | TEXT | Optional integrity / tamper detection |

### Storage Invariants

- (workflow_key, version) MUST be unique.
- Only one active version per workflow_key is allowed at a time.
- Projects MUST reference a concrete workflow_plan_id, not a (key, version) pair.
- Active plans MUST NOT be updated in place (enforced by application logic and/or DB constraints).
---

## Workflow Plan Structure (Logical)

A Workflow Plan defines:

- workflow_id
- version
- entry_node_ids[]
- nodes[]
- edges[]
- optional metadata

The structure is stored as validated JSON within plan_json.

### Entry Point Semantics (MVP Constraint)

- Workflow Plans MAY define one or more entry nodes via entry_node_ids[].
- For MVP, workflows SHOULD define exactly one entry node.
- Support for multiple entry points is intentionally reserved for future patterns, such as:
  - resuming execution from a saved checkpoint
  - re-entering a workflow after interruption or failure
  - administrative or recovery entry paths

The use of entry_node_ids[] is deliberate future-proofing and does not imply that multi-entry execution is required or supported in MVP.

---

## Nodes

A node represents a single executable step.

### Required Fields

- **node_id** - stable identifier
- **type** - one of: concierge, task, qa, gate, end
- **task_ref** - required for task and qa types

### Optional Fields

- **produces** - artifact type(s) this node may produce
- **requires_consent** - boolean
- **requires_qa** - boolean
- **non_advancing** - boolean
- **description** - human-readable intent

### Node Invariants

- Nodes MUST NOT reference other nodes.
- Nodes MUST NOT encode routing logic.
- Nodes MAY be reused across multiple workflow plans.

---

## Edges

An edge defines a legal transition.

### Required Fields

- **edge_id** - stable identifier
- **from_node_id**
- **outcome** - step outcome that enables this edge

### Optional Fields

- **to_node_id** - nullable for non-advancing edges
- **label** - user-facing summary
- **kind** - auto or user_choice
- **priority** - hint for ordering and recommendations
- **conditions** - simple predicates evaluated by the engine

### Non-Advancing Edge Semantics

- to_node_id = null indicates control remains at the current node.
- to_node_id = from_node_id MAY be used as an explicit self-loop.
- Both are treated as non-advancing.

---

## Outcomes

Nodes emit standardized outcomes, including:

- **success** - step completed successfully
- **needs_user_input** - progress blocked pending user input
- **needs_consent** - consent required before proceeding
- **failed** - step failed
- **blocked** - step cannot proceed due to preconditions
- **no_change** - step completed but produced no state transition

Edges bind to outcomes, not to node internals.
---

## Conditions

Conditions MAY reference only:

- artifact presence / absence
- staleness (per ADR-036)
- consent or QA completion
- workflow-local flags

Conditions MUST NOT:

- execute code
- inspect document content
- depend on LLM reasoning

### Workflow-Local Flags

Flags MAY be set by:

- step outcomes (engine-owned)
- Concierge context updates

Names and semantics are workflow-specific.

Plans MAY reference flags but MUST NOT define executable logic.

---

## Terminal Semantics

A workflow is complete when:

- execution reaches a node of type end, or
- a node has no outbound edges whose conditions evaluate true for its possible outcomes

A node with no valid outbound edges is implicitly terminal.

---

## Option Derivation (ADR-037 Alignment)

The Step Engine derives available_options[] by:

1. Selecting edges whose:
   - from_node_id matches current node
   - outcome matches emitted outcome
   - conditions evaluate true

2. Mapping edges to user-visible options per ADR-037

3. Using priority as a hint for ordering and recommendations

Workflow Plans SHOULD include non-advancing options (e.g., ask_more_questions) at decision points.

---

## Consequences

### Positive

- Durable, auditable workflows
- Strong governance boundaries
- Reusable role tasks
- Safe agentic routing
- Supports future visualization and tooling

### Tradeoffs

- Requires explicit workflow authoring discipline
- Expressiveness is intentionally constrained
- Workflow changes require versioning, not edits

These tradeoffs are intentional.

---

## Non-Goals

This ADR does NOT:

- Define Step Engine internals
- Define role task schemas
- Enable dynamic workflow synthesis
- Support parallel execution
- Introduce runtime-editable workflows
- Encode retry counters or loop-breaking logic in workflow plans


---

## Implementation Notes

### Circuit Breaker on QA Rework Loops (Engine-Owned)

Workflow Plans intentionally do not encode retry counters or loop-breaking logic.
The Step Engine MUST enforce an engine-owned circuit breaker to prevent infinite QA -> rework cycles.

- max_retries = 2 (MVP default)
- When tripped, the engine exposes escalation options consistent with ADR-037.
- The workflow plan schema remains unchanged; plans stay declarative and static.
- The system MUST record a full audit trail including retry counts, breaker activation, options offered, and the option selected.
---

## Summary

ADR-038 establishes Workflow Plans as:

- database-stored
- versioned
- immutable once active
- declarative graphs
- engine-interpreted
- aligned with ADR-037 routing constraints

This locks workflow legality into durable, auditable artifacts while preserving conversational flexibility and role-task reuse.

**The graph is the law. The database is the record. The engine is the enforcer.**
# ADR-037 - Concierge-Constrained Workflow Routing

**Status:** Accepted
**Date:** 2026-01-15
**Decision Type:** Architectural / Governance
**Supersedes:** None

**Related ADRs:**
- ADR-035 - Durable LLM Threaded Queue (Draft)
- ADR-036 - Document Lifecycle & Staleness (Accepted)

---

## Context

The Combine executes work through multi-step pipelines involving:

- Conversational guidance (Concierge)
- Role-based artifact generation
- QA and other governance gates
- Document lifecycle management (including staleness)

Early patterns allowed steps/roles to implicitly determine what comes next, via hard-coded sequencing or weak routing semantics. This created risks:

- Hidden coupling between tasks and workflows
- Drift and inconsistent behavior across workflows
- Governance bypass risk (QA, consent, staleness)
- Agentic overreach (helpful but unauthorized transitions)

At the same time, the Concierge adds significant value when it can guide, recommend, and adapt to user answers - provided its authority is bounded.

---

## Decision

**Workflows define what is possible.**
**The Step Engine enforces legality.**
**The Concierge chooses only from engine-provided options.**

Specifically:

- The Step Engine SHALL provide an explicit, finite list of available_options[] at decision points.
- The Concierge MAY select, recommend, or present options to the user, but MUST select only from available_options[].
- The Concierge MUST NOT invent options, skip gates, or transition to unlisted steps.
- Workflow plans SHOULD include a non-advancing option (e.g., ask_more_questions) at decision points to preserve conversational flow while keeping movement governed.

---

## Architectural Invariants

### 1. Engine-Owned Routing Authority

The Step Engine is the sole authority on:

- Which steps are available now
- Which transitions are legal
- Which preconditions apply (QA, consent, staleness, dependencies)

Routing is owned by workflow plans (data-driven graphs of steps/edges), not by role tasks.

### 2. Concierge as Constrained Router

The Concierge:

- Receives available_options[] from the Step Engine

**MAY:**
- Select one option
- Recommend among options
- Ask the user to choose
- Choose a non-advancing ask more questions option when available

**MUST:**
- Choose only from available_options[]

**MUST NOT:**
- Create or mutate options
- Bypass required gates
- Jump to steps not exposed by the engine
- Reinterpret or embellish option effects beyond contract data

If no valid option exists, the Concierge MUST return a non-advancing outcome (e.g., needs_system_intervention) and must not improvise.

### 3. Ask More Questions Option

To preserve conversational flow while keeping movement governed:

- Workflow plans SHOULD include a non-advancing option at meaningful decision points (e.g., option_id = ask_more_questions)
- Selecting this option SHALL NOT advance the workflow graph to downstream artifacts
- Selecting this option MAY update workflow state/context (e.g., captured answers), which MAY affect future option availability

This enables: We are not ready to choose a branch yet - let us clarify. ...without letting Concierge invent new routes.
### 4. Explicit Option Contract

Each engine-provided option MUST include sufficient metadata to prevent interpretation drift.

**Minimum fields:**

| Field | Description |
|-------|-------------|
| option_id | Stable identifier |
| label | User-facing short name |
| description | User-facing explanation |
| target_step_id | Engine-internal; MAY be null for non-advancing options |
| eligibility | eligible or blocked |
| blockers[] | Reasons if blocked |
| kind | auto, user_choice, or blocked |
| requires_consent | Boolean |
| effects_summary | User-facing summary of what will occur if chosen |

The Concierge MUST present option effects using only the provided metadata, without embellishment or reinterpretation.

### 5. Staleness Interaction

When upstream documents are stale (per ADR-036), the Step Engine MUST reflect staleness in the option list by one or more of:

- Marking downstream options as blocked with an explicit staleness entry in blockers[]
- Keeping options eligible but including an explicit warning in effects_summary

The Step Engine MAY decide which behavior applies per workflow, but it MUST be explicit in option eligibility and/or blockers.

### 6. Consent Mechanics

Options may be marked requires_consent = true. ADR-037 does not mandate the exact consent implementation, but it establishes the governance requirement:

- A consent requirement MUST be enforced before executing the effects of the chosen option.

Acceptable enforcement patterns include (non-exhaustive):
- Concierge collects explicit consent prior to invoking the engine choose option
- Engine returns a needs_consent outcome when attempting to execute the option

Implementation details are specified in workflow/engine contracts.

### 7. Workflow Change Mid-Flight

Workflow reassignment is a real scenario but is intentionally constrained:

- If workflow change is supported, it MUST occur only through an engine-provided option (e.g., change_workflow) or an engine-owned administrative mechanism.
- The Concierge MUST NOT reassign workflows implicitly or by invention.

(If unsupported in MVP, workflows are immutable after creation; this remains compatible with this ADR.)

---

## Selection Rules

| Scenario | Concierge Behavior |
|----------|-------------------|
| Single eligible auto option | Select automatically (optionally narrating) |
| Multiple eligible user_choice options | Present choices to user; MAY recommend; MUST NOT auto-select without confirmation |
| All options blocked | Explain blockers using provided data; MAY ask for unblocking input; MUST NOT proceed otherwise |
| User requests unavailable action | Explain action is not available; MAY suggest closest available option(s); MAY route to restart/change-workflow only if exposed by engine |

---

## Consequences

### Positive

- Strong governance guarantees (QA/consent/staleness cannot be bypassed by chat)
- True task reuse across workflows (tasks do not encode routing)
- Auditability: options offered + option selected is durable evidence
- Safe agentic behavior: judgment within explicit boundaries

### Tradeoffs

- Workflows must be explicit enough to produce meaningful options
- Concierge intelligence is constrained by option quality
- Requires careful UX for user-choice branches

---

## Non-Goals

This ADR does not:

- Define the workflow plan schema (separate contract/ADR)
- Define Step Engine internal processing mechanics
- Enable free-form agentic planning or workflow synthesis
- Define a full workflow marketplace or dynamic workflow authoring

---

## Implementation Notes

Logging MUST record:

- The full available_options[] snapshot presented at decision time
- The chosen option_id
- Whether selection was automatic, recommended, or user-confirmed
- Whether staleness or consent affected eligibility

### Circuit Breaker on Rework Loops

To prevent infinite QA -> rework -> QA loops, the Step Engine MUST enforce an engine-owned circuit breaker.
This policy is not expressed in the workflow plan.

- max_retries = 2 (MVP default)
- Retries are tracked per (project_id, generating_node_id) for consecutive QA failures that route to rework.
- When the circuit breaker trips, the Step Engine MUST expose escalation options via the ADR-037 available_options[] contract.
- The Concierge remains constrained to selecting only from the provided option list.
- The system MUST record a full audit trail including retry counts, breaker activation, options offered, and the option selected.
---

## Summary

ADR-037 establishes a hard boundary:

- The workflow graph defines legality
- The engine exposes the legal option set
- The Concierge selects only from that set, including a governed ask more questions non-advancing option
- Staleness and consent are reflected and enforced through explicit options and outcomes

**The law is the graph. The Concierge is the judge - within the law.**
---

## Amendment: Dynamic Kind Determination for Gate Options

**Added:** 2026-01-19
**Context:** Outcome gates following document QA (e.g., Intake Gate per ADR-025)

### Problem

ADR-037 defines `kind` as a static property on edges/options (`auto`, `user_choice`, `blocked`). This forces a choice:

- Always auto-route (loses governance)
- Always require user selection (creates friction for clear cases)

Neither serves expert users or defensible governance well.

### Decision

The Step Engine MAY dynamically compute option `kind` at runtime based on document contract signals, rather than relying solely on static edge definitions.

For outcome gates following document QA, the engine SHALL evaluate:

| Signal | Source | Purpose |
|--------|--------|---------|
| `qa_pass` | QA node outcome | Structural validity |
| `confidence` | Document contract field | Intent clarity |
| `intent_class` | Document contract field | Recognized vs unknown |
| `missing_critical` | Document contract field | Completeness |

### Auto-Qualification Rule

The engine SHALL auto-select `qualified` (kind = `auto`) when ALL of:

- `qa_pass == true`
- `confidence >= 0.8`
- `missing_critical == false`
- `intent_class` is recognized (not `unknown` or `mixed`)

### User-Choice Presentation Rule

When auto-qualification criteria are NOT met, the engine SHALL:

1. Set `kind = user_choice`
2. Pre-select a recommended outcome based on available signals
3. Display 1-2 supporting reasons for the recommendation
4. Offer easy override via alternate options

**Example presentation:**

```
Recommended: Qualified
Because: QA passed; intent confidence 0.85; required fields present.
[Proceed] [Change outcome â–¼]
```

This reduces cognitive load while preserving the governance checkpoint.

### Signals That Trigger User-Choice

The engine SHALL require user selection when ANY of:

- `confidence < 0.8`
- `missing_critical == true`
- `intent_class` is `unknown` or `mixed`
- QA passed structurally but flagged semantic uncertainty
- Downstream step is high-cost (e.g., full architecture generation)
- Policy risk indicators present

### Governance Invariants

- Auto-qualification MUST be logged with full signal values
- User override of recommendations MUST be logged
- The Andon cord (manual override) is always available
- QA validates structure, not truth — gate decisions are driven by document contract signals

### Audit Requirements

The system MUST record:

- All signal values evaluated at gate decision time
- Whether `kind` was computed as `auto` or `user_choice`
- The recommended outcome (if user_choice)
- The actual outcome selected
- Whether user overrode the recommendation

### Non-Goals

This amendment does NOT:

- Allow Concierge to compute `kind` (engine-owned)
- Replace QA validation (QA remains one input among several)
- Enable content inspection beyond declared contract fields
- Permit confidence thresholds to be workflow-defined (engine policy)

### Summary

Dynamic kind determination enables the system to:

- Auto-qualify when signals are unambiguous
- Pause for human judgment when signals are uncertain
- Present recommendations that reduce friction without removing control

**The gate remains governance. The signals determine friction.**

---

## Amendment: Scope Clarification (2026-01-22)

**Context:** ADR-037 defines the `available_options[]` contract for Concierge-constrained routing. This pattern applies to decision-heavy workflows, not all workflows.

**Scope Clarification:**

ADR-037 **applies to**:
- Project Discovery (ambiguity resolution, branching paths)
- Architecture decisions (options and tradeoffs)
- Planning workflows (scope decisions, prioritization)
- Any workflow where user must choose between legitimate alternatives

ADR-037 **does not apply to**:
- Intake qualification (mechanical sufficiency, not options selection)
- Linear execution workflows (no branching decisions)
- Auto-completing workflows (QA pass → done)

**Rationale:**

The `available_options[]` contract is valuable when:
1. Multiple legitimate paths exist
2. User judgment is required to select
3. Selection has governance implications

Intake qualification does not meet these criteria. Intake determines whether intent is sufficiently bounded, not which of several paths to take.

**Implementation Note:**

The Concierge Intake workflow (`concierge_intake.v1.json`) uses:
- Mechanical sufficiency checks (not options selection)
- Auto-routing on field completion
- User consent via Lock action (not options contract)

This is intentional and correct. The full ADR-037 pattern will apply to Discovery and Architecture workflows.

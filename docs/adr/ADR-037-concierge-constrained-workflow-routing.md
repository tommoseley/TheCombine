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
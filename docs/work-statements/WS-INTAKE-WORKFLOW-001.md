# WS-INTAKE-WORKFLOW-001: Concierge Intake Document Workflow Plan

**Status:** Draft
**Date:** 2026-01-16
**Scope:** Single-commit (workflow plan artifact only)
**Related ADRs:** ADR-025, ADR-035, ADR-036, ADR-037, ADR-038, ADR-039

---

## Objective

Define and implement a reference **Concierge Intake Document Workflow Plan** as the first concrete implementation of ADR-039 (Document Interaction Workflow Model).

This workflow plan governs the creation of the Concierge Intake Document while respecting the governance boundary defined in ADR-025.

---

## Deliverables

1. `seed/workflows/concierge_intake.v1.json` - Workflow plan per ADR-038 schema
2. Unit tests validating workflow plan structure
3. Documentation of node types, edges, and terminal outcome mapping

---

## Architectural Constraints

### 1. Thread Ownership (ADR-035)

The Intake Document Workflow SHALL own a Durable LLM Thread (ADR-035).

- **ADR-035** = interaction history (messages)
- **Workflow execution** = control state (current node, transitions)

The workflow MUST NOT reinvent conversation state. It owns a thread; it does not duplicate one.

### 2. Governance Boundary Enforcement (ADR-025)

The Intake Gate is a governance boundary, not a chat UX feature.

Downstream document creation MUST check:
- Intake Gate outcome = `qualified`
- Intake document is `stabilized` (execution) AND `accepted` (lifecycle)

Fail fast if not. No inference. No "best effort."

### 3. Authoritative Outcome Mapping

Gate outcome (ADR-025 governance vocabulary) is authoritative.

Workflow terminal outcome (ADR-039 execution vocabulary) is mapped deterministically:

| Gate Outcome | Workflow Terminal |
|--------------|-------------------|
| `qualified` | `stabilized` |
| `not_ready` | `blocked` |
| `out_of_scope` | `abandoned` |
| `redirect` | `abandoned` |

This mapping is enforced by the workflow; it is not inferred at query time.

Both outcomes are recorded. They MUST NOT drift.

### 4. Explicit Consent

Consent SHALL be captured explicitly before:
- Writing a stable intake artifact, OR
- Starting downstream generation

Implementation options:
- Explicit "Proceed" CTA node
- "I consent" gate step in workflow

Consent MUST NOT be a hidden implicit side-effect.

### 5. Staleness Handling (ADR-036)

If Intake becomes stale, the system MUST NOT silently re-enter intake.

Staleness surfaces as:
- Downstream options blocked with clear blocker reason
- Explicit "refresh intake" option (non-advancing until complete)

No automatic re-entry. No silent regeneration.

### 6. Circuit Breaker (max_retries = 2)

Engine-owned circuit breaker applies to:
- QA failures on intake document
- Regeneration loops on intake document

When tripped, engine offers escalation options (per ADR-037):
- Ask more questions
- Narrow scope
- Switch intent class
- Abandon/redirect

### 7. Structured Output (Not Transcript)

The Concierge Intake Document is a structured, governed summary.

- MAY link to thread evidence (ADR-035)
- MUST NOT be raw chat dumped into a document
- Schema is governed per ADR-025 Section 7

---

## Workflow Plan Structure (Reference)

```
Nodes:
  - start
  - clarification (concierge node, owns thread)
  - consent_gate (gate node)
  - generation (task node)
  - qa (qa node)
  - remediation (task node, loops to qa)
  - outcome_gate (gate node, determines gate outcome)
  - end_stabilized
  - end_blocked
  - end_abandoned

Edges:
  start -> clarification
  clarification -> consent_gate
  consent_gate [proceed] -> generation
  consent_gate [not_ready] -> end_blocked
  generation -> qa
  qa [pass] -> outcome_gate
  qa [fail, retries < max] -> remediation
  qa [fail, retries >= max] -> end_blocked (circuit breaker)
  remediation -> qa
  outcome_gate [qualified] -> end_stabilized
  outcome_gate [not_ready] -> end_blocked
  outcome_gate [out_of_scope] -> end_abandoned
  outcome_gate [redirect] -> end_abandoned
```

---

## Prohibited Actions

- DO NOT create a separate "intake conversation state machine" (use ADR-035 threads)
- DO NOT allow downstream to proceed without `qualified` + `stabilized` + `accepted`
- DO NOT make consent implicit
- DO NOT auto-re-enter intake on staleness
- DO NOT store raw transcript as the intake document
- DO NOT allow gate outcome and workflow terminal to drift

---

## Verification

1. Workflow plan validates against ADR-038 schema
2. All nodes have defined types per ADR-039
3. Terminal outcomes map correctly to gate outcomes
4. Circuit breaker edges present
5. Consent gate is explicit
6. Thread ownership declared (not inline state)

---

## Acceptance Criteria

- [ ] `seed/workflows/concierge_intake.v1.json` exists and validates
- [ ] Unit tests pass for workflow plan structure
- [ ] Outcome mapping is deterministic and documented
- [ ] No prohibited patterns present
- [ ] Ready for engine integration (separate work statement)

---

## Non-Goals

This work statement does NOT include:
- Engine execution of the workflow (future WS)
- UI/UX for intake conversation
- Thread persistence implementation (ADR-035 scope)
- Downstream document workflow plans

---

## Summary

WS-INTAKE-WORKFLOW-001 delivers the reference Concierge Intake Document Workflow Plan.

It demonstrates:
- ADR-039 document interaction workflow pattern
- ADR-025 governance boundary as execution model
- ADR-035 thread ownership (not reinvention)
- Deterministic outcome mapping
- Explicit consent and circuit breaker mechanics

This is the first concrete instantiation of the document-centric execution model.

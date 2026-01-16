# ADR-039 — Document Interaction Workflow Model

**Status:** Draft
**Date:** 2026-01-16
**Decision Type:** Architectural / Structural

**Related ADRs:**
- ADR-012 — Interaction Model
- ADR-014 — Quality Assurance Modes
- ADR-025 — Intake Gate
- ADR-035 — Durable LLM Threaded Queue
- ADR-036 — Document Lifecycle & Staleness
- ADR-037 — Concierge-Constrained Workflow Routing
- ADR-038 — Workflow Plan Schema

---

## Context

The Combine produces and maintains **documents as first-class, durable artifacts** (e.g., Intake, Discovery, Architecture, Backlogs).

Creating or refining a document is not a single action. It typically involves:

- conversational clarification
- one or more generation attempts
- quality assurance
- remediation and rework
- eventual stabilization or escalation

Historically, these interactions were modeled implicitly inside project workflows or step implementations, causing:

- repetition of the same question → generation → QA loop
- leakage of document concerns into project workflows
- inconsistent QA and remediation behavior
- difficulty enforcing gates such as ADR-025 (Intake)

A structural model is required to make document creation and refinement explicit, reusable, and governable.

---

## Decision

The Combine SHALL treat **each document as having its own document-scoped workflow**, called a **Document Interaction Workflow**.

A Document Interaction Workflow:

- governs the lifecycle of a *single document instance*
- is implemented as a workflow plan (per ADR-038)
- internally uses the interaction mechanics of ADR-012
- internally applies QA modes defined in ADR-014
- MAY own one or more Durable LLM Threads (ADR-035)
- produces a terminal document outcome consumed by project workflows

Document Interaction Workflows are **nested execution units**, distinct from project-level workflows.

---

## Core Principles

1. **Documents are living artifacts**
   A document may require multiple interactions before stabilizing.

2. **Document workflows are self-contained**
   Questioning, generation, QA, and rework loops belong to the document, not the project.

3. **Projects orchestrate documents**
   Project workflows invoke document workflows and react only to their terminal outcomes.

4. **Mechanics are reused, not redefined**
   - ADR-012 defines *how* interactions occur
   - ADR-014 defines *how* quality is judged
   - ADR-039 defines *where* those mechanics apply

---

## Scope

### In Scope
- Document-scoped workflows
- Multi-call execution (questioning → generation → QA → remediation)
- Document terminal outcomes
- Relationship between document workflows and project workflows
- Concierge participation within document workflows

### Out of Scope
- Interaction mechanics (ADR-012)
- QA policy or strictness (ADR-014)
- Workflow schema definition (ADR-038)
- Step routing constraints (ADR-037)
- Parallel document execution semantics

---

## Document Interaction Workflow Structure

A Document Interaction Workflow:

- is defined using the Workflow Plan Schema (ADR-038)
- is executed against a **single document instance**
- is persisted using the same workflow execution infrastructure as project workflows
- is scoped to a `document_id` rather than a `project_id`
- may contain internal loops
- MUST eventually reach a terminal outcome

### Typical Node Types
- `concierge` — clarification and questioning
- `task` — document generation or revision
- `qa` — document validation
- `gate` — consent or readiness checks
- `end` — terminal state

---

## Standard Document Lifecycle Phases (Conceptual)

While not mandated, most document workflows follow this pattern:

1. **Clarification** — Concierge-led questioning (ADR-012)
2. **Generation** — LLM-based document creation
3. **Quality Assurance** — QA per ADR-014
4. **Remediation** — Rework based on QA or user feedback
5. **Stabilization** — Document accepted as valid and usable

These phases may repeat internally but are opaque to the project workflow.

---

## Relationship to Document Lifecycle & Staleness (ADR-036)

Document Interaction Workflow state and Document Lifecycle state are **orthogonal**.

- Workflow execution state reflects *how a document is being produced*
- Lifecycle state reflects *the admissibility and freshness of the document artifact*

Rules:

- A workflow reaching `stabilized` MAY transition the document lifecycle state to `accepted`
- Document staleness does NOT automatically restart a document workflow
- Regeneration due to staleness SHALL be performed by initiating a new Document Interaction Workflow instance

---

## Terminal Outcomes

A Document Interaction Workflow MUST conclude with exactly one of the following terminal outcomes:

- `stabilized`
  Document is complete, accepted, and admissible downstream.

- `blocked`
  Progress cannot continue without external intervention (e.g., missing information, consent denial, policy constraints).

- `abandoned`
  Document creation intentionally halted.

Unexpected execution failures (e.g., infrastructure or engine faults) are not terminal outcomes and are handled by engine-level retry and recovery mechanisms. Persistent failures MAY surface as `blocked`.

---

## Relationship to Project Workflows

- Project workflows invoke Document Interaction Workflows as atomic steps
- Project workflows MUST NOT:
  - manage internal document loops
  - interpret intermediate document states
  - bypass document QA or stabilization

- Project workflows MAY:
  - branch based on document terminal outcomes
  - halt execution if required documents are blocked or abandoned

Documents do not directly advance project state.

---

## Concierge Participation

- The Concierge MAY participate within a Document Interaction Workflow
- Concierge actions remain constrained by ADR-037
- Document workflows MAY expose non-advancing clarification options (e.g., ask more questions)

The Concierge does not control project progression directly from within a document workflow.

---

## QA Integration

- QA nodes within document workflows apply QA modes defined in ADR-014
- QA failures and remediation loops are internal to the document workflow
- Engine-owned circuit breakers (max retries) apply by default

QA does not directly advance project workflows.

---

## Audit and Governance

The system MUST record:

- all interaction turns (ADR-012)
- Durable LLM Thread history (ADR-035)
- document workflow transitions
- QA outcomes and remediation cycles
- terminal document outcomes

This audit trail is required for defensibility and governance.

---

## Consequences

### Positive
- Clean separation of concerns
- Reusable document creation patterns
- Enforceable intake and governance gates
- Simplified project workflows
- Consistent QA behavior

### Tradeoffs
- Introduces an additional execution layer
- Requires disciplined workflow orchestration

These tradeoffs are intentional.

---

## Non-Goals

This ADR does NOT:

- Replace ADR-012 or ADR-014
- Introduce new QA or interaction mechanics
- Allow documents to modify project workflows directly
- Encode retry counters or loop-breaking logic in workflow plans
- Support parallel document execution

---

## Summary

ADR-039 establishes **Document Interaction Workflows** as a first-class architectural concept.

It defines **where** multi-call interaction patterns live while reusing existing interaction, QA, routing, and workflow primitives.

This ADR completes the document-centric execution model of The Combine and enables clean enforcement of intake, discovery, and downstream governance.

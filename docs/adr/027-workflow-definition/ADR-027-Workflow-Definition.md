# ADR-027 — Workflow Definition, Selection, and Governance

**Status:** Accepted  
**Date:** 2026-01-02

**Related ADRs:**

- ADR-011 — Document Ownership Model
- ADR-012 — Interaction Model
- ADR-024 — Clarification Question Protocol & Usability Constraints
- ADR-025 — Intake Gate & Project Qualification
- ADR-026 — Concierge Role Definition

---

## 1. Context

Following the Concierge Intake Gate, The Combine must proceed through one of many possible workflows, depending on the nature of the qualified request.

Examples include (non-exhaustive):

- Software product development
- Technical architecture definition
- Construction project planning
- Organizational or operational strategy formulation
- Migration or transformation initiatives

Each of these requires different roles, task types, artifacts, and constraints.

Without a formal notion of workflow:

- Roles may assume inappropriate authority
- Task prompts may implicitly encode process
- Execution may default to a single "happy-path" pipeline
- Domain-specific needs (e.g., construction vs. software) become blurred

This ADR introduces workflow as a first-class, governed concept that bridges intake and execution — without prescribing orchestration mechanics.

---

## 2. Decision

A **Workflow** is a governed, declarative definition of:

- Which roles may participate
- Which task types may be executed
- Which artifacts may be produced or modified
- Which gates and escalation paths apply
- Which constraints bound execution

Workflows define scope and permission, not sequence or mechanics.

Workflow selection is informed by the Concierge Intake Gate, but workflows are not executed, enforced, or embedded by the Concierge.

---

## 3. What a Workflow Is (and Is Not)

### 3.1 A Workflow IS

A workflow is:

- A bounded execution envelope
- A capability map, not a script
- A policy definition, not a process diagram
- A constraint set over allowed actions

**It defines what is permitted, not how it is performed.**

### 3.2 A Workflow IS NOT

A workflow is not:

- A step-by-step process
- A rigid sequence of actions
- A UI or API flow
- An orchestration or scheduling mechanism
- A replacement for role or task prompts

Execution behavior remains governed by the Interaction Model (ADR-012).

---

## 4. Workflow Selection & Intake Relationship

### 4.1 Concierge Responsibility

The Concierge Intake Gate:

- Records user intent
- Surfaces constraints and gaps
- Classifies project characteristics
- Signals qualification or rejection

It MAY:

- Recommend or declare an applicable workflow
- Provide rationale for workflow suitability

It MUST NOT:

- Execute a workflow
- Encode workflow logic into the intake artifact
- Implicitly select a workflow through questioning style

The Concierge's role is informative and gating, not procedural.

### 4.2 Workflow Determination

A workflow may be:

- Explicitly selected (user or system-driven)
- Inferred from intake classification
- Confirmed via user acknowledgment

**Failure State:**  
If no workflow can be determined or confirmed — due to ambiguity, mismatch, or user non-acknowledgment — execution MUST NOT proceed. This is an explicit failure state, not an implicit default.

### 4.3 Project Type vs. Workflow

The Concierge Intake Document may include a project type classification (e.g., greenfield, enhancement, migration).

- Project type may inform workflow selection
- Project type does not define the workflow
- Workflow definition remains a separate governed construct

This distinction prevents workflow logic from being embedded into intake artifacts.

---

## 5. Workflow Structure (Conceptual)

Each workflow defines, at minimum:

**Eligible Roles**  
(e.g., Concierge, PM, Architect, BA, QA, Human Reviewer)

**Permitted Task Types**  
(e.g., discovery questions, backlog creation, architecture documentation)

**Artifact Ownership Rules**  
(what documents may be created or modified)

**Gate Requirements**  
(QA, clarification, escalation, human approval)

**Termination Conditions**  
(completion, rejection, escalation — v1 uses implicit termination: workflow ends when final step completes or explicit failure occurs)

Workflows may differ radically in structure without violating system coherence.

---

## 6. Relationship to Interaction Model

**Workflows define scope.**  
**The Interaction Model defines behavior.**

- ADR-012 governs how interactions occur
- This ADR governs which interactions are allowed

No workflow may bypass:

- Clarification Question Protocol (ADR-024)
- Independent QA evaluation
- Logging and audit requirements
- Explicit failure and escalation states

---

## 7. Governance & Extensibility

### 7.1 Workflow as a Governed Artifact

Workflow definitions are:

- Explicitly named
- Versioned
- Reviewable
- Auditable

They are governed inputs subject to ADR-013 (Seed Governance) and are treated as certified, hashable artifacts.

### 7.2 Adding a New Workflow

Introducing a new workflow requires:

- Clear articulation of scope
- Defined role participation
- Explicit constraints and boundaries

It does not require:

- New execution engines
- Changes to existing workflows
- Reinterpretation of role authority

---

## 8. Non-Goals

This ADR does not:

- Define workflow execution engines
- Specify orchestration or scheduling tooling
- Dictate UI or API representations
- Encode domain-specific methodologies
- Define mid-execution workflow transitions

---

## 9. Notes on Workflow Change

Handling workflow transitions mid-execution (e.g., discovering a project should follow a different workflow) is out of scope for this ADR.

Such situations may require:

- A new intake gate
- A formally declared workflow migration
- Or explicit human escalation

These decisions are deferred to future ADRs.

---

## 10. Risks & Drift Warnings

Primary risks:

- Treating workflows as implicit pipelines
- Allowing task prompts to invent workflow logic
- Letting role prompts absorb workflow authority
- Encoding workflow assumptions in handlers or UI

Mitigation:

- Keep workflows declarative and governed
- Enforce separation between scope (workflow) and behavior (interaction)
- Require explicit workflow identification in logs and artifacts

---

## 11. Summary

Workflows are the missing middle layer between intent and execution.

They allow The Combine to:

- Support multiple problem domains without collapse
- Preserve role and task integrity
- Scale without enforcing a single process
- Remain auditable, explainable, and governable

**They define what kind of work this is, not how the work is done.**



# ADR-025 — Intake Gate & Project Qualification

**Status:** Draft  
**Date:** 2026-01-02  
**Decision Type:** Architectural / Governance  
**Supersedes:** N/A  
**Related ADRs:** ADR-009, ADR-010, ADR-011, ADR-012, ADR-024

---

## 1. Context

The Combine operates in environments where ambiguity, partial intent, and underspecified requests introduce unacceptable downstream risk.

Historically, "project discovery" has been treated as the first structured step. This assumes that a sufficiently clear project intent already exists. In practice, this assumption is often false.

There is a need for a formal intake gate that:

- Allows clarification through limited interaction
- Records intent without inferring or improving it
- Explicitly determines whether a request is suitable to proceed
- Prevents downstream processes from compensating for missing or unclear inputs

---

## 2. Decision

The Combine SHALL introduce a Concierge Intake Gate as a mandatory, first-class gate preceding Project Discovery.

No Project Discovery, Epic Backlog creation, or Architecture documentation MAY occur unless the Concierge Intake Gate concludes with a qualifying outcome.

**This gate is a governance boundary, not a workflow.**

---

## 3. Role of the Concierge Intake Gate

The Concierge Intake Gate exists to:

- Capture user intent through limited, guided conversation
- Ask clarification questions when required
- Record constraints, goals, and unknowns explicitly
- Determine whether sufficient information exists to proceed

The gate MUST NOT:

- Infer unstated intent
- Improve, refine, or optimize the request
- Design solutions
- Propose scope, architecture, or backlog structure

---

## 4. Interaction Model

The Concierge operates as a bounded conversational interface with the following properties:

- Questions are permitted and expected
- Statements of intent must be grounded in user responses
- The Concierge MAY signal readiness to proceed
- The Concierge MUST NOT autonomously close the conversation

**User control is explicit:**  
The user decides when the intake conversation is closed.

Once closed, the Intake Gate produces a governed artifact and becomes immutable.

---

## 5. Gate Outcomes

The Concierge Intake Gate concludes with exactly one of the following outcomes:

| Outcome | Meaning |
|---------|---------|
| `qualified` | Sufficient clarity exists to proceed to Project Discovery |
| `not_ready` | Additional clarification, alignment, or preparation is required |
| `out_of_scope` | The request does not fall within The Combine's domain |
| `redirect` | The request is better served by a different engagement type |

Only a `qualified` outcome produces an artifact eligible for Project Discovery.

All other outcomes explicitly halt downstream processing.

---

## 6. Project Type Classification

As part of qualification, the Concierge Intake Document includes a project type classification, such as:

- Greenfield
- Enhancement
- Migration
- Integration
- Replacement
- Unknown

This classification informs downstream handling but does not constrain it.

---

## 7. Output Artifact

The Intake Gate produces a **Concierge Intake Document**.

This document:

- Is a governed artifact suitable for downstream consumption
- Is derived solely from user-provided information
- Contains no inferred intent, recommendations, or solutioning

Includes:

- Captured intent
- Constraints
- Known unknowns
- Gate outcome
- Supporting conversation context (if applicable)

**Raw chat transcripts alone are not valid downstream inputs.**  
Only the Concierge Intake Document is admissible.

The concrete schema used to represent this document is determined by the current certified schema registered at execution time. Schema versions are not fixed by this ADR.

---

## 8. Governance & Enforcement

- The Intake Gate is a hard dependency
- Downstream processes MUST fail fast if invoked without a qualified intake artifact
- Discovery and Architecture handlers MUST NOT attempt to repair or infer missing intake information

All gate decisions and artifacts are subject to:

- **ADR-009** (Audit & Governance)
- **ADR-010** (LLM Execution Logging)

---

## 9. Non-Goals

This ADR explicitly does not define:

- UI or conversational presentation
- Implementation details
- Prompt wording
- Storage or persistence mechanics
- How many questions may be asked

Those concerns are addressed elsewhere.

---

## 10. Risks & Drift Warnings

Primary risks include:

- Treating the Concierge as a soft pre-chat rather than a gate
- Allowing downstream steps to compensate for poor intake
- Allowing the Concierge to infer intent "to be helpful"
- Reintroducing workflow coupling instead of gate enforcement

**This ADR must remain a boundary definition, not a process description.**

---

## 11. Summary

The Concierge Intake Gate establishes a formal, auditable boundary between unstructured user intent and structured project execution.

It ensures that The Combine proceeds only when clarity exists — and halts cleanly when it does not.

**This gate is foundational to safety, predictability, and accountability across the system.**

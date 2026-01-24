# ADR-026 — Concierge Role Definition & Conversation Control

**Status:** Draft  
**Date:** 2026-01-02  
**Decision Type:** Role Definition / Governance  
**Related ADRs:** ADR-009, ADR-010, ADR-012, ADR-024, ADR-025

---

## 1. Context

The Combine introduces a Concierge Intake Gate (ADR-025) as a mandatory boundary before Project Discovery. That gate requires a clearly defined role responsible for facilitating clarity without assuming analytical, decision-making, or design authority.

This ADR defines the Concierge role itself, independent of any specific task prompt or execution schema.

---

## 2. Role Identity

The Concierge is a **facilitator of clarity**, not an analyst, product owner, or decision-maker.

The Concierge's sole responsibility is to:

- Elicit user-provided intent
- Surface ambiguity through questions
- Record constraints, gaps, and stated goals accurately
- Determine whether sufficient clarity exists to proceed

The Concierge does not:

- Infer unstated intent
- Improve, refine, or optimize requests
- Propose solutions, scope, architecture, or backlog structure
- Compensate for missing information

---

## 3. Core Purpose

The Concierge exists to ensure that downstream work begins only when intent is explicit and bounded, or halts cleanly when it is not.

**This role enforces clarity as a prerequisite — not as an emergent property of later stages.**

---

## 4. Authority Boundaries

### The Concierge MAY:

- Ask clarification questions
- Summarize user-provided intent
- Explicitly document known unknowns
- Identify constraints stated by the user
- Classify the project type (e.g., greenfield, enhancement, migration, integration, replacement, unknown) based solely on user input
- Conclude with a non-qualifying outcome (not_ready, out_of_scope, redirect) when appropriate
- Signal when sufficient information exists to proceed

### The Concierge MUST NOT:

- Decide product value or priority
- Define requirements or acceptance criteria
- Design architecture or technical solutions
- Infer intent beyond what the user has stated
- Proceed past the Intake Gate without qualification
- Close the conversation autonomously

---

## 5. Conversation Closure Protocol

The Concierge operates within a user-controlled conversation lifecycle.

When the Concierge determines that sufficient information exists to proceed, it MUST:

- Explicitly signal readiness to the user
- Summarize its understanding of:
  - Intent
  - Constraints
  - Known gaps
- Invite the user to:
  - Add more context, or
  - Close the conversation

**The Concierge MUST NOT close the conversation on its own.**

### Early Closure Handling

If the user attempts to close the conversation before the Concierge has signaled readiness:

- The Concierge SHOULD warn the user of specific missing information or unresolved gaps
- The Concierge SHOULD confirm whether the user wishes to proceed despite those gaps
- If the user confirms closure, the Concierge proceeds with a documented record of unresolved gaps

**The user always retains final control over closure.**

---

## 6. Output & Artifacts

The Concierge produces a **Concierge Intake Document** as defined in ADR-025.

This role does not define:

- The document's schema
- Serialization format
- Storage mechanism
- Version identifiers

Those concerns are governed elsewhere.

The Concierge treats the generated document as authoritative and immutable once the gate closes.

---

## 7. Governance Alignment

The Concierge role enforces:

- **ADR-009** — All decisions and gate outcomes are explicit and auditable
- **ADR-010** — All inputs, outputs, and execution context are loggable
- **ADR-025** — No Project Discovery may occur without a qualifying intake outcome

---

## 8. Non-Goals

This ADR does not define:

- Task prompts
- Question phrasing or schemas
- UI or chat presentation
- Workflow sequencing beyond the Intake Gate
- Persistence or replay mechanics

---

## 9. Separation of Role vs. Task

This ADR defines role identity and authority only.

All execution behavior — including:

- Question ordering
- Output schemas
- Validation rules

— belongs exclusively to task prompts governed separately.

---

## 10. Risks & Drift Warnings

Primary risks include:

- Allowing the Concierge to behave as an analyst or PM
- Softening rejection outcomes to "be helpful"
- Allowing downstream stages to repair poor intake
- Collapsing user-controlled closure into system control

**The Concierge must remain a gatekeeper of clarity, not a contributor to solution content.**

---

## 11. Summary

The Concierge role establishes a disciplined, auditable boundary between raw user intent and structured execution.

It protects The Combine from ambiguity, inferred intent, and premature execution — while preserving user agency and transparency.

---

## Amendment: Mechanical Intake Boundary (2026-01-22)

**Context:** The original ADR envisioned the Concierge as a conversational agent with multi-turn LLM interaction. Implementation revealed that conversational resolution at intake creates ambiguity, not clarity.

**Decision:**

The Concierge is **not a conversational agent**. It is a **bounded interpretation and qualification function** whose purpose is to produce a lockable intake artifact.

**Revised Role Identity:**

The Concierge:
- Extracts intent mechanically from user input
- Presents a reviewable interpretation for user verification
- Gates downstream work on explicit user confirmation (Lock action)
- Does NOT engage in multi-turn conversation to "understand" intent

**Rationale:**

Intake exists to establish an intent boundary, not to resolve ambiguity. Ambiguity resolution belongs downstream in Discovery, where structured questioning and options contracts (ADR-037) apply.

Attempting to make Intake "conversational" introduced:
- Infinite question loops
- Unclear completion criteria  
- Scope creep into Discovery territory

**Stage Separation Principle:**

| Stage | Purpose | Interaction Model |
|-------|---------|-------------------|
| Intake | Establish intent boundary | Mechanical + Review |
| Discovery | Resolve ambiguity | Guided questioning |
| Architecture | Constrain solution | Options & tradeoffs |
| Execution | Produce artifacts | Agentic workflows |

**Supersedes:**
- Multi-turn LLM intake conversation
- User-controlled conversation closure (Section 5)
- Question-based clarification loops

**Preserved:**
- Concierge does not infer unstated intent
- Concierge does not propose solutions
- Gate outcomes remain authoritative

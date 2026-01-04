# ADR-029 — Contextual Document Resolution

**Status:** Draft  
**Date:** 2026-01-02  
**Priority:** Post-MVP  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-011 — Document Ownership Model
- ADR-012 — Interaction Model
- ADR-017 — Prompt Certification & Trust Levels
- ADR-027 — Workflow Definition & Governance
- ADR-028 — Reference Document Management

---

## 1. Decision Summary

Reference documents are resolved and condensed dynamically per workflow step, based on role and task context, rather than preprocessed globally.

Document resolution is:

- Contextual (role + task aware)
- Ephemeral (derived, not authoritative)
- Non-owning (does not create new owned documents)
- Deterministic within a step execution
- Explicitly governed by the interaction loop (ADR-012)

**This ADR defines when and how reference documents are transformed into usable context for a step.**  
**It does not define storage, ownership, or upload rules (ADR-028).**

---

## 2. Core Principles

**Original documents remain the source of truth**  
Derived summaries are contextual views, not authoritative artifacts.

**Condensing is role- and task-specific**  
The same document may be summarized differently depending on who is consuming it and for what purpose.

**Resolution happens inside step execution**  
There is no global preprocessing or ingestion phase.

**No hidden continuity**  
Derived context does not persist silently across steps.

---

## 3. Integration with the Interaction Model (ADR-012)

Contextual document resolution is part of step execution, not a standalone workflow.

Within ADR-012's loop:

### 3.1 Step Execution Augmentation

Before a worker can:

- Ask clarification questions
- Produce a primary output

The Combine MUST:

1. Gather reference documents available at the current scope (ADR-028)
2. Resolve them for this role and task
3. Provide the worker with condensed reference context, not raw documents (unless small enough to pass through unmodified)

The threshold for "small enough" is implementation-defined but SHOULD be documented per deployment.

This occurs before the Clarification Gate.

---

## 4. Condensing Phases

### 4.1 Pre-Clarification Condensing

**Purpose:** Enable informed questioning.

Before the Clarification Gate:

- Reference documents are condensed according to:
  - Role identity
  - Task intent
  - Workflow scope
- The worker uses this material to:
  - Understand constraints
  - Detect gaps
  - Formulate clarification questions

No output is produced at this stage.

### 4.2 Post-Clarification Re-Condensing

After the Clarification Gate completes, if the user has:

- Provided answers that shift focus or priority, OR
- Attached new reference documents

Then reference materials MUST be re-resolved.

Condensing instructions MUST incorporate:

- User answers
- Newly provided reference documents
- Any clarified priorities

This ensures output reflects updated intent.

---

## 5. Condensing Agent

Condensing is performed by the same worker role executing the step.

Condensing occurs as part of the worker's reasoning process within a single step execution. It is not a separate LLM invocation unless context limits require chunked processing.

**Rationale:**

- The worker has the best understanding of what information matters
- Avoids introducing a second interpretive agent
- Preserves accountability within the step

This is an internal reasoning aid, not a separate execution.

---

## 6. Condensing Instructions

Condensing behavior is governed by:

- The role prompt (how this role interprets information)
- The task prompt (what matters for this execution)

No standalone "summarizer role" is introduced.

Condensing instructions MUST NOT:

- Introduce new requirements
- Add assumptions
- Alter document meaning

---

## 7. What Is Stored (MVP)

For MVP:

| Artifact | Stored |
|----------|--------|
| Original reference document | ✅ Yes |
| Condensed context | ❌ No |
| Usage record (doc X used in step Y) | ✅ Yes |

Condensed material is ephemeral and may differ across replays due to model variance. This is acceptable per ADR-010's replay model, which guarantees input reproducibility but not output identity.

Exact replayability of summaries is explicitly deferred.

---

## 8. Trust & Governance

- Condensed material inherits the trust level of its source (ADR-028)
- Condensed context MUST NOT be treated as certified
- QA evaluates outputs, not the condensing process itself
- Any step relying on reference material MUST log document IDs used

---

## 9. Explicit Non-Goals (Deferred)

The following are out of scope for this ADR and MVP:

- Persistent caching of condensed summaries
- Cross-step reuse of summaries
- User-guided highlighting ("focus on section 3")
- Token-budget optimization strategies
- Knowledge base construction

These may be addressed in future ADRs.

---

## 10. Failure Modes

**If reference documents are too large to condense within constraints:**

- The worker MUST enter clarification
- The user may be asked to narrow scope or provide excerpts

**If reference material is irrelevant or contradictory:**

- The worker MUST surface this explicitly via the Clarification Gate, requesting user guidance on which source to prefer
- Silent disregard is prohibited

---

## 11. Consequences

### Positive

- Strong alignment with interaction model
- Role-correct interpretation
- Minimal state and low complexity
- Clear audit trail

### Negative

- Repeated condensing work
- Larger prompts in some steps
- Non-identical replays across executions

These are acceptable for MVP.

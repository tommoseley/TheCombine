# ADR-012 — Interaction Model

**Status:** Accepted  
**Version:** v1.1  
**Date:** 2026-01-02  
**Decision Type:** Architectural

**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-011 — Document Ownership Model
- ADR-024 — Clarification Question Protocol
- ADR-027 — Workflow Definition & Governance
- ADR-029 — Contextual Document Resolution (post-MVP)

---

## 1. Decision Summary

This ADR defines the canonical interaction model for all execution steps in The Combine.

The interaction model establishes:

- A closed-loop execution structure
- Explicit handling of uncertainty
- Mandatory independent validation
- Controlled remediation of failures
- Optional human acceptance when required

**The objective is risk containment, not determinism.**

This ADR defines *how* any step executes.  
It does not define which steps exist or their sequence (see ADR-027).

---

## 2. Problem Statement

Large language models are stochastic systems.  
Unchecked, they tend to:

- Infer missing intent silently
- Collapse clarification into generation
- Self-certify outputs
- Drift across iterations without accountability

The Combine requires an interaction model that:

- Forces ambiguity to surface explicitly
- Separates generation from validation
- Prevents unreviewed outputs from propagating
- Produces auditable, replayable execution traces

---

## 3. Definitions

**Interaction Cycle**  
A bounded sequence of execution states resulting in either an approved output or an explicit failure.

**Worker**  
An LLM operating under a certified role prompt to perform a specific task.

**Clarification Gate**  
A hard gate in which the Worker may only ask questions and must not produce partial output.

**QA Role**  
An independent evaluator that judges outputs against constraints but does not modify them.

**Acceptance Gate**  
A human decision point validating business judgment or intent alignment, distinct from QA.

---

## 4. Canonical Interaction Loop

Every workflow step (as defined in ADR-027) executes using the following loop.

### 4.1 Request to Worker

The Combine invokes the Worker with:

- User intent or upstream task intent
- Certified role identity
- Task prompt
- Input documents (as declared by the workflow)
- Scope context (per ADR-011: project, epic, story, etc.)

**Scope Constraints:**

- The Worker may only reference documents permitted by its scope boundary.
- Access to documents outside scope is prohibited.

The Worker must either:

- Produce a complete output, or
- Declare ambiguity and enter the Clarification Gate.

### 4.2 Clarification Gate

If ambiguity exists:

- The Worker must respond only with clarification questions.
- No partial output, assumptions, or embedded answers are permitted.
- Questions are returned to the user.
- The Worker is re-invoked with:
  - Original request
  - User answers

**All clarification behavior MUST conform to ADR-024.**  
**This ADR defines *when* clarification occurs.**  
**ADR-024 defines *how* questions are structured and constrained.**

### 4.3 Primary Output Production

- The Worker produces a complete artifact.
- No self-QA or self-certification is permitted.
- Output is treated as provisional until validated.

### 4.4 QA Gate (Mandatory)

Output is submitted to QA.

QA evaluates against:

- Task instructions
- Schemas and constraints
- Governance and safety rules
- Risk thresholds

**QA Constraints:**

- QA may judge only.
- QA must not repair, rewrite, or improve output.
- QA findings must be explicit and immutable.

If QA fails, execution proceeds to remediation.

### 4.5 Remediation Loop (If Required)

If QA fails:

- The Combine re-invokes the Worker with:
  - Original request
  - Prior output
  - QA findings
- Worker produces a revised output.
- Output returns to QA.

This loop continues until:

- QA passes, or
- An explicit failure state is declared.

Remediation loops must be:

- Bounded
- State-aware
- Non-expansive in scope

### 4.6 Acceptance Gate (If Required)

Some outputs require human acceptance before downstream use.

- Acceptance requirements are declared by the workflow (ADR-027).
- Acceptance is distinct from QA:
  - QA validates correctness and constraint compliance.
  - Acceptance validates business judgment and intent alignment.

**Outcomes:**

- **Accepted** — Output may be consumed downstream
- **Rejected** — Returned to remediation with human feedback

No output requiring acceptance may proceed without it.

### 4.7 Response to User

Only outputs that have:

- Passed QA, and
- Been accepted when required

may be surfaced or used as downstream inputs.

Intermediate churn is hidden unless explicitly configured.

---

## 5. Execution State Model (Normative)

Each step must exist in exactly one of the following states:

| State | Meaning |
|-------|---------|
| `pending` | Not yet started |
| `awaiting_clarification` | Questions sent to user |
| `executing` | Worker generating output |
| `awaiting_acceptance` | Pending human decision |
| `completed` | Successfully finished |
| `failed` | Unrecoverable failure |

State transitions must be explicit and logged.

---

## 6. Relationship to Workflows (ADR-027)

- ADR-012 defines execution semantics.
- ADR-027 defines:
  - Which steps exist
  - Their order and iteration
  - Inputs and outputs
  - Acceptance requirements

Every workflow step executes using this interaction model.

---

## 7. Audit & Logging Alignment

All interaction stages must comply with:

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging

At minimum, logs must capture:

- Each execution state transition
- Clarification questions and answers
- QA findings per iteration
- Acceptance decisions
- Final disposition

---

## 8. Out of Scope

This ADR does not define:

- Workflow composition
- Prompt content
- Handler wiring
- Context condensation (see ADR-029)
- UI or conversational presentation

---

## 9. Drift Risks

Key risks include:

- Allowing Workers to infer intent silently
- Collapsing clarification into generation
- Treating QA as advisory
- Allowing acceptance to bypass QA

Any relaxation of these constraints requires a new ADR.

---

## Closing Note (Non-Normative)

The Combine interaction model is a control system, not a chatbot.

- Questions surface uncertainty
- QA constrains harm
- Acceptance captures human judgment

This ADR defines the machinery that makes that discipline enforceable.

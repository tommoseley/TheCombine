# ADR-012 — Interaction Model

**Status:** Accepted  
**Date:** 2026-01-02  
**Related ADRs:** ADR-009 (Audit & Governance), ADR-010 (LLM Execution Logging), ADR-011 (Project / Epic / Story Ownership)

---

## 1. Decision Summary

This ADR defines the canonical interaction model for The Combine.

The interaction model establishes:

- A closed-loop execution structure
- Explicit handling of uncertainty
- Mandatory independent validation
- Controlled remediation of failures

**The goal is risk containment, not determinism.**

This ADR defines *what* interaction stages must exist and *how they relate*, not how they are implemented.

---

## 2. Problem Statement

LLMs are stochastic systems.  
Unchecked, they:

- Infer missing intent silently
- Collapse questioning into generation
- Self-certify outputs
- Drift across iterations without accountability

The Combine requires an interaction model that:

- Forces ambiguity to surface explicitly
- Separates generation from validation
- Prevents unreviewed outputs from escaping
- Creates auditable, replayable execution traces

---

## 3. Definitions

**Interaction Cycle**  
A bounded sequence of LLM executions resulting in a QA-approved output or an explicit failure.

**Worker**  
The LLM operating under a certified role prompt to perform the current task.

**Clarification Gate**  
A phase in which the Worker may only ask questions and must not produce partial solutions.

**QA Role**  
An independent evaluator that judges outputs against explicit criteria but does not modify them.

---

## 4. Canonical Interaction Loop

All Combine interactions must conform to the following conceptual loop:

### 1. Request to Worker

- User intent is provided.
- Worker operates under a certified role prompt.
- Worker must either:
  - Produce a complete output, or
  - Declare ambiguity and enter questioning.

### 2. Clarification Gate

If ambiguity exists:

- Worker responds only with questions.
- No partial answers or assumptions are permitted.
- User provides answers.
- Worker is re-invoked with:
  - Original request
  - User answers

### 3. Primary Output Production

- Worker produces a complete artifact.
- No self-QA or self-certification is permitted.

### 4. QA Pass

- Output is submitted to QA.
- QA evaluates against:
  - Task instructions
  - Schemas and constraints
  - Risk thresholds
  - Safety and governance rules
- QA must judge only; it must not correct.

### 5. Remediation Loop (If Required)

If QA fails:

- Combine sends back to the Worker:
  - Original request
  - Worker output
  - QA findings
- Worker produces a revised output.
- Output returns to QA.
- Loop continues until:
  - QA passes, or
  - Explicit failure is declared.

### 6. Response to User

- Only QA-approved outputs may be surfaced.
- Intermediate churn is not user-visible unless explicitly configured.

---

## 5. Questioning Model

Questions are first-class outputs, not conversational noise.

**Constraints:**

- Questioning must be explicitly permitted by the task prompt.
- Questioning must occur before primary output generation.
- Questions must not embed assumptions or lead answers.
- Questioning exists to eliminate ambiguity, not explore ideas.
- Implicit clarification is prohibited.

---

## 6. QA Model

QA is a veto authority, not an advisor.

**Constraints:**

- QA evaluates only explicit artifacts.
- QA must not repair, rewrite, or "helpfully improve" outputs.
- QA findings must be explicit, immutable, and loggable.
- QA failure must be visible to the system.
- Workers may not self-certify or bypass QA.

---

## 7. Looping Constraints

Remediation loops must be:

- Explicitly bounded
- State-aware (each iteration is distinct)
- Non-expansive in scope

Unbounded or implicit looping is prohibited.

Failure to satisfy constraints must result in an explicit failure state.

---

## 8. Audit & Logging Alignment

All interaction stages must comply with:

- **ADR-009** — decisions and failures are explicit
- **ADR-010** — all inputs, outputs, and QA findings are logged

At minimum, execution records must capture:

- Each iteration
- QA feedback per iteration
- Final disposition (pass or fail)

---

## 9. Out of Scope

This ADR does not define:

- Handler wiring
- Prompt content
- Execution infrastructure
- UI or conversational presentation
- How many QA passes are "enough"

Those concerns belong to implementation or future ADRs.

---

## 10. Drift Risks

Primary risks include:

- Allowing Workers to infer intent silently
- Collapsing questioning into generation
- Treating QA as advisory rather than authoritative
- Introducing "fast paths" that bypass validation

Any relaxation of these constraints requires a new ADR.

---

## Closing Note (Non-Normative)

The Combine's interaction model is a control system, not a dialogue model.

Questions exist to surface uncertainty.  
QA exists to constrain harm.  
Iteration exists to enforce accountability.

This ADR formalizes that structure.

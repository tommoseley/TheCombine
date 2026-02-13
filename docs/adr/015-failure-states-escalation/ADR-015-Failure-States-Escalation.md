# ADR-015 — Failure States & Escalation Semantics

**Status:** Draft (Scaffold)  
**Date:** 2026-01-02  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-012 — Interaction Model
- ADR-014 — Quality Assurance Modes

---

## 1. Decision Summary

This ADR defines the explicit failure states recognized by The Combine and the rules governing escalation, retry, and termination.

**Failure is treated as a first-class, auditable outcome, not an exception or anomaly.**

---

## 2. Problem Statement

LLM-driven systems fail in non-binary ways:

- Ambiguity cannot be resolved
- Constraints are mutually exclusive
- QA rejects outputs repeatedly
- Inputs are insufficient or contradictory

Without explicit failure semantics:

- Systems silently degrade
- Retries become infinite or opaque
- Responsibility is blurred
- Users lose trust in outcomes

The Combine requires explicit, bounded, and observable failure states.

---

## 3. Definitions

**Failure State**  
A formally recognized condition where progression cannot continue without external intervention.

**Escalation**  
The act of surfacing a failure to a higher authority (human or system) for resolution.

**Retry**  
A bounded re-execution attempt using the same or augmented inputs.

**Terminal Failure**  
A failure state that halts execution definitively.

---

## 4. Recognized Failure Categories (Conceptual)

This ADR recognizes failure categories including, but not limited to:

- Ambiguity Failure
- Constraint Conflict
- QA Rejection
- Input Incompleteness
- Execution Error
- Governance Violation

These categories are conceptual, not exhaustive.

---

## 5. Ambiguity Failure

Occurs when:

- Required information is missing
- Clarification questions cannot be resolved
- User-provided answers remain contradictory

Rules:

- Must be surfaced explicitly
- Must not be silently bypassed
- May trigger escalation

---

## 6. QA Rejection Failure

Occurs when:

- QA repeatedly rejects outputs
- Required constraints cannot be satisfied
- Structural or semantic risks persist

Rules:

- QA findings must be immutable
- Each retry must reference prior findings
- Retry limits must be explicit

---

## 7. Retry Semantics

Retries:

- Must be bounded
- Must be logged
- Must not alter constraints silently

Retries are not a substitute for escalation.

---

## 8. Escalation Semantics

Escalation may occur to:

- A human operator
- A supervisory system
- A blocking user interaction

Escalation must:

- Preserve full context
- Include failure classification
- Surface unresolved constraints

---

## 9. Terminal Failure

A terminal failure:

- Ends the interaction loop
- Produces a failure artifact
- Is logged as a final outcome

**Terminal failure is a valid and expected result.**

---

## 10. Governance & Audit Alignment

All failures must comply with:

- **ADR-009** — explicit, traceable decisions
- **ADR-010** — full execution and failure logging

No failure may be:

- Hidden
- Coerced into success
- Converted into partial output without disclosure

---

## 11. Out of Scope

This ADR does not define:

- UI handling of failures
- Alerting mechanisms
- Automated remediation strategies
- Cost or performance optimization

---

## 12. Drift Risks

Primary risks include:

- Treating retries as infinite
- Suppressing failure visibility
- Collapsing failure types into generic errors
- Allowing QA vetoes to be overridden informally

Any exception to failure semantics requires a new ADR.

---

## 13. Open Questions

- What are default retry limits per failure type?
- Which failures mandate human escalation?
- Can some failures downgrade scope instead of terminating?
- How are failure artifacts exposed to users?

These questions are intentionally deferred.

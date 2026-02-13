# ADR-016 — Escalation Targets & Human-in-the-Loop Design

**Status:** Draft (Scaffold)  
**Date:** 2026-01-02  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-012 — Interaction Model
- ADR-014 — Quality Assurance Modes
- ADR-015 — Failure States & Escalation Semantics

---

## 1. Decision Summary

This ADR defines *who or what* The Combine may escalate to, under which conditions, and what information must be surfaced during escalation.

**Escalation is treated as a designed system boundary, not an error-handling afterthought.**

---

## 2. Problem Statement

In The Combine:

- Workers do not self-certify
- QA acts as a veto
- Failures are explicit and logged

However, not all failures are equal:

- Some require user clarification
- Some require human judgment
- Some must halt execution entirely

Without explicit escalation targets and rules:

- Systems stall indefinitely
- Responsibility becomes ambiguous
- Humans are pulled in too late or too early
- Governance guarantees erode

The Combine requires explicit, auditable human-in-the-loop design.

---

## 3. Definitions

**Escalation Target**  
An authorized recipient of a failure state or blocked execution.

**Human-in-the-Loop (HITL)**  
A deliberate pause where human judgment is required before proceeding.

**Blocking Escalation**  
Escalation that halts all further progress until resolved.

**Advisory Escalation**  
Escalation that surfaces risk but does not block execution.

---

## 4. Escalation Principles

Escalation in The Combine must be:

- **Explicit** — never implicit or inferred
- **Bounded** — no infinite waiting
- **Context-preserving** — full execution history included
- **Role-respecting** — escalation does not override role boundaries
- **Auditable** — logged as a first-class event

---

## 5. Recognized Escalation Targets (Conceptual)

This ADR recognizes the following classes of escalation targets:

- User
- Human Operator
- System Supervisor
- Terminal Failure

These are conceptual categories, not implementation bindings.

---

## 6. User Escalation

Occurs when:

- Required clarifications cannot be inferred
- Inputs are incomplete or contradictory
- Ambiguity blocks safe progress

Rules:

- Questions must be explicit
- No partial output may be produced
- Execution resumes only with user response

---

## 7. Human Operator Escalation

Occurs when:

- QA repeatedly vetoes output
- Constraints conflict irreconcilably
- Ethical, legal, or safety concerns arise
- Scope or authority boundaries are unclear

Rules:

- Full execution and QA context must be provided
- Operator actions must be explicit and logged
- Operators may resolve, constrain, or terminate execution

---

## 8. System Supervisor Escalation

Occurs when:

- Automated thresholds are exceeded (e.g., retry limits)
- Cross-run patterns indicate systemic risk
- Governance rules require higher-order arbitration

Rules:

- Supervisor does not produce content
- Supervisor only decides continuation, scope reduction, or termination
- Decisions are recorded as governance artifacts

---

## 9. Terminal Escalation

Occurs when:

- No escalation target can resolve the failure
- Constraints prohibit any safe continuation
- Governance rules mandate termination

Rules:

- A failure artifact is produced
- No further retries occur
- Outcome is logged as terminal

**Terminal escalation is not an error; it is a valid system outcome.**

---

## 10. Information Required for Escalation

All escalations must include:

- Failure classification (from ADR-015)
- Correlation ID
- Original request
- All LLM inputs and outputs
- QA findings (immutable)
- Retry history (if any)

**No escalation may occur with partial context.**

---

## 11. Governance & Audit Alignment

Escalation behavior must comply with:

- **ADR-009** — all escalation decisions are explicit and traceable
- **ADR-010** — escalation artifacts are logged and replayable

Escalation must never:

- Bypass QA
- Override certified prompts
- Suppress failure visibility

---

## 12. Out of Scope

This ADR does not define:

- UI/UX for escalation handling
- Notification or paging systems
- Staffing or operational processes
- Cost or latency optimization

---

## 13. Drift Risks

Primary risks include:

- Over-escalation that blocks normal progress
- Under-escalation that hides real risk
- Informal human overrides without logging
- Treating escalation as an exception path instead of a designed path

Any deviation requires a new ADR.

---

## 14. Open Questions

- Which escalation targets are enabled by default?
- What escalation thresholds are configurable?
- Can some escalations downgrade scope instead of blocking?
- How are escalations surfaced differently to users vs operators?

These questions are intentionally deferred.

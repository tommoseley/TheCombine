# ADR-022 — Trust Demotion, Recovery, and Revocation

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-01-02

---

## 1. Context

ADR-017 establishes Prompt Trust Levels. ADR-018 establishes Prompt Change Control. ADR-020 introduces Failure Analytics as learning signals.

What remains undefined is how trust is reduced, restored, or revoked over time.

Without explicit rules, trust becomes:

- Sticky (never decreases)
- Political (manual, undocumented)
- Unsafe (continued reliance on degraded prompts)

This ADR defines how trust changes — and who is allowed to change it.

---

## 2. Decision

Prompt trust levels in The Combine are mutable but governed.

Trust MAY be:

- Demoted
- Temporarily suspended
- Fully revoked
- Later restored

…but never silently and never automatically.

---

## 3. Trust Demotion

### 3.1 Grounds for Demotion

Trust demotion MAY occur due to:

- Repeated QA failures
- Trust boundary violations (ADR-019)
- High-severity failure patterns (ADR-020)
- Prompt drift from certified intent
- Explicit human judgment

Demotion MUST NOT occur due to:

- Single benign failure
- Model stochastic variation alone
- Performance concerns without risk impact

### 3.2 Demotion Mechanics

When a prompt is demoted:

- Its trust level is reduced by exactly one step
- Existing executions remain valid
- New executions must honor the new trust level

Demotion events MUST be logged with:

- Prompt identifier
- Previous trust level
- New trust level
- Reason
- Authorizing entity (human or policy)

---

## 4. Trust Suspension

Suspension is a temporary disablement.

Suspended prompts:

- MAY NOT be used in new executions
- MAY still be replayed
- Retain historical trust metadata

**Suspension is appropriate when risk is unclear but credible.**

---

## 5. Trust Revocation

Revocation is permanent de-certification.

Revoked prompts:

- MAY NOT be executed
- MAY NOT be re-certified without explicit re-approval
- Remain immutable for audit purposes

**Revocation MUST be human-authorized.**

---

## 6. Trust Recovery

Recovery MAY occur when:

- Prompt is revised under ADR-018
- Failures are resolved and verified
- QA confidence is restored

Recovery:

- MUST be explicit
- MUST not exceed the previous highest certified level
- MUST include rationale

**Trust does not "snap back."**

---

## 7. Interaction with Replay

Replays MUST:

- Reflect the trust level at time of execution
- Surface later demotion or revocation as metadata
- Never invalidate historical results retroactively

---

## 8. Governance Alignment

This ADR enforces:

- **ADR-009** (accountability)
- **ADR-017** (trust levels)
- **ADR-018** (change control)
- **ADR-020** (learning signals)

---

## 9. Out of Scope

This ADR does not define:

- Automated trust scoring
- Machine-driven trust escalation
- Organizational approval hierarchies

---

## 10. Summary

Trust must be earned — and re-earned.

**This ADR ensures trust in The Combine is earned, fragile, and governable.**

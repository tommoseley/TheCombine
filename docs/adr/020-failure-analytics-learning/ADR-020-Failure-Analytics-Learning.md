# ADR-020 — Failure Analytics & Learning Signals

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-01-02

---

## 1. Context

The Combine intentionally accepts stochastic behavior but constrains harm through:

- Explicit questions
- Independent QA
- Replayable execution (ADR-010)

However, without structured failure analytics, the system cannot improve:

- Prompt quality
- QA effectiveness
- Trust calibration

This ADR defines how failures become learning signals, not silent losses.

---

## 2. Decision

All failures in The Combine MUST emit structured, analyzable signals.

**Failures are not exceptions — they are first-class data.**

---

## 3. Failure Categories

Failures MUST be classified as one of:

- Clarification failure
- Constraint violation
- QA rejection
- Trust boundary violation
- Execution error
- Human escalation

Each category MUST be explicit and exclusive.

---

## 4. Signal Capture

For every failure, the system MUST record:

- Failure type
- Stage of failure
- Prompt versions involved
- Trust levels involved
- QA findings (if applicable)
- Human intervention (if applicable)

**No failure may exist without metadata.**

---

## 5. Learning Signals (Non-Autonomous)

Failure analytics MAY be used to:

- Flag prompts for review
- Recommend trust demotion
- Identify recurring ambiguity patterns
- Surface fragile task definitions

Failure analytics MUST NOT:

- Auto-modify prompts
- Auto-escalate trust
- Change behavior without human approval

---

## 6. Replay Integration

Failures MUST be replayable.

- Replaying a failed run MUST reproduce the failure
- Analytics MAY compare failures across prompt versions
- Differences MUST be attributable to explicit changes

---

## 7. Governance Alignment

This ADR reinforces:

- **ADR-009:** explicit accountability
- **ADR-017:** trust calibration
- **ADR-018:** prompt evolution discipline

---

## 8. Out of Scope

This ADR does not define:

- ML-based optimization
- Automated prompt rewriting
- Alerting thresholds or dashboards

---

## 9. Consequences

**Positive:**

- Turns failure into institutional knowledge
- Prevents repeated mistakes
- Enables defensible improvement

**Trade-off:**

- Increased logging volume
- Requires discipline in classification

---

## 10. Summary

Failure is not noise.  
Failure is data.

**This ADR ensures the Combine learns without self-directing.**

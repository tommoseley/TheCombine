# ADR-021 — Human Decision Capture & Accountability

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-01-02

---

## 1. Context

Despite extensive automation, The Combine intentionally preserves human authority:

- Final approvals
- Escalation resolution
- Ethical judgment
- Risk acceptance

However, human decisions are often:

- Undocumented
- Detached from execution context
- Lost over time

This ADR defines how human decisions are captured, attributed, and preserved.

---

## 2. Decision

All human interventions in The Combine MUST be explicitly captured as governed events.

**Human judgment is authoritative — but never invisible.**

---

## 3. What Constitutes a Human Decision

Examples include:

- Approving a QA-failed output
- Overriding a constraint
- Accepting risk explicitly
- Selecting between alternatives
- Terminating an execution path

**Silence is not a decision.**

---

## 4. Required Decision Record

Every captured human decision MUST include:

- Decision type
- Decision maker (identity)
- Related execution(s)
- Reasoning summary
- Timestamp

This record becomes part of the execution audit trail.

---

## 5. Relationship to LLM Outputs

Human decisions:

- Do NOT modify historical LLM outputs
- Do NOT rewrite prompt history
- MAY authorize exceptions for specific executions

**Human decisions never retroactively legitimize system behavior.**

---

## 6. Replay Semantics

Replays MUST:

- Surface human decisions clearly
- Distinguish system output from human override
- Preserve original failure states

**Replays without human context are invalid.**

---

## 7. Governance Alignment

This ADR enforces:

- **ADR-009:** accountability
- **ADR-016:** human-in-the-loop escalation
- Regulatory defensibility

---

## 8. Out of Scope

This ADR does not define:

- Approval UI
- Authorization models
- Delegation hierarchies

---

## 9. Consequences

**Positive:**

- Preserves institutional memory
- Makes responsibility explicit
- Enables post-hoc reasoning

**Trade-off:**

- Slower exception handling
- Increased documentation burden

**This is intentional.**

---

## 10. Summary

Automation executes. Humans decide. Decisions must be remembered.

**This ADR ensures authority survives scale.**

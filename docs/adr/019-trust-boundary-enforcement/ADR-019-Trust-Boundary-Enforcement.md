# ADR-019 — Trust Boundary Enforcement in Prompt Composition

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-01-02

---

## 1. Context

ADR-017 establishes Prompt Trust Levels. ADR-018 establishes Prompt Change Control.

However, prompts in The Combine are rarely used in isolation. They are composed at runtime from multiple sources:

- Role prompts
- Task prompts
- Context documents
- System instructions
- QA feedback
- User input

Without explicit enforcement, composition can violate trust guarantees:

- Low-trust inputs influencing high-trust behavior
- Deprecated prompts being indirectly reintroduced
- User or tool content escalating authority unintentionally

This ADR defines hard trust boundaries for prompt composition.

---

## 2. Decision

Prompt composition in The Combine MUST enforce strict trust boundary rules.

No composed prompt may:

- Elevate trust implicitly
- Allow lower-trust content to override higher-trust intent
- Introduce uncertified instructions into certified execution paths

**Trust is enforced mechanically, not by convention.**

---

## 3. Trust Boundary Rules

### 3.1 Downward Influence Only

Higher-trust prompts MAY reference lower-trust inputs as context, but never as instructions.

Lower-trust prompts MAY NOT:

- Override
- Amend
- Reinterpret
- Narrow
- Expand

the authority of higher-trust prompts.

### 3.2 Instruction vs Context Separation

All composed prompt material MUST be classified as one of:

- **Instructional** (governing behavior)
- **Contextual** (informational only)

Only instructional content from equal or higher trust levels may affect behavior.

### 3.3 No Implicit Escalation

Prompt composition MUST NOT:

- Merge multiple low-trust prompts to simulate high trust
- Infer authority from repetition
- Treat historical outputs as instructions unless explicitly certified

---

## 4. Enforcement Mechanism

At composition time, the Combine MUST:

- Identify trust level of each component
- Enforce precedence rules
- Reject illegal compositions before execution

Violations result in:

- Hard failure
- Logged trust violation event
- No LLM execution

---

## 5. Interaction with Replay

Trust boundaries apply equally during replay.

- Replays MUST reconstruct the original trust context
- Trust violations discovered later MUST NOT retroactively invalidate prior executions
- Violations MAY trigger future prompt revocation or demotion

---

## 6. Governance Requirements

Every composed execution MUST log:

- Prompt components used
- Trust level of each component
- Resolution order
- Any suppressed or rejected content

This data supports audits and post-failure analysis.

---

## 7. Out of Scope

This ADR does not define:

- UI visualization of trust boundaries
- Prompt authoring tools
- Trust scoring heuristics

---

## 8. Consequences

**Positive:**

- Prevents authority leakage
- Makes trust enforceable, not aspirational
- Supports enterprise and regulatory defensibility

**Trade-off:**

- Reduced compositional flexibility
- Higher upfront rigor

---

## 9. Summary

Trust is meaningless if it can be bypassed compositionally.

**This ADR ensures that prompt trust survives contact with complexity.**

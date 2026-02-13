# ADR-018 — Prompt Change Control & Deprecation

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-01-02

---

## 1. Context

The Combine treats prompts as governed behavioral artifacts, not configuration text.

As established in prior ADRs:

- **ADR-010:** All LLM executions are logged, replayable, and attributable to specific prompt versions.
- **ADR-017:** Prompts are assigned trust levels that govern how and where they may be used.
- **ADR-009:** All system-affecting changes must be explicit, traceable, and auditable.

However, without explicit change control, prompt evolution introduces unbounded risk:

- Silent behavioral drift
- Invalid replay comparisons
- Undocumented trust erosion
- Inability to reason about failures historically

This ADR defines how prompts may change over time without compromising auditability, trust, or replay integrity.

---

## 2. Decision

All prompts in The Combine are subject to formal change control and deprecation rules.

Prompt changes MUST be:

- Explicit
- Versioned
- Classified
- Auditable
- Governed by trust-level impact

**No prompt may change behavior silently.**

---

## 3. Prompt Identity & Immutability

### 3.1 Canonical Identity

A prompt is uniquely identified by:

- prompt_id
- ersion
- content_hash

Once certified, a prompt version is immutable.

Any textual change, however small, constitutes a new version.

### 3.2 Immutability Guarantees

- Certified prompts must never be edited in place
- Historical executions always reference the exact prompt version used
- Replays MUST resolve to the original prompt content, even if deprecated

---

## 4. Change Classification

All prompt changes MUST be classified before certification.

### 4.1 Non-Breaking Changes

**Examples:**

- Clarifying language
- Tightening constraints
- Reducing ambiguity without changing intent

**Rules:**

- New version required
- Trust level MAY remain unchanged
- Replay comparisons remain meaningful but not identical

### 4.2 Breaking Changes

**Examples:**

- Changed authority boundaries
- Altered output expectations
- Modified reasoning posture
- Changed safety or escalation behavior

**Rules:**

- New version required
- Trust level MUST be re-evaluated
- Prior versions remain valid but frozen

### 4.3 Emergency Changes

**Examples:**

- Safety violations
- Discovered harmful behavior
- Regulatory risk

**Rules:**

- Prompt may be immediately demoted or revoked
- New version MUST be created for remediation
- Revocation MUST be logged with justification

---

## 5. Deprecation Semantics

### 5.1 Deprecation vs Revocation

| State | Meaning |
|-------|---------|
| Active | Prompt may be used for new executions |
| Deprecated | Prompt may be replayed but not used for new work |
| Revoked | Prompt may not be executed except for forensic replay |

### 5.2 Deprecation Rules

- Deprecation does not invalidate historical runs
- Deprecated prompts MUST:
  - Remain retrievable
  - Remain replayable
  - Be explicitly labeled in logs and UI
- New executions MUST fail if they reference deprecated prompts (unless explicitly allowed for migration)

---

## 6. Trust Level Interaction

Prompt change control integrates directly with ADR-017 Trust Levels.

**Rules:**

- A prompt MAY NOT increase trust level without re-certification
- A prompt MAY be demoted due to:
  - QA findings
  - Failure analytics
  - Human escalation
- Trust demotion MUST NOT retroactively invalidate prior executions

---

## 7. Replay & Comparison Guarantees

Prompt change control exists primarily to protect replay integrity.

**Guarantees:**

- Replay MUST resolve exact prompt versions
- Deprecated or revoked prompts MUST remain accessible for replay
- Comparison tooling MUST surface:
  - Version differences
  - Trust differences
  - Deprecation state

---

## 8. Governance & Audit Requirements

Every prompt change MUST record:

- Prior version
- New version
- Change classification
- Trust impact
- Reason for change
- Author (human or system)
- Timestamp

**No silent prompt evolution is permitted.**

---

## 9. Out of Scope

This ADR does not define:

- Prompt authoring workflows
- UI for prompt editing
- Analytics or learning loops
- Human approval UX

These are addressed in future ADRs.

---

## 10. Consequences

**Positive:**

- Behavioral drift becomes observable
- Failures become attributable
- Replay becomes defensible
- Trust becomes enforceable over time

**Trade-offs:**

- Slower prompt iteration
- Increased governance overhead
- Higher discipline required in development

**This is intentional.**

---

## 11. Summary

Prompts define behavior.  
Behavior must not change silently.  
Trust must survive time.

**Prompt Change Control is the bridge between trust and learning in The Combine.**

Without it, every other governance mechanism eventually collapses under drift.

# ADR-017 — Prompt Certification & Trust Levels

**Status:** Draft  
**Date:** 2026-01-02  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-012 — Interaction Model
- ADR-014 — Quality Assurance Modes
- ADR-015 — Failure States & Escalation Semantics
- ADR-016 — Escalation Targets & Human-in-the-Loop Design

---

## 1. Decision Summary

This ADR establishes a formal certification model for prompts used within The Combine, defining:

- Trust levels for prompts
- Certification requirements per level
- What certified prompts are allowed to do
- How uncertified prompts are constrained
- How trust level influences QA rigor and escalation

**Prompts are treated as governed system artifacts, not configuration or free text.**

---

## 2. Problem Statement

Prompts in The Combine:

- Shape system behavior
- Influence decision boundaries
- Affect risk, safety, and correctness
- Must remain replayable and auditable

Without explicit certification and trust levels:

- Prompt drift becomes invisible
- Behavior changes cannot be attributed
- QA enforcement becomes inconsistent
- User-supplied or ad-hoc prompts can silently override governance

The system requires a trust model that is explicit, enforceable, and logged.

---

## 3. Definitions

**Prompt**  
A structured instruction set provided to an LLM, including role prompts and task prompts.

**Certified Prompt**  
A prompt that has passed defined review criteria and is approved for use at a given trust level.

**Trust Level**  
A classification indicating what authority and scope a prompt is permitted.

**Prompt Fingerprint**  
A deterministic hash of prompt content used for logging and replay.

---

## 4. Core Principles

Prompt governance in The Combine follows these principles:

- **Prompts are code** — they must be versioned, reviewed, and auditable
- **Trust is explicit** — no prompt is implicitly trusted
- **Authority is bounded** — prompts cannot exceed their trust level
- **Certification is separable** — prompts may evolve independently of code
- **Replayability is mandatory** — prompt identity must be recoverable

---

## 5. Trust Levels

The Combine defines the following trust levels.

### 5.1 Core (System-Certified)

**Characteristics:**

- Authored and approved by system maintainers
- Define foundational behavior and constraints
- Cannot be overridden at runtime

**Permissions:**

- Define role identity and authority
- Enforce governance rules
- Block execution
- Trigger escalation paths

**Examples:**

- Role prompts
- QA role prompts
- System-level task prompts

### 5.2 Combine-Certified

**Characteristics:**

- Reviewed and approved prompts
- Governed but extensible
- Versioned and fingerprinted

**Permissions:**

- Perform scoped tasks
- Produce governed artifacts
- Participate in QA loops

**Constraints:**

- Cannot redefine role identity
- Cannot bypass QA or logging
- Must operate within defined schemas

**Examples:**

- Task prompts (discovery, backlog creation, architecture documentation)

### 5.3 Community / Extension

**Characteristics:**

- Third-party or user-authored
- Not system-reviewed
- Allowed only via composition

**Permissions:**

- Provide supplemental context
- Influence content within strict boundaries

**Constraints:**

- Cannot issue instructions
- Cannot override certified prompts
- Treated as untrusted input

**Examples:**

- User-provided guidance
- Domain reference text
- External templates

### 5.4 Uncertified (Untrusted)

**Characteristics:**

- Ad hoc or runtime-provided
- No review or guarantees

**Permissions:**

- Context only

**Hard Constraints:**

- Must never be treated as instruction
- Must not influence control flow
- Must not modify behavior boundaries

**All uncertified prompts are treated as data, not logic.**

---

## 6. Prompt Composition Rules

When multiple prompts are used together:

- Higher trust prompts dominate lower trust prompts
- Lower trust prompts may only supply context
- Instruction channels are reserved for certified prompts
- Conflicts must be resolved in favor of higher trust

**No prompt may escalate its own trust level.**

---

## 7. QA Implications

Trust level influences QA behavior:

- **Core prompts:** subject to the strictest QA and change control
- **Certified prompts:** validated against schemas and constraints
- **Uncertified prompts:** ignored for instruction evaluation

QA must verify:

- Prompt trust level
- Prompt fingerprint consistency
- No instruction leakage from lower-trust content

---

## 8. Logging & Replay Requirements

Per ADR-010, every execution must log:

- Prompt ID
- Prompt version
- Trust level
- Prompt fingerprint (hash)
- Composition order

Replay must reproduce:

- Exact prompt content
- Trust boundaries
- QA outcomes

---

## 9. Governance Alignment

This ADR enforces:

- **ADR-009:** explicit, traceable governance of behavior
- **ADR-010:** full execution observability
- **ADR-012:** separation of worker, QA, and escalation roles
- **ADR-016:** controlled escalation based on certified behavior

**Prompt certification violations are governance failures, not runtime errors.**

---

## 10. Out of Scope

This ADR does not define:

- UI for managing prompts
- Approval workflows
- Storage mechanisms
- Prompt authoring tools

These are implementation concerns.

---

## 11. Drift Risks

Primary risks include:

- Treating prompts as configuration
- Allowing uncertified prompts to issue instructions
- Silent prompt edits without version bumps
- Over-certification that blocks evolution

Any relaxation of trust boundaries requires a new ADR.

---

## 12. Open Questions

- Should certification require human sign-off or automated checks?
- Are there intermediate trust levels needed?
- How are deprecated prompts handled?
- Can trust level influence cost or performance limits?

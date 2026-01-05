# ADR Acceptance Checklist (Canonical)

An ADR may be marked **Accepted** only when all applicable checks pass.

---

## 1. Structural Integrity

- [ ] ADR has a clear, stable title that matches its scope
- [ ] ADR status is explicitly set (`Draft`, `Proposed`, `Accepted`, etc.)
- [ ] Decision is stated unambiguously in the Decision Summary
- [ ] Non-goals are explicitly listed (prevents scope creep)

---

## 2. Architectural Consistency

- [ ] Terminology is consistent with accepted ADRs
- [ ] No hard-coded domain assumptions leak into pattern-level ADRs
- [ ] Responsibilities are clearly bounded (what this ADR governs vs. defers)
- [ ] No contradictions with higher- or same-layer ADRs

---

## 3. Cross-ADR Alignment

- [ ] All referenced ADRs exist and are correctly titled
- [ ] Related ADR list reflects current accepted architecture
- [ ] This ADR neither redefines nor duplicates another ADR's authority
- [ ] Any delegation ("see ADR-XXX") is explicit and intentional

---

## 4. Implementation Mappability

- [ ] Every major rule can be enforced or validated mechanically
- [ ] No requirement relies on "good behavior" or implicit interpretation
- [ ] States, gates, or constraints can be represented in code
- [ ] Failure conditions are explicit (not silent or implied)

---

## 5. Enforcement & Failure Semantics

- [ ] Violations result in explicit failure states
- [ ] No "soft" bypasses or undefined fallback behavior
- [ ] Failure handling is delegated appropriately (or explicitly out of scope)
- [ ] Auditability is preserved (decisions, transitions, outcomes)

---

## 6. Scope & Authority Boundaries

- [ ] Human vs. agentic authority is clearly separated
- [ ] Gates (QA, Acceptance, Clarification) have defined roles and powers
- [ ] No role is allowed to self-certify its own output
- [ ] Authority escalation paths are not ambiguous

---

## 7. Longevity & Stability

- [ ] ADR does not lock in version numbers of dependent artifacts
- [ ] ADR defines patterns, not instances (unless explicitly intended)
- [ ] ADR can survive new workflows, roles, or document types
- [ ] ADR avoids premature optimization or speculative features

---

## 8. Fit Within the Layered Model

- [ ] ADR cleanly belongs to one architectural layer:
  - Governance
  - Interaction
  - Workflow
  - Artifact
  - Enforcement
- [ ] ADR does not straddle layers without explicit justification
- [ ] ADR does not introduce hidden coupling across layers

---

## 9. "Sharp Edge" Test

Ask explicitly:

- [ ] Could a reasonable implementer misinterpret this?
- [ ] Could a shortcut undermine this without detection?
- [ ] Could two ADRs be followed simultaneously and still conflict?

**If yes to any → Not Accepted**

---

## 10. Final Acceptance Gate

- [ ] All checklist items reviewed
- [ ] Known gaps explicitly recorded (and intentionally deferred)
- [ ] ADR produces no unresolved architectural tension
- [ ] ADR strengthens the system, not just documents it

---

**➡️ Status may now be set to `Accepted`**

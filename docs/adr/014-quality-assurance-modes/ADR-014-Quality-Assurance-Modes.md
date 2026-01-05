# ADR-014 — Quality Assurance Modes

**Status:** Draft (Scaffold)  
**Date:** 2026-01-02  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-012 — Interaction Model

---

## 1. Decision Summary

This ADR defines the Quality Assurance (QA) modes available within The Combine and the constraints governing their use.

QA modes establish *how* validation is performed, not *what* is being validated.

---

## 2. Problem Statement

Not all validation requires the same mechanism.

Some checks are:

- Deterministic
- Mechanical
- Schema- or rule-based

Others require:

- Judgment
- Semantic reasoning
- Contextual risk assessment

Without explicit QA modes:

- Validation responsibilities blur
- Human-like judgment leaks into mechanical checks
- "Fast paths" emerge that bypass appropriate scrutiny
- Auditability degrades

The Combine requires explicit QA modes with clear boundaries and authority.

---

## 3. Definitions

**QA Mode**  
A formally defined method of evaluating an artifact.

**Mechanical QA**  
Validation performed using deterministic rules, schemas, or programs.

**Agentic QA**  
Validation performed by an LLM operating under a certified QA role prompt.

**QA Authority**  
The right to approve or reject an artifact for progression or release.

---

## 4. Supported QA Modes (Conceptual)

This ADR recognizes the existence of multiple QA modes, including but not limited to:

- Mechanical QA
- Agentic QA
- Hybrid QA (composition of modes)

This section defines categories, not implementations.

---

## 5. Mechanical QA (Conceptual)

Mechanical QA is characterized by:

- Deterministic evaluation
- Explicit pass/fail criteria
- Replayable outcomes

Typical characteristics:

- Schema validation
- Structural completeness checks
- Constraint enforcement
- Static analysis

Mechanical QA must not:

- Interpret intent
- Make assumptions
- Repair outputs

---

## 6. Agentic QA (Conceptual)

Agentic QA is characterized by:

- Semantic evaluation
- Risk assessment
- Judgment under uncertainty

Typical characteristics:

- Evaluating adherence to instructions
- Detecting hallucination or unsafe assumptions
- Assessing structural or logical coherence

Agentic QA must not:

- Modify artifacts
- Replace mechanical checks
- Self-certify its own outputs

---

## 7. Composition Rules

If multiple QA modes are used:

- Their order must be explicit
- Their authority boundaries must be clear
- Failure in any required mode must block progression

Implicit or ad hoc composition is prohibited.

---

## 8. Governance & Audit Alignment

All QA modes must comply with:

- **ADR-009** — explicit decisions and traceability
- **ADR-010** — loggable inputs, outputs, and outcomes

QA mode selection and results must be auditable.

---

## 9. Out of Scope

This ADR does not define:

- Specific schemas or validation rules
- Prompt content for QA roles
- Performance optimizations
- UI representation of QA results

---

## 10. Drift Risks

Primary risks include:

- Treating agentic QA as advisory
- Allowing agentic QA to bypass mechanical checks
- Collapsing QA modes into a single opaque step
- Introducing undocumented "fast validation" paths

Any expansion of QA authority requires a new ADR.

---

## 11. Open Questions

- When is agentic QA mandatory vs optional?
- Can QA modes be task-specific?
- How are conflicting QA results resolved?
- Are QA modes configurable per document type?

These questions are intentionally deferred.

# ADR-023 — Regulatory Readiness & Audit Export Model

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-01-02

---

## 1. Context

The Combine is explicitly designed for environments where:

- Decisions must be explainable
- Errors must be traceable
- Human accountability must be provable

Internal auditability (ADR-009, ADR-010) is necessary but insufficient.

This ADR defines how the system supports external audit, regulatory inquiry, and compliance review.

---

## 2. Decision

The Combine MUST be able to produce complete, coherent audit exports without requiring live system access or internal interpretation.

**Audit readiness is a design invariant, not a deployment option.**

---

## 3. Audit Export Scope

An audit export MUST be able to include:

- Execution records
- Prompt versions and trust levels
- QA findings
- Human decisions
- Failure classifications
- Change histories
- Replay artifacts

Exports MUST be:

- Read-only
- Tamper-evident
- Self-describing

---

## 4. Export Boundaries

Audit exports MUST NOT include:

- Model internals
- Proprietary weights
- Hidden chain-of-thought
- User secrets unless explicitly authorized

**Transparency does not require exposure of internals.**

---

## 5. Export Granularity

Exports MUST support at least:

- Single execution
- Prompt lineage
- Time-bounded window
- Incident-focused bundle

Granularity MUST be explicit at export time.

---

## 6. Traceability Guarantees

Every exported artifact MUST be traceable to:

- A unique execution ID
- A correlation ID
- A timestamp
- A governing prompt version
- A trust level at time of execution

**If traceability cannot be proven, the export is invalid.**

---

## 7. Human Accountability in Audits

Audit exports MUST clearly distinguish:

- System-generated outputs
- QA judgments
- Human decisions and overrides

**No export may blur authorship.**

---

## 8. Replay Compatibility

Audit exports MUST be compatible with replay tooling.

An auditor SHOULD be able to:

- Reconstruct context
- Replay decisions
- Observe failure paths
- Identify divergence causes

---

## 9. Governance Alignment

This ADR formalizes the external-facing implications of:

- **ADR-009** (auditability)
- **ADR-010** (execution logging)
- **ADR-016** (human-in-the-loop)
- **ADR-021** (decision capture)

---

## 10. Out of Scope

This ADR does not define:

- Regulatory frameworks (HIPAA, SOX, etc.)
- Export file formats
- Storage or retention policies

---

## 11. Consequences

**Positive:**

- Enterprise credibility
- Regulatory defensibility
- Reduced institutional risk

**Trade-off:**

- Higher data retention cost
- Increased design discipline

**These are acceptable.**

---

## 12. Summary

If you cannot explain it, you cannot ship it.

**This ADR ensures The Combine is audit-ready by construction, not by apology.**

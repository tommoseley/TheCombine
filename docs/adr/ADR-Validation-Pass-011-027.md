# ADR Validation Pass: ADR-011 ↔ ADR-027 ↔ Workflow Schema

**Date:** 2026-01-02  
**Validator:** Claude  
**Scope:** Cross-document consistency check

---

## 1. Purpose

Verify alignment between:

- **ADR-011** — Document Ownership Model (pattern)
- **ADR-027** — Workflow Definition & Governance (instance)
- **Workflow Schema** — Implementation Model (enforcement)

---

## 2. Methodology

### 2.1 Validation Matrix Approach

Each constraint in ADR-011 was checked against:

1. Whether ADR-027 references or implements it
2. Whether the schema provides mechanical enforcement
3. Whether gaps exist that could allow violations

### 2.2 Categories Evaluated

| Category | Source |
|----------|--------|
| Ownership Declaration | ADR-011 §2 |
| Structural Constraints | ADR-011 §3 |
| Reference Rules | ADR-011 §5 |
| Discovery Scope | ADR-011 §6 |
| Workflow Structure | ADR-027 §5 |

---

## 3. Validation Results

### 3.1 Ownership Constraints (ADR-011 §2)

| Rule | ADR-027 | Schema | Status |
|------|---------|--------|--------|
| §2.1 Ownership MUST be explicit | §5 mentions artifact ownership | `document_types.may_own[]` | ✅ Aligned |
| §2.2 Ownership is exclusive | Implied | Single `parent_doc_type` per entity | ✅ Aligned |
| §2.2 Document may be root | Implied | Top-level docs have `may_own: []` | ✅ Aligned |
| §2.3 Ownership creates scope | §5 mentions scope | `scope` field on types/steps | ✅ Aligned |
| §2.4 Violations cause failure | §6 requires explicit failure | `_validate_ownership_dag()` | ✅ Aligned |

### 3.2 Structural Constraints (ADR-011 §3)

| Rule | ADR-027 | Schema | Status |
|------|---------|--------|--------|
| §3.1 DAG required, no cycles | Not explicit | `_validate_ownership_dag()` | ✅ Enforced |
| §3.2 Child scope ≤ parent | Not explicit | `_validate_scope_consistency()` | ✅ Enforced |

### 3.3 Reference Rules (ADR-011 §5)

| Rule | Schema Enforcement | Status |
|------|-------------------|--------|
| §5.1 Child → Parent: Permitted | `_validate_reference_rules()` | ✅ Enforced |
| §5.1 Child → Ancestor: Permitted | `_validate_reference_rules()` | ✅ Enforced |
| §5.2 Sibling → Sibling: Forbidden | `_validate_reference_rules()` | ✅ Enforced |
| §5.2 Cross-branch: Forbidden | `_validate_reference_rules()` | ✅ Enforced |
| §5.3 Parent → Child: Forbidden | `_validate_reference_rules()` | ✅ Enforced |

### 3.4 Discovery Scope (ADR-011 §6)

| Rule | Schema Enforcement | Status |
|------|-------------------|--------|
| Discovery only at owning docs | Not enforced | ⚠️ Deferred |
| Leaf docs MUST NOT discover | Not enforced | ⚠️ Deferred |

**Deferred Resolution:** Infer from `may_own` — if empty, document is a leaf. Implement when discovery prompts are formalized.

### 3.5 ADR-027 §5 Coverage

| Requirement | Schema Implementation | Status |
|-------------|----------------------|--------|
| Eligible Roles | `steps[].role` | ✅ Aligned |
| Permitted Task Types | `steps[].task_prompt` | ✅ Aligned |
| Artifact Ownership | `document_types[].may_own` | ✅ Aligned |
| Gate Requirements | `document_types[].acceptance_required` | ✅ Aligned |
| Termination Conditions | Implicit (end of steps) | ✅ Clarified |

---

## 4. Gaps Identified

### 4.1 Fixed During This Pass

| Gap | Resolution |
|-----|------------|
| ADR-027 missing ADR-011 reference | Added to Related ADRs |
| Reference rules not enforced | Added `_validate_reference_rules()` |
| Termination conditions unclear | Clarified as implicit in v1 |

### 4.2 Deferred

| Gap | Reason | Future Resolution |
|-----|--------|-------------------|
| Discovery scope validation | Discovery prompts not formalized | Infer from `may_own` when needed |
| Explicit termination conditions | Not needed for v1 | Add schema field in v2 if needed |

---

## 5. Summary

### 5.1 Alignment Score

| Category | Aligned | Gaps | Deferred |
|----------|---------|------|----------|
| Ownership Declaration | 5/5 | 0 | 0 |
| Structural Constraints | 2/2 | 0 | 0 |
| Reference Rules | 5/5 | 0 | 0 |
| Discovery Scope | 0/2 | 0 | 2 |
| ADR-027 §5 Coverage | 5/5 | 0 | 0 |
| Cross-references | 2/2 | 0 | 0 |
| **Total** | **19/21** | **0** | **2** |

### 5.2 Final Status

**ADR-011 ↔ ADR-027 ↔ Schema: ✅ VALIDATED**

All critical alignment issues resolved. Deferred items are non-blocking and have documented resolution paths.

---

## 6. Approval

This validation pass confirms that:

1. ADR-011 defines the ownership pattern
2. ADR-027 defines workflow instances
3. The Implementation Model enforces both mechanically
4. No contradictions exist between the three documents

**Pattern vs. Instance separation: Confirmed**  
**Mechanical enforcement: Implemented**  
**Cross-references: Complete**

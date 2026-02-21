# ADR-053 — Planning Before Architecture in Software Product Development

**Status:** Accepted
**Date:** 2026-02-20
**Supersedes:** Implicit pre-WP ordering from Epic/Feature pipeline

---

## Decision

The canonical document order within the `software_product_development` POW shall be:

Discovery
-> Implementation Plan Primary (IPP)
-> Implementation Plan (IPF)
-> Technical Architecture (TA)
-> Work Package execution

Planning defines scope.
Architecture constrains execution.
Architecture does not silently reshape scope.

Technical Architecture is an advisory, constraint-bearing artifact -- not a structural authority over committed Work Packages.

---

## Context

With ADR-051 (Work Package as Runtime Primitive) and ADR-052 (Document Pipeline Integration for WP/WS), the Combine shifted from Epic/Feature hierarchy to Work Package/Work Statement hierarchy.

Under this ontology:

- IPP identifies candidate Work Packages.
- IPF reconciles and commits Work Packages.
- Work Packages are first-class execution artifacts.
- TA emits architectural constraints and ADR candidates.

A decision was required regarding whether TA precedes or follows IPF in canonical workflow order.

---

## Options Considered

### Option A -- TA Before IPF

Discovery -> IPP -> TA -> IPF -> Work Packages

Implications:

- Architecture influences scope before commitment.
- Structural coupling between TA and IPF.
- Risk of architecture dominating value decomposition.

### Option B -- IPF Before TA (Chosen)

Discovery -> IPP -> IPF -> TA -> Work Packages

Implications:

- Scope decomposition is value-first.
- Architecture evaluates committed scope.
- TA may surface constraints, risks, ADR candidates.
- Structural change requires explicit operator action.

---

## Rationale

The Combine's governing principles:

- Intent-first planning
- Explicit structural authority
- Deterministic artifact lifecycle
- No silent mutation of execution artifacts

If TA precedes IPF, architecture implicitly acquires structural authority over scope.

Placing TA after IPF:

- Preserves separation of concerns
- Keeps Work Package identities stable
- Makes structural changes explicit
- Reduces churn and reconciliation storms

Planning decomposes.
Architecture constrains.

---

## Consequences

### Positive

- Clear authority boundary between planning and architecture
- Stable Work Package identities
- Simplified staleness propagation
- Reduced structural volatility
- Cleaner mental model for operators

### Negative

- Architecture may discover structural tensions after WPs are committed.
- Resolving architectural conflicts requires an explicit reconciliation cycle.

### Concrete Feedback Loop

If TA produces findings that materially conflict with committed Work Packages:

1. Operator reviews TA findings.
2. Operator chooses one of:
   - (A) Accept architectural constraints without restructuring WPs.
   - (B) Trigger an explicit IPF re-reconciliation cycle.
3. Reconciliation updates WPs through normal IPF commit logic.

No automatic restructuring occurs as a side effect of TA generation.

---

## Enforcement Level

### Phase 1 -- Declarative (Now)

POW node order enforces canonical sequence.

### Phase 2 -- Soft Enforcement (Optional Future)

- UI discourages WS generation before TA.
- TA conflict indicators on WPs.

### Phase 3 -- Hard Enforcement (Optional Future)

- Prevent WP acceptance without TA.
- Require explicit override for structural conflicts.

---

## Summary

Architecture informs.
Planning defines.
Structural mutation must be explicit.

ADR accepted.

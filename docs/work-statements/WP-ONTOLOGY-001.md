# WP-ONTOLOGY-001: Unify Combine Pipeline Around Work Packages and Work Statements

## Status: Accepted

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline Integration for WP/WS

---

## Intent

Replace Epic/Feature ontology with Work Package ? Work Statement model as the sole execution hierarchy. No dual pipelines. No migration scaffolding. Clean pivot.

---

## Scope In

- WP and WS as first-class document types (in existing document store)
- IPP outputs `work_package_candidates[]`
- IPF reconciles to committed WPs
- WS must belong to a WP (no orphan WS)
- WS acceptance appends to Project Logbook (transactional)
- Production Floor renders WP ? WS only
- Epic pipeline fully removed

## Scope Out

- Program-level runtime objects or program logbooks
- Auto WS generation DCW from WP
- TA emitting ADR artifacts
- Advanced analytics or projections

---

## Key Design Principle

WP is a first-class document type in the existing artifact store; runtime state is represented via document fields (with optional projections later). No parallel domain model.

---

## Definition of Done

1. Epic doc types are removed/blocked (no creation, no schema, no UI nodes)
2. IPP/IPF emit and reconcile WPs only
3. WS cannot exist without parent WP
4. Project Logbook auto-append verified (on WS acceptance)
5. Production Floor shows only WP/WS hierarchy
6. Tier 0 green

---

## Execution Order

1. WS-ONTOLOGY-001 -- Work Package Document Type
2. WS-ONTOLOGY-002 -- Work Statement Document Type + Parent Enforcement
3. WS-ONTOLOGY-003 -- Project Logbook + Auto-Append
4. WS-ONTOLOGY-004 -- IPP Schema/Prompt Swap
5. WS-ONTOLOGY-005 -- IPF Reconciliation Update
6. WS-ONTOLOGY-006 -- Remove Epic/Feature Pipeline
7. WS-ONTOLOGY-007 -- Production Floor UI

Each WS depends on the previous. Execute in order.

---

_End of WP-ONTOLOGY-001_

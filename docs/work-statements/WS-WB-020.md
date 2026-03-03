# WS-WB-020: Define Mechanical Document Readiness Gate for TA Consumption

**Parent:** WP-WB-002
**Dependencies:** None

## Problem

"TA stabilized" is ambiguous in current model (status vs lifecycle_state). We need a deterministic condition for "TA can be used as binding input".

## Deliverable

A single, testable predicate used by WB and future stations.

## Requirements

- Implement `is_doc_ready_for_downstream(doc)` (or TA-specific variant) with explicit rules.
- Rules must use fields that actually exist in the document model.
- Add Tier-1 tests covering:
  - ready state
  - draft/active/stale/archived combinations as applicable
  - missing fields behavior (hard fail vs not-ready)

## Acceptance

- Predicate is used by WB propose station gate (WS-WB-025)
- Tests prove semantics and prevent regressions

## Allowed Paths

- `app/domain/services/` (new or existing readiness module)
- `tests/tier1/`

## Prohibited

- Do not redesign document lifecycle broadly
- Do not modify the Document model schema

# WS-WB-024: Audit Events for Proposal Station

**Parent:** WP-WB-002
**Dependencies:** None

## Deliverables

- Add event types and structured payload definitions to WB audit service:
  - `WB_WS_PROPOSAL_REQUESTED`
  - `WB_WS_PROPOSAL_REJECTED` (gate failures)
  - `WB_WS_PROPOSED` (per WS persisted)
  - `WB_WP_WS_INDEX_UPDATED`

## Requirements

- Events emitted for all mutation paths and for rejection paths
- Tier-1 tests assert audit events are written

## Acceptance

- Every propose run is reconstructible from audit stream

## Allowed Paths

- `app/domain/services/wb_audit_service.py`
- `tests/tier1/`

## Prohibited

- Do not modify existing audit event types or their payloads
- Do not change the audit event builder signature

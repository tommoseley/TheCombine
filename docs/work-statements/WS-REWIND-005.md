# WS-REWIND-005 — Automatic Destabilization

**Status:** Draft
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

When upstream rewind occurs, automatically revoke stabilization status of dependent WPs and WSs so they cannot be promoted or used as if stable.

## Scope

### In Scope
- When rewind marks a WP stale, all child WSs also become stale
- Stabilization status (if tracked) is revoked for stale artifacts
- Integration with rewind service: destabilization fires as part of rewind execution
- Stabilization state on document content (`governance_pins`, lifecycle_state) updated

### Out of Scope
- Re-stabilization after regeneration (user must re-stabilize)
- UX for destabilization visibility
- Partial destabilization (all-or-nothing per WP)

## Procedure

### Step 1: Identify stabilization state locations
- Check Document.lifecycle_state (generating/partial/complete/stale)
- Check Document.accepted_at / accepted_by fields
- Check WP content governance_pins if stabilization is tracked there

### Step 2: Implement destabilization logic
- Create `app/domain/services/destabilization_service.py`
- `destabilize_downstream(project_id, stale_document_ids) → list[destabilized_ids]`
  - For each stale WP: find child WSs, mark them stale too
  - Reset lifecycle_state to 'stale'
  - Clear accepted_at / accepted_by (revoke acceptance)
  - Record destabilization in lineage

### Step 3: Wire into rewind service
- After `mark_stale()` in rewind service, call `destabilize_downstream()`
- Destabilization happens atomically with the rewind

### Step 4: Write tests
- Test: rewind at TA destabilizes all WPs and WSs
- Test: rewind at WP destabilizes child WSs
- Test: rewind at WS only affects that WS
- Test: lifecycle_state set to 'stale'
- Test: accepted_at cleared

## Verification Criteria
- Stale WPs have their child WSs also marked stale
- Lifecycle state is revoked
- Acceptance state is cleared
- Destabilization is atomic with rewind
- Tests pass

## Allowed Paths
- app/domain/services/destabilization_service.py
- app/domain/services/rewind_service.py (integration)
- tests/tier1/test_destabilization.py

## Prohibited Actions
- Do not implement re-stabilization
- Do not partially destabilize (all children of a stale WP must become stale)
- Do not build UX for destabilization

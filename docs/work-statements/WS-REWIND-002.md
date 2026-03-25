# WS-REWIND-002 — Artifact Status Model

**Status:** Draft
**Parent WP:** WP-REWIND-001
**Governing ADR:** ADR-063

## Objective

Implement the MVP artifact status model (current / stale / superseded) with deterministic transition rules and guards.

## Scope

### In Scope
- Status enum: current, stale, superseded
- Legal transition rules (current→stale, stale→superseded, current→superseded)
- Transition guard function that rejects illegal transitions
- Integration with existing `Document.status` column

### Out of Scope
- Schema migration (existing `status` column already supports string values)
- Regeneration logic
- UI status display

## Procedure

### Step 1: Define status enum and transitions
- Create `app/domain/models/artifact_status.py`
- Define `ArtifactStatus` enum: CURRENT, STALE, SUPERSEDED
- Define `LEGAL_TRANSITIONS` dict mapping each status to its allowed next statuses
- Create `validate_transition(from_status, to_status)` → bool

### Step 2: Create status transition service
- Create `app/domain/services/artifact_status_service.py`
- `mark_stale(document_id, reason)` → transitions current→stale
- `mark_superseded(document_id, replacement_id)` → transitions stale→superseded
- Both must validate transition legality before executing
- Both must record the transition reason

### Step 3: Write tests
- Test all legal transitions succeed
- Test illegal transitions are rejected (stale→current, superseded→current)
- Test mark_stale with valid current document
- Test mark_stale rejects already-stale document
- Test mark_superseded links to replacement

## Verification Criteria
- Three statuses defined with no extras
- Transition guards prevent illegal status changes
- mark_stale and mark_superseded are deterministic
- Tests cover all transition paths

## Allowed Paths
- app/domain/models/artifact_status.py
- app/domain/services/artifact_status_service.py
- tests/tier1/test_artifact_status.py

## Prohibited Actions
- Do not add statuses beyond the MVP three
- Do not modify the documents table schema
- Do not implement rewind or regeneration logic

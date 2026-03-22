# WS-REWIND-016 — Rewind Action UI

**Status:** Draft
**Parent WP:** WP-REWIND-004
**Governing ADR:** ADR-063

## Objective

Add a user-facing control to rewind the pipeline from a selected stage, calling the rewind API endpoint.

## Scope

### In Scope
- "Rewind to here" button/action on pipeline stage indicators
- Confirmation dialog before rewind (destructive-ish action)
- Call `POST /api/v1/projects/{project_id}/rewind` with selected stage
- Display rewind result (affected count, new state)
- Refresh pipeline view after rewind

### Out of Scope
- Regeneration trigger from UI (separate action)
- Undo rewind
- Batch rewind across projects

## Procedure

### Step 1: Add rewind control to pipeline stage view
- On each pipeline stage indicator (CI, PD, TA, IP, WP, WS), add a "Rewind to here" action
- Only visible when the stage has a current document (can't rewind to empty stages)

### Step 2: Confirmation dialog
- "This will mark all documents from [stage] onward as stale. Continue?"
- Show count of documents that will be affected (call impact evaluator first if practical)

### Step 3: Execute rewind
- Call rewind API endpoint
- Handle success: refresh pipeline view, show result summary
- Handle failure: show error message from API

### Step 4: Write tests
- Test: rewind button visible on stages with current documents
- Test: confirmation dialog shows before executing
- Test: successful rewind refreshes pipeline state
- Test: API error displayed to user

## Verification Criteria
- User can rewind from any pipeline stage
- Confirmation prevents accidental rewind
- Pipeline view updates after rewind
- Errors are surfaced clearly

## Allowed Paths
- spa/src/components/
- spa/src/api/

## Prohibited Actions
- Do not implement undo/reverse rewind
- Do not trigger regeneration from the rewind action

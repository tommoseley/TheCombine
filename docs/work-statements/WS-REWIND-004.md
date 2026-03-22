# WS-REWIND-004 — Rewind Service

**Status:** Draft
**Parent WP:** WP-REWIND-001
**Governing ADR:** ADR-063

## Objective

Create the application service that accepts a rewind request, evaluates impact, marks downstream artifacts stale, records lineage, and returns the new active rewind point.

## Scope

### In Scope
- Rewind service accepting: project_id, rewind_to_stage, reason, actor
- Calls rewind impact evaluator to determine affected documents
- Calls artifact status service to mark affected documents stale
- Records lineage event (WS-REWIND-006)
- Returns rewind result: affected document count, new active stage, stale artifact list
- API endpoint: `POST /api/v1/projects/{project_id}/rewind`

### Out of Scope
- Regeneration (WP-REWIND-003)
- Automatic triggers (manual only)
- Destabilization (WP-REWIND-003)
- UX (WP-REWIND-004)

## Procedure

### Step 1: Create rewind request model
- `RewindRequest`: rewind_to_stage (PipelineStage), reason (str), actor (str)
- Validate: stage must be a valid PipelineStage
- Validate: project must exist

### Step 2: Create rewind service
- Create `app/domain/services/rewind_service.py`
- `execute_rewind(project_id, request) → RewindResult`
  1. Call `evaluate_rewind_impact(request.rewind_to_stage)`
  2. Call `get_affected_documents(project_id, affected_stages)`
  3. For each affected document, call `mark_stale(document_id, reason)`
  4. Record lineage event
  5. Return `RewindResult(affected_count, new_active_stage, stale_document_ids)`

### Step 3: Create API endpoint
- `POST /api/v1/projects/{project_id}/rewind`
- Request body: `RewindRequest`
- Response: `RewindResult`
- Requires project to exist
- Returns 400 if stage is invalid

### Step 4: Write tests
- Test: rewind at TA marks TA, IP, WP, WS documents stale
- Test: rewind at CI marks everything stale
- Test: rewind with no downstream documents succeeds (0 affected)
- Test: invalid stage returns 400
- Test: rewind records lineage event

## Verification Criteria
- Rewind service marks correct documents stale
- Lineage event is recorded
- API endpoint accepts and validates requests
- No documents outside the affected stages are modified
- Tests pass

## Allowed Paths
- app/domain/services/rewind_service.py
- app/api/v1/routers/projects.py (add endpoint)
- tests/tier1/test_rewind_service.py

## Prohibited Actions
- Do not implement regeneration
- Do not implement automatic triggers
- Do not modify document content (only status)
- Do not implement destabilization logic

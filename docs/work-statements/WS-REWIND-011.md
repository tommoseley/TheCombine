# WS-REWIND-011 — Regeneration Entrypoint

**Status:** Draft
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

Add the service/action that restarts document generation from the active rewind stage, producing new current artifacts that supersede the stale ones.

## Scope

### In Scope
- API endpoint: `POST /api/v1/projects/{project_id}/regenerate`
- Accept: stage to regenerate from (must be a stale stage)
- Trigger the existing document generation pipeline from that stage
- New documents become current; old stale documents become superseded
- Record regeneration in lineage events

### Out of Scope
- Partial regeneration (regenerate full downstream for MVP)
- Automatic regeneration after rewind (user must trigger explicitly)
- UI for regeneration

## Procedure

### Step 1: Create regeneration request model
- `RegenerateRequest`: from_stage (PipelineStage)
- Validate: stage must have stale artifacts for this project
- Validate: all upstream stages must have current artifacts

### Step 2: Create regeneration service
- Create `app/domain/services/regeneration_service.py`
- `execute_regeneration(project_id, from_stage) → RegenerationResult`
  1. Verify preconditions (stale artifacts exist, upstream is current)
  2. Trigger document generation for the stage (reuse existing pipeline)
  3. Mark old stale artifacts as superseded
  4. Record lineage event (type='regeneration')
  5. Return result with new document IDs

### Step 3: Create API endpoint
- `POST /api/v1/projects/{project_id}/regenerate`
- Request body: `RegenerateRequest`
- Response: `RegenerationResult`
- Returns 400 if preconditions not met

### Step 4: Write tests
- Test: regeneration creates new current document
- Test: old stale document becomes superseded
- Test: fails if upstream stages don't have current artifacts
- Test: fails if no stale artifacts exist at requested stage
- Test: lineage event recorded

## Verification Criteria
- Regeneration creates new versioned documents
- Old stale documents transition to superseded
- Precondition validation prevents invalid regeneration
- Lineage events track regeneration
- Tests pass

## Allowed Paths
- app/domain/services/regeneration_service.py
- app/api/v1/routers/projects.py (add endpoint)
- tests/tier1/test_regeneration_service.py

## Prohibited Actions
- Do not implement automatic regeneration
- Do not implement partial regeneration
- Do not build regeneration UI

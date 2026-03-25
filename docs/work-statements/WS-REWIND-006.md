# WS-REWIND-006 — Lineage Event Recording

**Status:** Draft
**Parent WP:** WP-REWIND-001
**Governing ADR:** ADR-063

## Objective

Persist rewind lineage events so the system can answer: what changed, why, what became stale, and what replaced it.

## Scope

### In Scope
- Lineage event model and table
- Record: trigger_source, actor, reason, rewind_stage, affected_document_ids, timestamp
- Query interface for lineage events by project
- Integration with rewind service (WS-REWIND-004)

### Out of Scope
- Regeneration tracking (deferred to WP-REWIND-003)
- UI visualization of lineage
- Branch/thread semantics

## Procedure

### Step 1: Create lineage event model
- Create `app/domain/models/lineage_event.py` (or add to existing models)
- Fields:
  - id: UUID (primary key)
  - project_id: UUID (FK to projects)
  - event_type: str ('rewind')
  - rewind_to_stage: str (PipelineStage value)
  - reason: str
  - actor: str
  - affected_document_ids: JSONB (list of UUIDs)
  - created_at: datetime

### Step 2: Create alembic migration
- Add `lineage_events` table
- Index on project_id and created_at

### Step 3: Create lineage service
- Create `app/domain/services/lineage_service.py`
- `record_rewind_event(project_id, rewind_stage, reason, actor, affected_ids) → LineageEvent`
- `get_events_for_project(project_id) → list[LineageEvent]`

### Step 4: Add API endpoint
- `GET /api/v1/projects/{project_id}/lineage` → list of lineage events
- Ordered by created_at descending

### Step 5: Write tests
- Test: record_rewind_event persists correctly
- Test: get_events_for_project returns events in order
- Test: event captures all required fields
- Test: API endpoint returns events

## Verification Criteria
- Lineage events table exists with correct schema
- Events are persisted during rewind
- Events are queryable by project
- All required fields are captured
- Tests pass

## Allowed Paths
- app/domain/models/lineage_event.py
- app/domain/services/lineage_service.py
- app/api/v1/routers/projects.py (add endpoint)
- alembic/versions/
- tests/tier1/test_lineage_service.py

## Prohibited Actions
- Do not track regeneration events yet (deferred)
- Do not build lineage visualization
- Do not implement branch/thread semantics

# WS-REWIND-010 — Stale Artifact Query Filtering

**Status:** Draft
**Parent WP:** WP-REWIND-002
**Governing ADR:** ADR-063

## Objective

Update repository and query behavior so stale/superseded artifacts are excluded from normal downstream execution unless explicitly requested for audit.

## Scope

### In Scope
- Default query mode: return only current artifacts
- Audit query mode: return all versions including stale/superseded
- Update list_by_space() to filter by status
- Update API endpoints that list documents to respect status filtering
- Add `include_historical=false` parameter to relevant endpoints

### Out of Scope
- Individual document retrieval by ID (always returns the exact document)
- Schema changes
- Binder rendering logic (separate concern)

## Procedure

### Step 1: Update list_by_space()
- Add `status_filter` parameter, default = ['current']
- When `status_filter` is provided, add WHERE clause on status
- When `include_all=True`, skip status filter (audit mode)

### Step 2: Update relevant API endpoints
- `GET /projects/{project_id}/documents` — add `?include_historical=false` query param
- `GET /projects/{project_id}/tree` — filter to current artifacts only by default
- Endpoints that return single documents by ID remain unchanged (exact lookup)

### Step 3: Maintain backward compatibility
- Default behavior returns same results as before (all existing docs are 'current')
- Only after rewind creates stale docs does filtering have visible effect

### Step 4: Write tests
- Test: list_by_space default returns only current
- Test: list_by_space with include_all returns all statuses
- Test: API endpoints respect include_historical parameter
- Test: single document by ID always returns regardless of status
- Test: backward compat — no behavioral change when all docs are current

## Verification Criteria
- Default queries exclude stale and superseded artifacts
- Audit mode returns all versions
- API parameter works correctly
- Single-document lookups unaffected
- Backward compatible with existing behavior
- Tests pass

## Allowed Paths
- app/api/services/document_service.py
- app/api/v1/routers/projects.py
- app/persistence/pg_repositories.py
- tests/tier1/test_stale_query_filtering.py

## Prohibited Actions
- Do not modify single-document-by-ID retrieval
- Do not change schema
- Do not implement rewind or regeneration logic

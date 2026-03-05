# WS-ROUTE-003: API Prefix Consolidation

## Status: Draft

## Parent: WP-ROUTE-001
## Governing ADR: ADR-056
## Depends On: WS-ROUTE-001
## Parallelizable With: WS-ROUTE-002

## Objective

Move all API routes under the `/api/v1/` prefix. Currently `/work-binder/` routes are mounted at the root level. This consolidation ensures all backend routes live under a single namespace, cleanly separating API from SPA routes.

## Scope

### In Scope

- Move `/work-binder/*` routes to `/api/v1/work-binder/*`
- Update SPA API client to use new prefixes
- Update any other scattered API routes not under `/api/v1/`
- Tier-1 tests

### Out of Scope

- SPA routing changes (WS-ROUTE-002)
- Dead route removal (WS-ROUTE-005)
- Work Binder deep linking (WS-ROUTE-004)
- Changes to route logic (only prefixes change)

## Implementation

### Step 1: Update work_binder router mount

**File:** `app/api/main.py`

Change the work_binder router mount from root to `/api/v1`:

**Before:**
```python
app.include_router(work_binder_router, prefix="/work-binder", tags=["work-binder"])
```

**After:**
```python
app.include_router(work_binder_router, prefix="/api/v1/work-binder", tags=["work-binder"])
```

### Step 2: Audit all router mounts

**File:** `app/api/main.py`

Check every `app.include_router()` call. Any router not under `/api/v1/` (except `/auth/` and SPA fallback) should be moved.

Current expected consolidation:

| Current Mount | New Mount |
|--------------|-----------|
| `/work-binder` | `/api/v1/work-binder` |
| `/api/commands` | `/api/v1/commands` (if exists) |
| `/api/admin` | `/api/v1/admin` (if exists) |

### Step 3: Update SPA API client

**File:** `spa/src/api/client.js`

Update all `/work-binder/` references to `/api/v1/work-binder/`:

```javascript
// Before
getCandidates: (projectId) =>
    request('/work-binder/candidates?project_id=' + projectId),

// After
getCandidates: (projectId) =>
    request('/work-binder/candidates?project_id=' + projectId),
// Note: if API_BASE is already '/api/v1', then the client may already
// prepend this. Check the request() helper function.
```

**Important:** The `request()` helper in `client.js` uses `API_BASE = '/api/v1'`. If work-binder calls already go through `request()`, they would need the path adjusted. If they use a separate base, consolidate.

### Step 4: Verify no hardcoded paths in SPA

Search SPA for any hardcoded `/work-binder/` references outside the API client:

```bash
grep -r "work-binder" spa/src/ --include="*.jsx" --include="*.js"
```

## Tier-1 Tests

- All work_binder route tests use the new `/api/v1/work-binder/` prefix
- SPA API client methods point to consolidated paths
- No references to old `/work-binder/` prefix in production code

## Allowed Paths

```
app/api/main.py
spa/src/api/client.js
tests/tier1/api/test_work_binder_routes.py
```

## Prohibited

- Do not change route handler logic (only prefixes)
- Do not modify work_binder.py route definitions (only the mount point)
- Do not add or remove routes
- Do not modify SPA components (only API client)

## Verification

- `GET /api/v1/work-binder/candidates?project_id=...` works
- `POST /api/v1/work-binder/import-candidates` works
- `POST /api/v1/work-binder/promote` works
- Old `/work-binder/` paths return 404 (not silently redirected)
- SPA build passes
- All tests pass

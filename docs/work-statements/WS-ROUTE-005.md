# WS-ROUTE-005: Dead Route Cleanup + Contract Update

## Status: Draft

## Parent: WP-ROUTE-001
## Governing ADR: ADR-056
## Depends On: WS-ROUTE-004

## Objective

Remove dead routes (story-backlog commands, HTMX view routes) and replace ROUTING_CONTRACT.md v1 with v2 content reflecting the current system.

## Scope

### In Scope

- Remove story-backlog command routes (if they still exist in code)
- Remove HTMX view routes (if they still exist in code)
- Remove deprecated route handlers that serve no traffic
- Update `docs/governance/ROUTING_CONTRACT.md` to v2 (ADR-056 content)
- Run Tier-0 verification

### Out of Scope

- Adding new routes (prior WSs)
- SPA changes (prior WSs)
- API logic changes

## Implementation

### Step 1: Audit dead routes

Search codebase for routes referenced in ROUTING_CONTRACT.md v1 that no longer serve traffic:

```
POST /api/commands/story-backlog/init
POST /api/commands/story-backlog/generate-epic
POST /api/commands/story-backlog/generate-all
GET /view/EpicBacklogView
GET /view/StoryBacklogView
```

For each: verify the route handler exists, verify no SPA or test references, remove if dead.

### Step 2: Remove dead route handlers

If found, remove the route handler functions and their router registrations. Remove associated imports.

### Step 3: Audit HTMX-era view routes

Search for routes that return HTML fragments or full pages via Jinja2 templates that are no longer used now that the SPA handles all rendering:

```
GET /projects/{project_id}/documents/{doc_type_id}  (HTMX HTML response)
```

If these exist and are not called by anything, remove them.

### Step 4: Update ROUTING_CONTRACT.md

**File:** `docs/governance/ROUTING_CONTRACT.md`

Replace the entire v1 content with v2 content derived from ADR-056. The contract should reflect the current system:

- Route categories: SPA, API, Command, Stream, Auth, Static
- SPA route scheme with deep links
- API under `/api/v1/`
- Kebab-case convention
- display_id resolution contract
- Deprecation protocol (kept from v1 — still valid)
- Governance boundary table

Update the frozen date to reflect the new version.

### Step 5: Run Tier-0

```bash
ops/scripts/tier0.sh --frontend
```

## Tier-1 Tests

- Remove any tests for deleted routes
- Verify no test references to dead route paths
- All remaining tests pass

## Allowed Paths

```
app/api/v1/routers/ (route removal only)
app/web/routes/ (route removal only)
app/api/main.py (router mount removal only)
docs/governance/ROUTING_CONTRACT.md
tests/
```

## Prohibited

- Do not add new routes
- Do not modify existing live route logic
- Do not remove routes that are actively used by the SPA
- Do not delete test files (only remove tests for deleted routes)

## Verification

- Dead routes return 404
- All live routes still work
- ROUTING_CONTRACT.md reflects current system
- Tier-0 passes (pytest + lint + typecheck + SPA build)

## Definition of Done

All verification items pass. WP-ROUTE-001 is complete.

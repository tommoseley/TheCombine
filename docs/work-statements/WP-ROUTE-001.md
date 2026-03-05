# WP-ROUTE-001: Unified Routing v2

## Status: Accepted

## Governing ADR

ADR-056 — Unified Routing Contract v2

## Objective

Enable deep linking for all documents and projects. Every artifact gets a bookmarkable, shareable URL. Replace manual SPA routing with declarative client-side routing. Consolidate API prefixes under `/api/v1/`.

## Precondition

WP-ID-001 (Document Identity Standard) MUST be complete before this WP begins. Routing depends on `display_id` and prefix resolution.

## Work Statements

| WS | Title | Depends On | Parallelizable |
|----|-------|------------|----------------|
| WS-ROUTE-001 | Universal Document Resolver Endpoint | WP-ID-001 | No (foundation) |
| WS-ROUTE-002 | SPA Fallback + Client-Side Routing | WS-ROUTE-001 | Yes (with WS-ROUTE-003) |
| WS-ROUTE-003 | API Prefix Consolidation | WS-ROUTE-001 | Yes (with WS-ROUTE-002) |
| WS-ROUTE-004 | Work Binder Deep Linking | WS-ROUTE-002, WS-ROUTE-003 | No |
| WS-ROUTE-005 | Dead Route Cleanup + Contract Update | WS-ROUTE-004 | No |

## Dependency Chain

```
WP-ID-001 → WS-ROUTE-001 → WS-ROUTE-002 ─┐
                              └→ WS-ROUTE-003 ─┤→ WS-ROUTE-004 → WS-ROUTE-005
```

WS-ROUTE-002 and WS-ROUTE-003 can run in parallel (non-overlapping: SPA vs backend).

## Definition of Done

- `GET /api/v1/projects/{project_id}/documents/{display_id}` resolves any document
- SPA uses declarative routing with cold-load deep link support
- All API routes consolidated under `/api/v1/`
- Work Binder supports deep linking (both WP and WS display_ids)
- Dead routes removed (story-backlog, HTMX view routes)
- ROUTING_CONTRACT.md updated to v2
- All tests pass, SPA builds clean

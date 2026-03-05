# ADR-056 -- Unified Routing Contract v2

**Status:** Accepted
**Date:** 2026-03-04
**Related:** ADR-055, ROUTING_CONTRACT.md (v1, superseded)

---

## Context

The existing Routing Contract (v1.0, frozen 2026-01-12) was written during the HTMX era. The system has since migrated to a React SPA. The contract is now stale:

1. **VIEW routes assume HTMX.** `GET /projects/{project_id}/documents/{doc_type_id}` returns "HTML (full page or HTMX partial)." The SPA does not use these.

2. **Dead routes still listed.** `story-backlog/init`, `story-backlog/generate-epic`, `story-backlog/generate-all` — these document types no longer exist.

3. **No SPA route category.** The contract has no concept of client-side routes or deep linking.

4. **~270 API routes with no unifying scheme.** Routes accumulated organically: `/api/v1/projects/...`, `/api/commands/...`, `/work-binder/...`, `/api/admin/...`.

5. **No deep linking.** The SPA has 4 top-level routes (`/`, `/learn`, `/admin`, `/admin/workbench`). Selecting a project, document, or work package does not change the URL. Nothing is bookmarkable or shareable.

6. **Inconsistent path casing.** Some routes use underscores (`/doc_type_id`), others use hyphens (`/import-candidates`). No standard.

With ADR-055 establishing `display_id` as the universal document identity, we can now build a routing scheme around it.

---

## Decision

### 1. Route Categories (v2)

| Category | Pattern | Response | Owner |
|----------|---------|----------|-------|
| **SPA** | `/{path}` | `index.html` (client-side routing) | SPA |
| **API** | `/api/v1/{domain}/{resource}` | JSON | Backend |
| **Command** | `/api/v1/commands/{domain}/{action}` | JSON (task_id) | Backend |
| **Stream** | `/api/v1/commands/{domain}/{action}/stream` | SSE | Backend |
| **Auth** | `/auth/{action}` | Redirect / JSON | Backend |
| **Static** | `/assets/{file}` | File | Vite build |

The legacy VIEW category (HTMX HTML responses) is **retired**. All user-facing rendering goes through the SPA.

### 2. SPA Route Scheme

The SPA owns all routes not prefixed with `/api/`, `/auth/`, or `/assets/`. The server returns `index.html` for any unmatched route (SPA fallback).

#### Core SPA Routes

```
/                                       → Lobby (project selector)
/projects/{project_id}                → Project dashboard
/projects/{project_id}/docs/{display_id}  → Document viewer
/projects/{project_id}/work-binder    → Work Binder
/projects/{project_id}/work-binder/{display_id}  → WB focused on document
/projects/{project_id}/production     → Production floor
/admin                                  → Admin panel
/admin/workbench                        → Admin workbench
/learn                                  → Learn page
```

#### Deep Link Examples

| URL | What It Opens |
|-----|---------------|
| `/projects/HWCA-001/docs/PD-001` | Project Discovery for Hello World |
| `/projects/HWCA-001/docs/TA-001` | Technical Architecture |
| `/projects/HWCA-001/docs/WS-003` | Work Statement (flat document view) |
| `/projects/HWCA-001/work-binder/WP-001` | Work Binder focused on WP-001 |
| `/projects/HWCA-001/work-binder/WS-003` | Work Binder → resolves to parent WP, WS-003 expanded |
| `/projects/APAM-002/docs/IP-001` | Implementation Plan for APAM |

#### Cold-Load Support

When a user navigates directly to a deep link (bookmark, shared URL):

1. Server returns `index.html` (SPA fallback)
2. SPA reads `window.location.pathname`
3. SPA parses route → resolves `project_id` → fetches project → renders correct view
4. If project or document not found → 404 page within SPA

### 3. API Route Consolidation

All API routes live under `/api/v1/`. Current scattered prefixes are consolidated:

| Current | Consolidated |
|---------|-------------|
| `/work-binder/...` | `/api/v1/work-binder/...` |
| `/api/commands/...` | `/api/v1/commands/...` |
| `/api/admin/...` | `/api/v1/admin/...` |
| `/api/v1/projects/...` | _(unchanged)_ |

### 4. Path Segment Conventions

- **URL paths:** kebab-case (`/work-binder`, `/import-candidates`, `/propose-ws`)
- **Path parameters:** snake_case when matching Python/DB identifiers (`{project_id}`, `{display_id}`)
- **JSON fields:** snake_case (unchanged)
- **Query parameters:** snake_case (unchanged)

### 5. Project Identifier in URLs

The existing `project_id` field (defined in ADR-055, section 9) serves as the human-readable project identifier in URLs. It already follows `{PREFIX}-{NNN}` format (e.g., `HWCA-001`), is unique, and is human-readable. URLs use `{project_id}` instead of UUIDs. No schema change needed.

`project_id` is the human-readable project identifier string (e.g., `HWCA-001`); the internal UUID primary key is `project.id`.

### 6. display_id Resolution in URLs

Routes containing `{display_id}` are resolved using the prefix resolution contract defined in ADR-055, section 11:

1. Parse `display_id` from URL path (e.g., `WP-001`)
2. Split on last hyphen → prefix `WP`, number `001`
3. Look up `WP` in `document_types.display_prefix` → `doc_type_id = "work_package"`
4. Query `documents` by `(space_id, doc_type_id, display_id = "WP-001")`
5. If not found → 404

This applies to both SPA deep linking (client fetches via API) and direct API calls.

### 7. SPA Client-Side Routing

The SPA SHALL implement declarative client-side routing with cold-load support. This replaces the current manual `window.location.pathname` matching.

Requirements:
- Declarative route definitions with URL parameter extraction
- Nested layouts
- Programmatic navigation
- Browser history integration (back/forward)

The specific routing library is an implementation choice for the Work Statement, not an architectural decision.

### 8. Server-Side SPA Fallback

The FastAPI server SHALL return `index.html` for any GET request whose path does not match `/api/`, `/auth/`, `/health`, or `/assets/` prefixes.

No `Accept` header inspection. API routes are disambiguated by prefix, not by content negotiation. This enables cold-load deep linking.

### 9. Universal Document Resolver Endpoint

A single API endpoint resolves any document by project_id and display_id:

```
GET /api/v1/projects/{project_id}/documents/{display_id}
```

Response: the document's JSON representation (content, metadata, version, status).

This endpoint is the backend half of deep linking. It can be built before any SPA routing changes, enabling incremental adoption. The SPA's deep link handler calls this endpoint to load document data on cold-load navigation.

### 10. Work Binder Deep Linking

The `/work-binder/{display_id}` route accepts both WP and WS display_ids:

- `/projects/HWCA-001/work-binder/WP-001` — opens Work Binder with WP-001 selected
- `/projects/HWCA-001/work-binder/WS-003` — WB resolves WS-003 → finds parent WP via `parent_document_id` → opens WB with that WP selected and WS-003 expanded

No hierarchy encoding in the URL. The Work Binder resolves context from the document type. This is simpler than nested paths like `/work-binder/WP-001/WS-003` and avoids breakage if a WS is ever reparented.

For flat document viewing (outside WB context), WSs are also addressable via `/projects/HWCA-001/docs/WS-003`.

### 11. Canonical Command Routes (Updated)

| Route | Purpose |
|-------|---------|
| `POST /api/v1/commands/documents/{doc_type_id}/build` | Build any document |
| `POST /api/v1/commands/documents/{doc_type_id}/mark-stale` | Mark document stale |

The `story-backlog/*` command routes are **removed** (document types no longer exist).

### 12. Deprecation of v1 Routes

All routes from ROUTING_CONTRACT.md v1 that are not carried forward here are deprecated. Since there is no production traffic, they can be removed without the deprecation monitoring period.

---

## Consequences

### Positive

- **Every artifact is linkable.** `/projects/HWCA-001/docs/WP-001` opens exactly that document.
- **Shareable URLs.** Operators can paste links in chat, docs, or work statements.
- **Browser navigation works.** Back/forward buttons navigate between documents.
- **Bookmarks work.** Save `/projects/APAM-002/work-binder` to get back to the work binder.
- **Clean API surface.** All backend routes under `/api/v1/`, all client routes owned by SPA.
- **Consistent casing.** Kebab-case in URLs, snake_case in data.

### Negative

- **Client-side routing library dependency.** The SPA will need a routing library. Implementation choice deferred to WS.
- **Server fallback route.** Must be configured carefully to not swallow API 404s.
- **Project identifier schema change.** Covered by ADR-055 (identity standard).

---

## Implementation Sequence

1. **ADR-055 first** — display_id, project_id, and prefix resolution must exist before routing can reference them.
2. **Universal document resolver** — `GET /api/v1/projects/{project_id}/documents/{display_id}`. This is the backend guardrail: once it works, SPA deep links can be implemented incrementally.
3. **Add SPA fallback** — FastAPI catch-all returns `index.html` for non-API routes.
4. **Refactor SPA routing** — replace manual pathname matching with declarative client-side routing.
5. **Consolidate API prefixes** — move `/work-binder/` under `/api/v1/`.
6. **Remove dead routes** — story-backlog commands, HTMX view routes.
7. **Update ROUTING_CONTRACT.md** — replace v1 with v2 content.

---

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add new SPA route | No |
| Add new API route under `/api/v1/` | No |
| Change URL path convention | Yes |
| Change project_id format | Yes (ADR-055) |
| Remove existing API route | No (if unused) |
| Add new route category | Yes |

---

_Draft: 2026-03-04_

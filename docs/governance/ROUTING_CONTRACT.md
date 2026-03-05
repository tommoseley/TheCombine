# Routing Contract v2.0

> **Supersedes**: v1.0 (2026-01-12). Updated per ADR-056 (Unified Routing v2).

## Philosophy

Routes are the API contract. The SPA owns all user-facing paths; the server owns API, auth, and static asset paths. Every document is addressable by URL via display_id (ADR-055).

## Route Categories

### SPA Routes (Client-Side)

**Pattern**: `/{path}` (any path not matching API, auth, or static)

All user-facing routes are handled by React Router. The server returns `index.html` for any unmatched path (catch-all fallback).

| Route | Purpose |
|-------|---------|
| `/` | Home / project list |
| `/learn` | Learn page (unauthenticated) |
| `/projects/{project_slug}` | Project dashboard |
| `/projects/{project_slug}/docs/{display_id}` | Document deep link |
| `/projects/{project_slug}/work-binder` | Work Binder |
| `/projects/{project_slug}/work-binder/{display_id}` | Work Binder deep link (WP/WS/WPC) |
| `/projects/{project_slug}/production` | Production view |
| `/admin` | Admin panel |
| `/admin/workbench` | Admin workbench |
| `/admin/executions/{execution_id}` | Execution detail |

**Path conventions**: kebab-case in URL segments, snake_case in parameters.
**Project slug**: Uses `project_id` field (e.g., `HWCA-001`).

### API Routes (Server-Side)

**Pattern**: `/api/v1/{domain}/{resource}`

All API endpoints live under `/api/v1/`. The SPA client prepends this prefix automatically.

| Route Pattern | Domain | Purpose |
|---------------|--------|---------|
| `/api/v1/projects/*` | Projects | CRUD, tree, workflow, documents |
| `/api/v1/projects/{id}/documents/{identifier}` | Documents | By doc_type_id or display_id |
| `/api/v1/work-binder/*` | Work Binder | WP/WS/WPC operations |
| `/api/v1/production/*` | Production | Status, start, SSE events |
| `/api/v1/executions/*` | Executions | Monitoring, transcripts |
| `/api/v1/workflows/*` | Workflows | Definitions, management |
| `/api/v1/intake/*` | Intake | Concierge intake flow |
| `/api/v1/intents/*` | Intents | Intent intake |
| `/api/v1/interrupts/*` | Interrupts | Operator interrupt resolution |

### Command Routes

**Pattern**: `/api/commands/{domain}/{action}`

Legacy command namespace. Story-backlog commands were planned but never implemented and are now formally retired.

### SSE Routes (Streaming)

| Route | Purpose |
|-------|---------|
| `/api/v1/production/events?project_id={id}` | Production line events |
| `/api/v1/intake/{execution_id}/events` | Intake generation events |

### Auth Routes

| Route | Purpose |
|-------|---------|
| `/auth/login/{provider}` | OAuth login redirect |
| `/auth/logout` | Logout |
| `/api/me` | Current user info |

### Static Routes

| Route | Purpose |
|-------|---------|
| `/assets/*` | SPA JS/CSS bundles (Vite build output) |
| `/content/*` | SPA content files (YAML/JSON config) |
| `/web/*` | Legacy web assets |

## Display ID Resolution (ADR-055)

The universal document resolver at `/api/v1/projects/{project_id}/documents/{identifier}` accepts both:

- **doc_type_id** (e.g., `project_discovery`) — traditional lookup
- **display_id** (e.g., `PD-001`) — ADR-055 prefix resolution

Display IDs match pattern `[A-Z]{2,4}-\d{3,}`. The prefix maps to `document_types.display_prefix` in the registry.

## SPA Deep Linking

Direct navigation to any SPA route works via:
1. Server catch-all returns `index.html` for non-API/auth/asset paths
2. React Router resolves the route client-side
3. Components read URL params via `useParams()`

Work Binder deep linking resolves display_id prefix:
- `WP-*` → Select work package directly
- `WS-*` → Fetch document, find parent WP, select parent
- `WPC-*` → Select candidate

## Retired Routes

The following routes from v1.0 are formally retired:

| Route | Status | Notes |
|-------|--------|-------|
| `POST /api/commands/story-backlog/init` | Never implemented | Story-backlog retired (WS-REGISTRY-002) |
| `POST /api/commands/story-backlog/generate-epic` | Never implemented | Story-backlog retired |
| `POST /api/commands/story-backlog/generate-all` | Never implemented | Story-backlog retired |
| `GET /view/EpicBacklogView` | Never existed | Listed in v1.0 deprecated registry |
| `GET /view/StoryBacklogView` | Never existed | Listed in v1.0 deprecated registry |
| HTMX partial routes | Superseded by SPA | React SPA handles all rendering |

## Deprecation Protocol

Same as v1.0:
1. Mark `deprecated=True` in FastAPI decorator
2. Emit `Warning` and `Deprecation` headers
3. Log usage
4. Monitor, then remove after zero hits

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add new API route under `/api/v1/` | No |
| Add new SPA route | No |
| Deprecate existing route | No |
| Remove deprecated route (after monitoring) | No |
| Change API namespace pattern | Yes |
| Change display_id resolution logic | Yes |
| Modify catch-all fallback behavior | Yes |

---

_Updated: 2026-03-04 (WP-ROUTE-001, ADR-056)_
_Supersedes: v1.0 (2026-01-12)_

# Routing Contract v1.0

> **Frozen**: Standardizes URL construction and retirement.

## Philosophy

Routes are the API contract. Changing routes without deprecation warnings breaks clients. All commands live under a predictable namespace.

## Route Categories

### VIEW Routes (Read-Only)

**Pattern**: `GET /projects/{project_id}/documents/{doc_type_id}`

- Response: HTML (full page or HTMX partial)
- Data Flow: `documents` table → `RenderModelBuilder` → `RenderModelV1` → Fragments
- Caching: Allowed

### COMMAND Routes (Mutating)

**Pattern**: `POST /api/commands/{domain}/{action}`

- Response: JSON with `task_id`
- Properties: Async, idempotent, mutate documents not views
- Caching: Never

### Canonical Command Routes

| Route | Purpose |
|-------|---------|
| `POST /api/commands/documents/{doc_type_id}/build` | Build any document |
| `POST /api/commands/documents/{doc_type_id}/mark-stale` | Mark document stale |
| `POST /api/commands/story-backlog/init` | Initialize story backlog |
| `POST /api/commands/story-backlog/generate-epic` | Generate stories for epic |
| `POST /api/commands/story-backlog/generate-all` | Generate all stories |

### SSE Routes (Streaming)

**Pattern**: `POST /api/commands/{domain}/{action}/stream`

- Response: `text/event-stream`
- Headers: `Cache-Control: no-cache`, `Connection: keep-alive`

## Deprecation Protocol

### Step 1: Mark Deprecated

```python
@router.post("/old/route", deprecated=True)
async def old_route(...):
    ...
```

### Step 2: Add Warning Header

All deprecated routes MUST emit:

```http
Warning: 299 - "Deprecated: Use POST /api/commands/documents/{doc_type_id}/build"
Deprecation: true
```

### Step 3: Log Usage

```python
logger.warning(f"DEPRECATED_ROUTE_HIT: {path} - Use {canonical_path} instead")
```

### Step 4: Monitor & Remove

- Monitor deprecated route usage for 2+ weeks
- Remove only after zero hits
- Never silent removal

## Deprecated Routes Registry

| Old Route | New Route | Status |
|-----------|-----------|--------|
| `/api/documents/build/{type}` | `/api/commands/documents/{type}/build` | Deprecated |
| `/api/documents/{id}/mark-stale` | `/api/commands/documents/{type}/mark-stale` | Deprecated |
| `/view/EpicBacklogView` | `/projects/{id}/documents/epic_backlog` | Deprecated |
| `/view/StoryBacklogView` | `/projects/{id}/documents/story_backlog` | Deprecated |

## Command Response Contract

All command routes return:

```json
{
  "status": "completed|queued|error",
  "task_id": "uuid",
  "doc_type_id": "string",
  "document_id": "uuid|null",
  "message": "string|null"
}
```

## Invariants

1. **All commands return task_id** - For async tracking
2. **Commands are idempotent** - Safe to retry
3. **Commands mutate documents, not views** - Separation of concerns
4. **Deprecated routes emit Warning header** - RFC 7234 compliance
5. **No silent route removal** - Always deprecate first

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add new command route | No |
| Deprecate existing route | No |
| Remove deprecated route (after monitoring) | No |
| Change route namespace pattern | Yes |
| Change command response schema | Yes |

---

_Frozen: 2026-01-12 (WS-DOCUMENT-SYSTEM-CLEANUP Phase 5, 7)_
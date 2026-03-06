# WS-RENDER-002: Project Binder Render (Markdown)

## Status: Accepted

## Governing References

- ADR-054 -- Governed Information Architecture with HTML and PDF Targets
- WS-RENDER-001 -- Single Document Render (dependency)
- ROUTING_CONTRACT v2.0

---

## Objective

Generate a single project binder Markdown file that concatenates all project documents in deterministic pipeline order. The binder includes a cover block, table of contents, and each document rendered via WS-RENDER-001's block renderer.

---

## Non-Goals

- IA verification gate (WS-RENDER-003)
- Evidence/provenance mode (WS-RENDER-004)
- PDF generation
- Persisting rendered output
- Per-document rendering (already done in WS-RENDER-001)

---

## Prerequisites / Dependencies

- WS-RENDER-001 complete (single document markdown renderer exists)
- Pipeline ordering is knowable from production status or document type configuration
- Work Binder WP/WS documents are queryable by project

---

## Implementation Tasks

### 1) Backend: Binder assembly service

**Create:** `app/domain/services/binder_renderer.py`

**Binder structure:**

```markdown
# {project_id} — {project_title}

> Generated: {ISO timestamp}
> Renderer: render-md@1.0.0

---

## Table of Contents

- [CI-001 — Concierge Intake](#ci-001)
- [PD-001 — Project Discovery](#pd-001)
- [IP-001 — Implementation Plan](#ip-001)
- [TA-001 — Technical Architecture](#ta-001)
- [WP-001 — Work Package Title](#wp-001)
  - [WS-001 — Work Statement Title](#ws-001)
  - [WS-002 — Work Statement Title](#ws-002)

---

# CI-001 — Concierge Intake
{rendered markdown from WS-RENDER-001 renderer}

---

# PD-001 — Project Discovery
{rendered markdown}
...
```

**Ordering rules (deterministic):**

1. Pipeline order for document types:
   - `concierge_intake`
   - `project_discovery`
   - `implementation_plan`
   - `technical_architecture`
   - `work_package`

2. Within a document type: `display_id` ascending

3. Work Binder specifics:
   - WPs by `display_id` ascending
   - WSs within each WP by `ws_index` order (NOT display_id order)
   - Each WS renders as a subsection under its parent WP

**Cover block fields:**
- `project_id`
- `project_title` (if available)
- `generated_at` (ISO 8601)
- `renderer_version` (`render-md@1.0.0`)
- `document_count` (total documents included)
- `production_line_state` (active/complete/idle — if available from production status)

### 2) Backend: Binder render endpoint

**File:** `app/api/v1/routers/projects.py`

**Route:**
```
GET /api/v1/projects/{project_id}/render
```

**Query params:**
- `scope` — `project` (required; reject other values with 400)
- `profile` — `standard` | `print` (default `print`)
- `format` — `md` (fixed; reject other values with 400)

**Endpoint logic:**
1. Resolve `{project_id}` to a project
2. Query all documents for the project
3. Sort by pipeline order, then display_id (WS by ws_index within WP)
4. Render each document using the markdown block renderer from WS-RENDER-001
5. Assemble binder: cover + TOC + rendered documents with separators
6. Return as attachment

**Response:**
- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="{project_id}-binder.md"`

**Error cases:**
- Project not found: 404
- `scope` not `project`: 400
- `format` not `md`: 400
- No documents found: return binder with cover only + "No documents produced yet" note

### 3) SPA: Download binder button

**Files:**
- `spa/src/api/client.js`
- `spa/src/components/Floor.jsx` (breadcrumb bar — add download button near theme toggle)

**API client:**
```javascript
renderProjectBinder: (projectId, profile = 'print') =>
    fetch(`${BASE}/projects/${projectId}/render?scope=project&format=md&profile=${profile}`)
        .then(r => r.blob()),
```

**UI behavior:**
- Add a download icon button in the `PipelineBreadcrumb` bar (near the theme toggle, right side)
- On click: fetch blob, trigger browser download
- Tooltip: "Download Project Binder (Markdown)"

---

## Tier-1 Tests

**File:** `tests/tier1/services/test_binder_renderer.py`

- Empty project produces cover-only binder
- Single document renders with cover + TOC + document section
- Multiple documents appear in pipeline order
- WPs sort by display_id ascending
- WSs within a WP sort by ws_index, not display_id
- TOC entries match document sections
- Cover block includes project_id and generated_at
- Output is deterministic (same input = same output)

**File:** `tests/tier1/api/test_binder_routes.py`

- GET with valid project_id returns 200 with `text/markdown` content type
- GET with invalid scope param returns 400
- GET with invalid format param returns 400
- GET with nonexistent project_id returns 404
- Response includes `Content-Disposition` header with correct filename
- No DB mutations occur

---

## Acceptance Criteria

- Binder downloads as a single `.md` file
- Documents appear in deterministic pipeline order
- Work Binder WS ordering uses `ws_index`, not display_id order
- Cover block includes project identity and generation timestamp
- TOC has anchor links to each document section
- No DB mutations occur
- SPA shows download button in breadcrumb bar
- Tier-1 tests pass; SPA builds clean

---

## Allowed Paths

**Backend:**
- `app/domain/services/binder_renderer.py` (new)
- `app/api/v1/routers/projects.py`
- `tests/tier1/services/test_binder_renderer.py` (new)
- `tests/tier1/api/test_binder_routes.py` (new)

**Frontend:**
- `spa/src/api/client.js`
- `spa/src/components/Floor.jsx`

---

## Prohibited Actions

- Persisting rendered output to the database
- Introducing new document types or schema changes
- Modifying the single-document renderer (WS-RENDER-001) behavior
- Adding new npm dependencies
- Inferring WS order from display_id (must use ws_index)

---

## Verification Steps

**Backend:**
- `python -m pytest tests/tier1/services/test_binder_renderer.py -v`
- `python -m pytest tests/tier1/api/test_binder_routes.py -v`

**Frontend:**
- `cd spa && npm run build`

**Integration (manual):**
- GET `/api/v1/projects/{id}/render?scope=project&format=md` returns valid Markdown binder
- Documents appear in correct order
- WSs within WPs follow ws_index order

**Tier 0:**
- `ops/scripts/tier0.sh --frontend`

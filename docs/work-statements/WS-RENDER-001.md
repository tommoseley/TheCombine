# WS-RENDER-001: Single Document Render (Markdown)

## Status: Accepted

## Governing References

- ADR-054 -- Governed Information Architecture with HTML and PDF Targets
- ROUTING_CONTRACT v2.0

---

## Objective

Provide an on-demand renderer that converts a canonical Combine document (JSON content + governed IA definitions) into presentation-grade Markdown for download, share, or print. Output is deterministic and regenerable; nothing is persisted.

---

## Non-Goals

- Project binder assembly (WS-RENDER-002)
- IA verification gate (WS-RENDER-003)
- Evidence/provenance mode (WS-RENDER-004)
- PDF generation
- Persisting rendered output

---

## Prerequisites / Dependencies

- IA block rendering model exists for document types (ADR-054, WS-IA-001 through WS-IA-003)
- Document content retrievable via existing `DocumentRepository`
- IA `render_as` vocabulary is stable (`paragraph`, `list`, `ordered-list`, `table`, `key-value-pairs`, `card-list`, `nested-object`)

---

## Implementation Tasks

### 1) Backend: Markdown block renderer

**Create:** `app/domain/services/markdown_renderer.py`

Build a renderer that maps IA block types to Markdown:

| `render_as` | Markdown Output |
|-------------|-----------------|
| `paragraph` | Plain text block |
| `list` | `- item` per entry |
| `ordered-list` | `1. item` per entry |
| `table` | GFM table with `columns` headers |
| `key-value-pairs` | `**Key:** value` per entry |
| `card-list` | `### {title}` + sub-fields per card |
| `nested-object` | `#### {field_label}` + recursive rendering |

**Input:** Document content (dict) + IA section definitions (from package.yaml)

**Output:** Markdown string

**Design decisions:**
- Reuse existing IA bind definitions from `combine-config` package.yaml — no new config authoring
- Sections render in IA-declared order
- Section labels become `## {label}` headers
- Fields without IA binds are omitted (governed output only)

### 2) Backend: Render endpoint

**File:** `app/api/v1/routers/projects.py`

**Route:**
```
GET /api/v1/projects/{project_id}/documents/{display_id}/render
```

**Query params:**
- `profile` — `standard` | `print` (default `standard`; `print` omits metadata preamble)
- `format` — `md` (fixed; reject other values with 400)

**Endpoint logic:**
1. Resolve `{project_id, display_id}` to a document row
2. Load canonical content (JSON body)
3. Load IA definitions for the document's `doc_type_id` from package.yaml
4. Render to Markdown using the block renderer
5. Return as attachment

**Response:**
- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="{project_id}-{display_id}.md"`

**Error cases:**
- Document not found: 404
- `format` not `md`: 400
- Document type has no IA definitions: render with fallback (section headers + raw field values)

### 3) SPA: Download button

**Files:**
- `spa/src/api/client.js`
- `spa/src/components/FullDocumentViewer.jsx`

**API client:**
```javascript
renderDocument: (projectId, displayId, profile = 'standard') =>
    fetch(`${BASE}/projects/${projectId}/documents/${displayId}/render?format=md&profile=${profile}`)
        .then(r => r.blob()),
```

**UI behavior:**
- Add "Download Markdown" button in `DocumentHeader` (visible when document is stabilized)
- On click: fetch blob, trigger browser download with correct filename
- No layout changes required

---

## Tier-1 Tests

**File:** `tests/tier1/services/test_markdown_renderer.py`

- Paragraph field renders as plain text
- List field renders as `- item` bullets
- Ordered list renders as `1. item` numbered items
- Table field renders as GFM table with column headers
- Key-value pairs render as `**Key:** value`
- Card-list renders with `###` sub-headers
- Nested-object renders with recursive field labels
- Missing content field is silently omitted
- Section ordering matches IA declaration order
- Output is deterministic (same input = same output)

**File:** `tests/tier1/api/test_render_routes.py`

- GET with valid display_id returns 200 with `text/markdown` content type
- GET with invalid format param returns 400
- GET with nonexistent display_id returns 404
- Response includes `Content-Disposition` header with correct filename
- No DB mutations occur (verify no write calls)

---

## Acceptance Criteria

- Rendering a stabilized document returns valid Markdown
- Filename matches `{project_id}-{display_id}.md`
- Output is deterministic for same inputs
- All IA `render_as` block types produce correct Markdown
- No DB mutations occur
- SPA shows "Download Markdown" button on stabilized documents
- Tier-1 tests pass; SPA builds clean

---

## Allowed Paths

**Backend:**
- `app/domain/services/markdown_renderer.py` (new)
- `app/api/v1/routers/projects.py`
- `tests/tier1/services/test_markdown_renderer.py` (new)
- `tests/tier1/api/test_render_routes.py` (new)

**Frontend:**
- `spa/src/api/client.js`
- `spa/src/components/FullDocumentViewer.jsx`

**Config (read-only):**
- `combine-config/document_types/*/releases/*/package.yaml` (read IA definitions)

---

## Prohibited Actions

- Persisting rendered output to the database
- Introducing new document types or schema changes
- Modifying IA definitions or package.yaml
- Adding new npm dependencies
- Creating a new templating system (reuse IA block definitions)

---

## Verification Steps

**Backend:**
- `python -m pytest tests/tier1/services/test_markdown_renderer.py -v`
- `python -m pytest tests/tier1/api/test_render_routes.py -v`

**Frontend:**
- `cd spa && npm run build`

**Integration (manual):**
- GET `/api/v1/projects/{id}/documents/{display_id}/render?format=md` returns valid Markdown
- Downloaded file opens correctly in any Markdown viewer

**Tier 0:**
- `ops/scripts/tier0.sh --frontend`

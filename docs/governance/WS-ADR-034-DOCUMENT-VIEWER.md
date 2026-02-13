# WS-ADR-034-DOCUMENT-VIEWER

**Status:** Draft  
**Created:** 2026-01-09

---

## Goal

Implement the DocumentViewer contract v1.0 end-to-end: the server emits `RenderModelV1` with nested sections and envelope fields, and the UI renders any document type using canonical component bindings and fragment resolution.

---

## Scope Constraints (Non-Negotiable)

| Constraint | Rule |
|------------|------|
| ❌ | No new block shapes |
| ❌ | No new docdef fields/semantics |
| ❌ | No PromptAssembler changes |
| ❌ | No client-side (React) rendering in this WS |
| ❌ | No document-type-specific templates |
| ✅ | RenderModelBuilder updated to emit contract structure |
| ✅ | DocumentViewer routes + rendering (Jinja2/HTMX) |
| ✅ | Golden-trace tests + regression tests |
| ✅ | Governance docs frozen |

---

## Deliverables

### 1) Contract-Aligned RenderModel Output

Update `RenderModelBuilder` to emit:

| Field | Value |
|-------|-------|
| `render_model_version` | `"1.0"` |
| `schema_id` | `"schema:RenderModelV1"` |
| `schema_bundle_sha256` | Computed from schema bundle |
| `document_id` | Per frozen strategy (UUID or hash) |
| `document_type` | Short name (e.g., `EpicDetailView`) |
| `title` | Document title |
| `sections[]` | Nested structure with `section_id`, `title`, `order`, `blocks[]` |
| `metadata.section_count` | Number of sections evaluated |

**Key change:** Blocks are nested under `sections[].blocks[]`, not flat.

---

### 2) Viewer Routes + Resolution

**Canonical routes:**

| Route | Purpose |
|-------|---------|
| `GET /view/{document_type}?<params>` | Render stored document |
| `POST /view/{document_type}/preview` | Render preview from request body |

**Document type resolution:**
- `document_type` (short name) → latest accepted `docdef:{document_type}:*`

**Legacy routes:**
- Existing routes at `/projects/{project_id}/documents/{doc_type_id}` are marked **deprecated**
- They remain functional but log deprecation warnings
- Removal scheduled for future WS

---

### 3) Fragment Resolution + Rendering

Viewer renders blocks by:

```
block.type → component (by schema_id) → view_bindings.web.fragment_id → fragment markup
```

**Graceful degradation placeholders:**

| Failure | Placeholder |
|---------|-------------|
| Component not found | "Unsupported block: {block.type}" |
| No web binding | "No web fragment binding: {component_id}" |
| Fragment not found | "Fragment not found: {fragment_id}" |
| Fragment render error | "Fragment render error: {fragment_id}" |

No failure crashes the page.

---

### 4) Golden Trace Coverage

Golden-trace tests must validate contract + rendering for:

| DocDef | Version |
|--------|---------|
| ProjectDiscovery | 1.0.0 |
| EpicSummaryView | 1.0.0 |
| EpicDetailView | 1.0.0 |
| EpicBacklogView | 1.0.0 |
| EpicArchitectureView | 1.0.0 |
| ArchitecturalSummaryView | 1.0.0 |
| StorySummaryView | 1.0.0 |
| StoryDetailView | 1.0.0 |
| StoryBacklogView | 1.0.0 |

**Each test validates:**
- HTTP 200 response
- Expected section headers present
- Expected block count (or placeholders)
- No unhandled exceptions

---

### 5) Governance Docs

| Document | Status |
|----------|--------|
| `DOCUMENT_VIEWER_CONTRACT.md` | Frozen (this contract) |
| `VIEWER_ROUTES_AND_RESOLUTION.md` | New: route patterns, docdef resolution, document_id strategy |

**Reference existing procedures:**
- `PROCEDURE_ADD_COMPONENT.md` (schema → component → fragment → tests)
- `PROCEDURE_ADD_DOCUMENT.md` (docdef → render checks → golden traces)

---

## Acceptance Criteria

| Criterion | Required |
|-----------|----------|
| RenderModelBuilder emits nested `sections[]` | ✅ |
| All required envelope fields present | ✅ |
| Viewer renders all golden-trace docs with no 500s | ✅ |
| Unknown/missing bindings degrade gracefully | ✅ |
| `detail_ref` links resolve with frozen URL rule | ✅ |
| Preview mode works without persistence | ✅ |
| No HTML in JSON payloads | ✅ |
| Test suite passes | ✅ |

---

## Failure Conditions (Automatic ❌ Reject)

| Condition | Reason |
|-----------|--------|
| Flat blocks returned (no `sections[]`) | Contract violation |
| Missing `schema_bundle_sha256` or `schema_id` | Contract violation |
| Any HTML appears in RenderModel JSON | Security violation |
| Non-deterministic `document_id` (same input → different id) | Contract violation |
| Viewer hardcodes doc types or per-doc templates | Generic viewer mandate violated |
| Viewer crashes on missing bindings | Graceful degradation required |
| Legacy routes removed (not just deprecated) | Scope creep |

---

## Out of Scope

- Client-side rendering migration (React components)
- New fragment/component types beyond contract requirements
- Changes to PromptAssembler
- Changes to docdef semantics or shapes
- `RenderActionV1` implementation
- Explicit version selection in URLs
- Legacy route removal (deferred to future WS)

---

## Implementation Notes

### Technology Stack (Unchanged)

- Jinja2 templates for HTML rendering
- HTMX for interactivity
- Tailwind CSS for styling
- Server-side fragment rendering

### Viewer Template Structure

```
templates/
  public/
    document_viewer.html          # Generic viewer (one template)
    partials/
      _section.html               # Section wrapper
      _block_renderer.html        # Dispatches to fragment
      _unknown_block.html         # Fallback placeholder
```

### Fragment Rendering Flow

```
1. Route receives request
2. Resolve docdef by document_type
3. Load document data (stored or preview)
4. Build RenderModelV1 via RenderModelBuilder
5. For each section:
   - Render section header
   - For each block:
     - Resolve component by block.type
     - Resolve fragment by component.view_bindings.web.fragment_id
     - Render fragment with block context
     - On failure: render placeholder
6. Return complete HTML page
```

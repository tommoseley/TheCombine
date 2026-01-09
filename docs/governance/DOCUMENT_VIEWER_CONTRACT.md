# DocumentViewer Contract v1.0

**Status:** Frozen  
**Effective:** 2026-01-09  
**WS:** WS-ADR-034-DOCUMENT-VIEWER

---

## Purpose

Provide a single, generic viewer that can display any Combine document by rendering a `RenderModelV1` envelope into the web UI using canonical components and fragment bindings.

---

## Non-Negotiables

1. **No HTML in JSON payloads.** `RenderModelV1` is data-only; HTML is produced by server-side fragment rendering.
2. **Deterministic rendering.** Given identical inputs (docdef + document data + schema bundle), output must be stable.
3. **Graceful degradation.** Unknown block types, missing fragments, and missing optional fields must not crash rendering.
4. **Frozen URL rule.** `detail_ref` navigation uses `/view/{document_type}?{params}`.

---

## Inputs

### RenderModelV1 Envelope (Canonical)

The DocumentViewer renders a `RenderModelV1` JSON envelope:

```json
{
  "render_model_version": "1.0",
  "schema_id": "schema:RenderModelV1",
  "schema_bundle_sha256": "sha256:<64hex>",
  "document_id": "<string>",
  "document_type": "<string>",
  "title": "<string>",
  "subtitle": "<string|null>",
  "sections": [
    {
      "section_id": "<string>",
      "title": "<string>",
      "order": 0,
      "description": "<string|null>",
      "blocks": [
        {
          "type": "schema:<BlockSchemaId>",
          "key": "<section_id>:<index>",
          "data": { },
          "context": { }
        }
      ]
    }
  ],
  "metadata": {
    "section_count": 0
  }
}
```

### Frozen Clarifications

| Field | Rule |
|-------|------|
| `schema_id` | Always `schema:RenderModelV1` |
| `sections[].title` | Sourced from docdef section config, not document data |
| `blocks[].key` | Always `section_id:index`, stable across renders |

---

## Document Identity

### document_id Strategy (Frozen)

Two modes:

| Mode | Strategy |
|------|----------|
| **Stored document** | `document_id` = database UUID (string form) |
| **On-demand render** (preview) | `document_id` = `sha256(document_type + canonical(params))[:16]` |

Where `canonical(params)` = params keys sorted, values normalized to strings, serialized as `k=v&k2=v2`.

This enables stable caching and traceability without requiring persistence.

---

## Document Type Resolution (Frozen)

URLs use a short name: e.g., `EpicDetailView`, `StorySummaryView`

The server resolves to the latest accepted docdef matching:
```
docdef:{document_type}:<semver>
```
Where `status=accepted` and semver is highest.

Explicit version selection (e.g., `?version=1.0.0`) is out of scope for MVP.

---

## Fragment & Component Resolution

### Resolution Path (Frozen)

For each block:

1. `block.type` = `schema:SomethingBlockV1`
2. Lookup `CanonicalComponent` by `schema_id == block.type`
3. Resolve fragment binding: `component.view_bindings.web.fragment_id`
4. Render fragment using block variables (see below)

If a block type has no component or no web binding:
- Render a standard **Unknown Block** placeholder with the schema id shown.

### Fragment Variable Contract (Frozen)

Variables always available to fragments:

| Variable | Description |
|----------|-------------|
| `block.type` | Schema ID of the block |
| `block.key` | Stable key (`section_id:index`) |
| `block.data` | Block payload (schema-specific) |
| `block.context` | Display context (titles, styles) |

**Container convention:**
- Container blocks provide `block.data.items` (array)
- Container fragments iterate items internally and bind each element as `item`

So:
- Single block fragments reference `block.data.*`
- Container item rendering references `item.*` inside the loop

Both are valid and expected.

---

## detail_ref Contract

### Data Structure (Frozen)

```json
{
  "document_type": "StoryDetailView",
  "params": {
    "story_id": "AUTH-101"
  }
}
```

### URL Construction Rule (Frozen)

```
/view/{document_type}?{params as query string}
```

Example: `/view/StoryDetailView?story_id=AUTH-101`

### Viewer Behavior

- The viewer MUST render `detail_ref` as a navigable link.
- Link behavior (drawer/modal vs navigation) is a UI decision, but the URL rule is fixed.

---

## Actions (RenderActionV1)

**Deferred.** `RenderModelV1` may contain `actions`, but DocumentViewer v1.0:
- Ignores `actions` if present
- Does not render action UI
- Does not require `actions` to exist

Actions will be addressed in a future WS.

---

## Data Resolution Modes (Frozen)

### Mode A: Stored Document (Production)

```
GET /view/{document_type}?<params>
```

- Server resolves stored document by `(document_type, params)`
- If not found: return 404 with "Document not found" UI state

### Mode B: Preview (Admin/Dev)

```
POST /view/{document_type}/preview
Body: { "document_data": { ... } }
```

- Server builds RenderModel from provided data
- No persistence required

---

## Graceful Degradation (Frozen)

The viewer MUST handle failures without crashing:

| Failure | Behavior |
|---------|----------|
| Component not found for `block.type` | Render "Unsupported block" placeholder showing `block.type` and `block.key` |
| `view_bindings.web.fragment_id` missing | Render "No web fragment binding" placeholder with `component_id` |
| Fragment lookup fails | Render "Fragment not found" placeholder with `fragment_id` |
| Fragment render fails | Render "Fragment render error" placeholder (no stack traces in UI) |

**No missing binding may crash the page.**

---

## Rendering Rules

### Section Ordering

- Sections MUST be rendered in ascending `order`.
- Sections with no blocks MUST be omitted (not shown).

### Block Rendering

For each block in section:
1. Resolve component by `block.type`
2. Resolve fragment by `component.view_bindings.web.fragment_id`
3. Render fragment with `block` object (includes `data`, `context`, `key`, `type`)

---

## Security Constraints

- No HTML permitted in JSON payloads
- HTML produced only by server-side fragment rendering
- Fragment render errors must not leak stack traces to UI

---

## Determinism

Given identical inputs, the RenderModel output must be stable:
- Section ordering stable
- Block keys stable
- `document_id` stable for same inputs (per strategy above)

# ADR-034: DocumentViewer Implementation Summary

**Date:** 2026-01-09
**Status:** Routes functional, tests passing

## Completed This Session

### 1. RenderModel Nested Sections Structure

Updated `RenderModelBuilder` and response models:

| Change | File |
|--------|------|
| Added `RenderSection` dataclass | `render_model_builder.py` |
| Changed flat `blocks[]` → nested `sections[]` | `render_model_builder.py` |
| Added envelope fields | `render_model_builder.py` |
| Updated response models | `composer_routes.py` |
| Empty sections filtered at build time | `render_model_builder.py` |

**Envelope fields now present:**
- `render_model_version`: "1.0"
- `schema_id`: "schema:RenderModelV1"
- `schema_bundle_sha256`: computed hash
- `document_id`: deterministic or provided
- `document_type`: short name
- `title`, `subtitle`
- `sections[]`: nested with blocks
- `metadata.section_count`

### 2. DocumentViewer Routes

Created `app/web/routes/public/view_routes.py`:

| Route | Purpose |
|-------|---------|
| `GET /view/{document_type}` | Render stored document (501 for now) |
| `POST /view/{document_type}/preview` | Render preview from request body |

**Features:**
- `FragmentRenderer` class for block → HTML
- Preloads fragments by schema_id
- Uses `fragment_markup` from `FragmentArtifact`
- Graceful degradation with styled placeholders
- HTMX support (partial vs full page)

### 3. Templates

| Template | Purpose |
|----------|---------|
| `document_viewer_page.html` | Full page wrapper |
| `_document_viewer.html` | Section/block renderer partial |

### 4. Legacy Route Deprecation

Added deprecation warnings to `document_routes.py`:
- Routes still functional
- Log warnings on use
- Docstrings updated

### 5. Test Results

**All 1176 tests passing**

## API Examples

**Preview endpoint:**
```bash
POST /view/StorySummaryView/preview
Content-Type: application/json

{
  "document_data": {
    "story_id": "TEST-001",
    "intent": "Test story intent.",
    "phase": "mvp",
    "risks": []
  }
}
```

**JSON API (unchanged):**
```bash
POST /api/admin/composer/preview/render/docdef:StorySummaryView:1.0.0
```

Returns full RenderModel JSON with nested sections.

## Files Modified

| File | Change |
|------|--------|
| `app/domain/services/render_model_builder.py` | Nested sections, envelope fields, empty section filtering |
| `app/web/routes/admin/composer_routes.py` | Updated response models for sections |
| `app/web/routes/public/view_routes.py` | **NEW** - DocumentViewer routes |
| `app/web/routes/public/document_routes.py` | Added deprecation warnings |
| `app/web/routes/public/__init__.py` | Added view_router |
| `app/web/routes/__init__.py` | Added view_router |
| `app/web/templates/public/pages/document_viewer_page.html` | **NEW** |
| `app/web/templates/public/partials/_document_viewer.html` | **NEW** |

## Contract Compliance

Per `DOCUMENT_VIEWER_CONTRACT.md`:

| Requirement | Status |
|-------------|--------|
| Nested sections structure | ✅ |
| All envelope fields | ✅ |
| Empty sections omitted | ✅ |
| No HTML in JSON | ✅ |
| Deterministic document_id | ✅ |
| Graceful degradation | ✅ |
| Fragment resolution | ✅ |

## Next Steps (Future WS)

1. Implement `GET /view/{document_type}` for stored documents
2. Add golden-trace tests for all 9 document types
3. Create `VIEWER_ROUTES_AND_RESOLUTION.md` governance doc
4. Remove deprecated routes after migration period

# WS-ROUTE-001: Universal Document Resolver Endpoint

## Status: Draft

## Parent: WP-ROUTE-001
## Governing ADR: ADR-056
## Depends On: WP-ID-001 (entire WP must be complete)

## Objective

Create a single API endpoint that resolves any document by `project_id` and `display_id`. This is the backend half of deep linking — once it works, SPA deep links can be implemented incrementally.

## Scope

### In Scope

- New endpoint: `GET /api/v1/projects/{project_id}/documents/{display_id}`
- Uses `resolve_display_id()` from `display_id_service.py` to map prefix → doc_type_id
- Queries document by `(space_id, doc_type_id, display_id, is_latest=True)`
- Returns document JSON (content, metadata, version, status, display_id)
- 404 if project or document not found
- Tier-1 tests

### Out of Scope

- SPA routing changes (WS-ROUTE-002)
- SPA fallback (WS-ROUTE-002)
- API prefix consolidation (WS-ROUTE-003)
- Changes to existing document endpoints

## Implementation

### Step 1: Add resolver endpoint

**File:** `app/api/v1/routers/projects.py` (or a new `documents.py` router if cleaner)

```python
@router.get("/projects/{project_id}/documents/{display_id}")
async def get_document_by_display_id(
    project_id: str,
    display_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Resolve any document by project_id and display_id.

    Uses ADR-055 prefix resolution: display_id prefix → doc_type_id → document lookup.
    """
    # 1. Resolve project
    project = await _get_project_by_project_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    # 2. Resolve display_id → doc_type_id
    try:
        doc_type_id = await resolve_display_id(db, display_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Query document
    result = await db.execute(
        select(Document).where(
            Document.space_id == project.id,
            Document.doc_type_id == doc_type_id,
            Document.display_id == display_id,
            Document.is_latest == True,
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {display_id} in project {project_id}")

    # 4. Return document representation
    return {
        "id": str(doc.id),
        "display_id": doc.display_id,
        "doc_type_id": doc.doc_type_id,
        "title": doc.title,
        "summary": doc.summary,
        "content": doc.content,
        "version": doc.version,
        "status": doc.status,
        "lifecycle_state": doc.lifecycle_state,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }
```

### Step 2: Add project lookup helper

If `_get_project_by_project_id()` doesn't exist, add it:

```python
async def _get_project_by_project_id(db: AsyncSession, project_id: str):
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    return result.scalars().first()
```

## Tier-1 Tests

**File:** `tests/tier1/api/test_document_resolver.py`

- Valid project_id + valid display_id → 200 with document JSON
- Invalid project_id → 404
- Valid project_id + unknown display_id → 404
- Invalid display_id format (e.g., `wp_wb_001`) → 400
- display_id with unknown prefix → 400
- Response includes `display_id`, `doc_type_id`, `title`, `content`, `version`

## Allowed Paths

```
app/api/v1/routers/projects.py
tests/tier1/api/test_document_resolver.py
```

## Prohibited

- Do not modify `display_id_service.py`
- Do not modify existing document endpoints
- Do not add SPA routing (WS-ROUTE-002)
- Do not modify work_binder routes

## Verification

- `GET /api/v1/projects/HWCA-001/documents/PD-001` returns Project Discovery
- `GET /api/v1/projects/HWCA-001/documents/WP-001` returns Work Package
- `GET /api/v1/projects/HWCA-001/documents/INVALID` returns 400
- `GET /api/v1/projects/NOPE-999/documents/PD-001` returns 404
- All tests pass

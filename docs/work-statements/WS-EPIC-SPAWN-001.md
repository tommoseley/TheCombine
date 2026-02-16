# WS-EPIC-SPAWN-001: Auto-Spawn Epic Documents from Implementation Plan (Final)

## Status: All Phases Complete

## Purpose

When the Implementation Plan (Final) (`implementation_plan`) reaches stabilized/done, Epic child documents should be created automatically from the `epics[]` array in the plan content. The user should not need to click "Generate Epics" - the IPF is the commitment artifact and stabilization is the trigger.

The spawning infrastructure already exists (`_spawn_child_documents()`, `ImplementationPlanHandler.get_child_documents()`, `Document.parent_document_id`). This WS adds idempotency, drift handling, lineage tracking, production floor visibility, and a UX panel showing spawned epics.

## Governing References

- ADR-009: Project Audit (all state changes explicit and traceable)
- ADR-043: Production Line (tracks, states, stations)
- ADR-049: No Black Boxes (mechanical ops must be explicit)
- POL-WS-001: Work Statement Standard
- Existing: `ImplementationPlanHandler.get_child_documents()` in `app/domain/handlers/implementation_plan_handler.py`
- Existing: `PlanExecutor._spawn_child_documents()` in `app/domain/workflow/plan_executor.py`
- Existing: `Document.parent_document_id` FK in `app/api/models/document.py`

## Scope

### In Scope

- Idempotent epic spawning (rerun does not duplicate)
- Lineage fields on spawned Epic documents (parent_document_id, source metadata)
- Drift handling when IPF content changes (supersede removed epics, update changed epics)
- Epic documents visible as L2 children on the production floor
- "Produced N Epic documents" panel in the IPF document viewer with links
- SSE event on epic spawn so the floor updates live

### Out of Scope

- Epic document workflows (generation, QA gates) - epics are data snapshots from the IPF, not independently produced artifacts yet
- Feature spawning from epics (future WS)
- Epic detail viewer enhancements
- Any changes to the IPP (Primary) workflow - only the Final IPF triggers spawning

## Preconditions

1. `implementation_plan` workflow definition exists with `end_stabilized` terminal node
2. `ImplementationPlanHandler` exists with `get_child_documents()` implementation
3. `_spawn_child_documents()` is called from `_persist_produced_documents()` on stabilization
4. `epic` document type exists in `document_types` table
5. Master workflow (`software_product_development`) defines `implementation_plan.may_own: ["epic"]`

---

## Phase 1: Idempotent Spawning with Lineage

**Objective:** Make `_spawn_child_documents()` idempotent and add lineage metadata to spawned documents.

### Step 1.1: Add idempotency check to `_spawn_child_documents()`

**File:** `app/domain/workflow/plan_executor.py`

Before creating each child document, check if a document with the same `(space_id, doc_type_id, identifier)` already exists where `parent_document_id` matches:

```
For each child_spec:
    existing = SELECT FROM documents
        WHERE space_id = project_uuid
        AND doc_type_id = spec.doc_type_id
        AND parent_document_id = parent_id
        AND content->>'epic_id' = spec.identifier
        AND is_latest = true

    If existing:
        Update content, bump version, update revision_hash
        Log "Updated existing child: {identifier}"
    Else:
        Create new Document as today
        Log "Created child: {identifier}"
```

This ensures rerunning the same IPF stabilization updates rather than duplicates.

### Step 1.2: Add lineage metadata to spawned epic content

**File:** `app/domain/handlers/implementation_plan_handler.py`

Enrich `get_child_documents()` to include lineage in the epic content:

```python
epic_content["_lineage"] = {
    "parent_document_type": "implementation_plan",
    "parent_execution_id": None,  # Filled by caller
    "source_candidate_ids": epic.get("source_candidate_ids", []),
    "transformation": epic.get("transformation", "kept"),
    "transformation_notes": epic.get("transformation_notes", ""),
}
```

Update `_spawn_child_documents()` to inject `execution_id` into the lineage before persisting.

### Step 1.3: Add execution_id to _spawn_child_documents signature

**File:** `app/domain/workflow/plan_executor.py`

Pass `state.execution_id` through to `_spawn_child_documents()` so it can be recorded in lineage metadata. Update the call site in `_persist_produced_documents()`.

---

## Phase 2: Drift Handling

**Objective:** When an IPF is re-stabilized with a changed epic set, handle additions, removals, and updates.

### Step 2.1: Detect drift on re-stabilization

**File:** `app/domain/workflow/plan_executor.py`

In the idempotent spawn logic (Phase 1.1), after processing all child_specs:

```
existing_children = SELECT FROM documents
    WHERE parent_document_id = parent_id
    AND doc_type_id = 'epic'
    AND is_latest = true

spawned_ids = {spec.identifier for spec in child_specs}
existing_ids = {doc.content['epic_id'] for doc in existing_children}

removed_ids = existing_ids - spawned_ids
```

### Step 2.2: Supersede removed epics

For each `removed_id`:
- Set `is_latest = false` on the existing document
- Set `lifecycle_state = 'stale'` (using existing `mark_stale()` method)
- Log: `"Superseded epic {removed_id} - no longer in IPF"`

Do NOT delete. Superseded epics remain for audit trail.

### Step 2.3: Log drift event

Emit an SSE event when drift is detected:

```json
{
    "event": "children_updated",
    "data": {
        "parent_document_type": "implementation_plan",
        "child_doc_type": "epic",
        "created": ["new_epic_1"],
        "updated": ["existing_epic_2"],
        "superseded": ["removed_epic_3"]
    }
}
```

---

## Phase 3: Production Floor Visibility

**Objective:** Spawned epics appear as L2 children under the Implementation Plan node on the production floor.

### Step 3.1: Include epic children in production tracks

**File:** `app/api/services/production_service.py`

The existing `get_production_tracks()` already handles `may_own` and `child_doc_type` from the master workflow. Verify that:

1. Epic documents (spawned via Phase 1) are returned as children of the `implementation_plan` track
2. Each epic track includes: `document_type: "epic"`, `document_name`, `state: "produced"` (they're data snapshots, not workflow-produced)
3. Epic tracks have `scope: "project"` and `level: 2` (set by transformer)

If the existing child aggregation in `production_service.py` doesn't pick up spawned epics, add a query:

```python
child_docs = SELECT FROM documents
    WHERE parent_document_id = implementation_plan_document.id
    AND doc_type_id = 'epic'
    AND is_latest = true
```

Attach as `track["children"]` on the implementation_plan track.

### Step 3.2: Verify frontend epic rendering

The existing `addEpicsToLayout()` in `spa/src/utils/layout.js` already renders L2 children from `item.children`. Verify that spawned epic documents flow through:

1. API returns them in the track's `children` array
2. `transformProductionStatus()` maps them to the expected format
3. `buildGraph()` picks them up via `item.children`
4. `addEpicsToLayout()` renders them in the manifold grid

---

## Phase 4: IPF Document Viewer Panel

**Objective:** Show "This plan produced N Epic documents" with links in the IPF document viewer.

### Step 4.1: Add children endpoint or include in render model metadata

**Option A (preferred):** Include spawned children count and list in the render model metadata.

**File:** `app/api/v1/routers/projects.py` (render-model endpoint)

When building metadata for `implementation_plan`, query child documents:

```python
if doc_type_id == "implementation_plan":
    child_count = SELECT COUNT(*) FROM documents
        WHERE parent_document_id = document.id
        AND is_latest = true
    child_epics = SELECT doc_type_id, title, content->>'epic_id' as epic_id
        FROM documents
        WHERE parent_document_id = document.id
        AND is_latest = true
    meta["spawned_children"] = {
        "count": child_count,
        "items": [{"epic_id": c.epic_id, "title": c.title} for c in child_epics]
    }
```

### Step 4.2: Render panel in FullDocumentViewer

**File:** `spa/src/components/FullDocumentViewer.jsx`

When `metadata.spawned_children` exists and `count > 0`, render a panel below the document header:

```
+--------------------------------------------------+
| This plan produced 9 Epic documents               |
| local_storage_foundation | data_models | ...      |
+--------------------------------------------------+
```

Each epic name is a clickable chip that navigates to the epic document (or expands the epic node on the floor). Style: subtle info panel, not prominent.

---

## Prohibited Actions

- Do not delete superseded epic documents - mark as stale/not-latest only
- Do not spawn epics from the Primary Implementation Plan (IPP) - only the Final (IPF)
- Do not create epic workflow executions - epics are data snapshots, not independently produced
- Do not modify the IPF content or workflow to accommodate epic spawning
- Do not require user action to trigger epic creation - stabilization is the sole trigger
- Do not spawn epics if the IPF reaches `end_blocked` (only on `stabilized`)

## Verification Checklist

1. **First stabilization:** IPF stabilizes -> N epic documents created with correct content, lineage, and parent_document_id
2. **Idempotency:** Re-stabilize same IPF -> no duplicate epics, existing ones updated
3. **Drift - removal:** Re-stabilize with fewer epics -> removed epics marked stale, not deleted
4. **Drift - addition:** Re-stabilize with new epic -> new epic created alongside existing ones
5. **Production floor:** Epic nodes appear as L2 children under the Implementation Plan node
6. **Document viewer:** IPF viewer shows "Produced N Epic documents" panel with epic names
7. **SSE events:** `children_updated` event fires on spawn -> floor updates without refresh
8. **Lineage:** Each epic document's content includes `_lineage` with parent execution_id and source_candidate_ids
9. **Tests pass:** All existing tests pass (`python -m pytest tests/ -x -q`)

## Definition of Done

- Epic documents are automatically created when the Implementation Plan (Final) reaches stabilized
- Rerunning stabilization is idempotent (no duplicates)
- Removed epics are superseded (stale), not deleted
- Epics appear on the production floor as L2 children
- IPF document viewer shows spawned epic count with links
- All changes covered by tests
- SPA builds clean

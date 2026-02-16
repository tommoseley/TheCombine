# WS-INSTANCE-ID-001: Multi-Instance Document Support via instance_id

## Status: Draft

## Purpose

The `idx_documents_unique_latest` constraint enforces one `is_latest=TRUE` document per `(space_type, space_id, doc_type_id)`. This blocks multi-instance document types (epic, feature) where a project needs multiple latest documents of the same type. Epic spawning from the Implementation Plan fails silently at the second INSERT due to this constraint.

This WS adds an `instance_id` column to documents, replaces the single unique index with two partial indexes (single-instance and multi-instance), adds doc-type metadata for cardinality, updates the spawn logic to use `instance_id`, adds station metadata to the IPF workflow definition, and surfaces the idempotency key in the Workflow Studio audit drawer.

## Governing References

- **ADR-009**: Project Audit (all state changes explicit and traceable)
- **ADR-011-Part-2**: Document hierarchy (parent_document_id with RESTRICT)
- **ADR-043**: Production Line (tracks, states, stations)
- **WS-EPIC-SPAWN-001**: Auto-spawn epic documents (blocked by this constraint)
- **POL-WS-001**: Work Statement Standard
- **Existing**: `idx_documents_unique_latest` created in migration `20251217_003`
- **Existing**: `PlanExecutor._spawn_child_documents()` in `app/domain/workflow/plan_executor.py`
- **Existing**: `ImplementationPlanHandler.get_child_documents()` in `app/domain/handlers/implementation_plan_handler.py`
- **Existing**: `WorkflowAuditDrawer` in `spa/src/components/viewers/WorkflowAuditDrawer.jsx`

## Scope

### In Scope

- Add `instance_id` column (nullable VARCHAR(200)) to `documents` table
- Replace `idx_documents_unique_latest` with two partial unique indexes
- Add `cardinality` and `instance_key` columns to `document_types` table
- Update `document_types` rows for `epic` and `feature` with cardinality metadata
- Update `_spawn_child_documents()` to set `instance_id` on child documents
- Update spawn idempotency check to use `instance_id` column instead of JSONB content lookup
- Add station metadata to the `implementation_plan` DCW definition
- Add Idempotency Key field to the Workflow Studio audit drawer

### Out of Scope

- Epic or feature DCW workflows (epics remain data snapshots from IPF)
- Changes to the IPP (Primary) workflow
- Lineage ID in the Technical Architecture viewer
- Retroactive backfill of `instance_id` on existing documents (no multi-instance docs exist yet)
- Changes to the master POW definition

## Preconditions

1. `epic` and `feature` document types exist in `document_types` table
2. `_spawn_child_documents()` exists and is called on IPF stabilization (WS-EPIC-SPAWN-001)
3. No existing epic or feature documents in the database (confirmed: zero rows)
4. Current alembic head is `20260216_001`

---

## Phase 1: Schema Migration

**Objective:** Add `instance_id` to documents, replace the unique index with two partial indexes, and add cardinality metadata to document_types.

### Step 1.1: Create alembic migration

**File:** `alembic/versions/20260216_002_add_instance_id.py`

Revision: `20260216_002`, revises: `20260216_001`

**Upgrade operations (in order):**

1. Add `instance_id` column to `documents`:

```sql
ALTER TABLE documents ADD COLUMN instance_id VARCHAR(200);
```

2. Create index on `instance_id` for query performance:

```sql
CREATE INDEX idx_documents_instance_id
ON documents (instance_id)
WHERE instance_id IS NOT NULL;
```

3. Drop the existing unique index:

```sql
DROP INDEX idx_documents_unique_latest;
```

4. Create two replacement partial unique indexes:

```sql
-- Single-instance: one latest per (space, doc_type) when instance_id is NULL
CREATE UNIQUE INDEX idx_documents_latest_single
ON documents (space_type, space_id, doc_type_id)
WHERE is_latest = TRUE AND instance_id IS NULL;

-- Multi-instance: one latest per (space, doc_type, instance_id) when instance_id is set
CREATE UNIQUE INDEX idx_documents_latest_multi
ON documents (space_type, space_id, doc_type_id, instance_id)
WHERE is_latest = TRUE AND instance_id IS NOT NULL;
```

5. Add `cardinality` and `instance_key` columns to `document_types`:

```sql
ALTER TABLE document_types ADD COLUMN cardinality VARCHAR(20) NOT NULL DEFAULT 'single';
ALTER TABLE document_types ADD COLUMN instance_key VARCHAR(100);
```

6. Set cardinality metadata for multi-instance types:

```sql
UPDATE document_types SET cardinality = 'multi', instance_key = 'epic_id'
WHERE doc_type_id = 'epic';

UPDATE document_types SET cardinality = 'multi', instance_key = 'feature_id'
WHERE doc_type_id = 'feature';
```

**Downgrade operations (reverse order):**

1. Reset cardinality on epic/feature rows
2. Drop `cardinality` and `instance_key` columns from `document_types`
3. Drop `idx_documents_latest_multi`
4. Drop `idx_documents_latest_single`
5. Recreate original `idx_documents_unique_latest` on `(space_type, space_id, doc_type_id) WHERE is_latest = TRUE`
6. Drop `idx_documents_instance_id`
7. Drop `instance_id` column from `documents`

### Step 1.2: Update Document model

**File:** `app/api/models/document.py`

Add `instance_id` column to the Document class:

```python
instance_id: Mapped[Optional[str]] = Column(
    String(200),
    nullable=True,
    index=False,  # Handled by partial index in migration
    doc="Stable domain identifier for multi-instance doc types (e.g., epic_id). NULL for single-instance types."
)
```

Add `instance_id` to any `to_dict()` or serialization methods if present.

### Step 1.3: Update DocumentType model

**File:** `app/api/models/document_type.py`

Add columns:

```python
cardinality = Column(
    String(20),
    nullable=False,
    default="single",
    doc="'single' = one latest per space, 'multi' = multiple instances per space"
)

instance_key = Column(
    String(100),
    nullable=True,
    doc="Content field name used as instance_id for multi-instance types (e.g., 'epic_id')"
)
```

Add both to `to_dict()`.

**Verification:**

- `alembic upgrade head` succeeds
- `SELECT column_name FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'instance_id'` returns 1 row
- `SELECT cardinality, instance_key FROM document_types WHERE doc_type_id = 'epic'` returns `('multi', 'epic_id')`
- Existing single-instance documents still work (is_latest constraint unchanged for NULL instance_id)
- All existing tests pass

---

## Phase 2: Update Spawn Logic

**Objective:** `_spawn_child_documents()` sets `instance_id` on child documents and uses it for idempotency lookups.

### Step 2.1: Set instance_id on child document creation

**File:** `app/domain/workflow/plan_executor.py`

In `_spawn_child_documents()`, when creating a new Document (around line 2051), set `instance_id` from the child spec's `identifier`:

```python
child_doc = Document(
    space_type="project",
    space_id=UUID(state.project_id),
    doc_type_id=spec["doc_type_id"],
    title=spec["title"],
    content=spec["content"],
    version=1,
    is_latest=True,
    status="draft",
    created_by=None,
    parent_document_id=parent_id,
    instance_id=spec.get("identifier"),  # <-- ADD THIS
)
```

### Step 2.2: Use instance_id for idempotency lookup

**File:** `app/domain/workflow/plan_executor.py`

Replace the existing idempotency check that reads from JSONB content (line 2018-2029):

**Before:**
```python
existing_result = await self._db_session.execute(
    select(Document).where(
        Document.parent_document_id == parent_id,
        Document.doc_type_id.in_([s["doc_type_id"] for s in child_specs]),
        Document.is_latest == True,
    )
)
existing_children = {
    doc.content.get("epic_id", ""): doc
    for doc in existing_result.scalars().all()
    if isinstance(doc.content, dict)
}
```

**After:**
```python
existing_result = await self._db_session.execute(
    select(Document).where(
        Document.parent_document_id == parent_id,
        Document.doc_type_id.in_([s["doc_type_id"] for s in child_specs]),
        Document.is_latest == True,
    )
)
existing_children = {
    doc.instance_id: doc
    for doc in existing_result.scalars().all()
    if doc.instance_id
}
```

### Step 2.3: Validate instance_id on write

**File:** `app/domain/workflow/plan_executor.py`

Before the creation loop in `_spawn_child_documents()`, add validation:

```python
for spec in child_specs:
    identifier = spec.get("identifier", "")
    if not identifier:
        logger.error(
            f"Child spec for {spec.get('doc_type_id')} missing identifier - "
            f"skipping (would violate multi-instance uniqueness)"
        )
        continue
    spawned_ids.add(identifier)
    # ... existing create/update logic
```

**Verification:**

- IPF stabilization creates 7 epic documents with `instance_id` set
- `SELECT instance_id, title FROM documents WHERE doc_type_id = 'epic' AND is_latest = TRUE` returns 7 rows with distinct instance_ids
- Re-stabilizing the same IPF updates existing epics (version bumped), no duplicates
- All existing tests pass

---

## Phase 3: IPF Station Metadata

**Objective:** Add station metadata to the `implementation_plan` workflow definition so the production floor shows station progression.

### Step 3.1: Add station metadata to nodes

**File:** `combine-config/workflows/implementation_plan/releases/1.0.0/definition.json`

Add `station` object to each node, following the pattern established in `implementation_plan_primary`:

| Node | Station ID | Label | Order |
|------|-----------|-------|-------|
| `generation` | `draft` | `DRAFT` | 1 |
| `qa_gate` | `qa` | `QA` | 2 |
| `remediation` | `qa` | `QA` | 2 |
| `end_stabilized` | `done` | `DONE` | 3 |
| `end_blocked` | `done` | `DONE` | 3 |

Example for `generation` node:

```json
{
    "node_id": "generation",
    "type": "task",
    "name": "Document Generation",
    "station": {
        "id": "draft",
        "label": "DRAFT",
        "order": 1
    },
    ...
}
```

Bump the revision field to `"dcwrev_2026_02_16_a"`.

**Verification:**

- Production floor shows DRAFT / QA / DONE stations for the Implementation Plan track
- During IPF production: DRAFT is active, then QA, then DONE
- Completed IPF shows all stations as complete
- Blocked IPF shows correct failed station

---

## Phase 4: Audit Drawer - Idempotency Key

**Objective:** Surface `instance_id` in the Workflow Studio audit drawer so engineers can verify matching logic during live runs.

### Step 4.1: Add Spawned Documents section to audit drawer

**File:** `spa/src/components/viewers/WorkflowAuditDrawer.jsx`

When the workflow data includes a node that `produces` a document type with `may_own` children, add a "Spawned Documents" section below the Nodes table:

```
+-----------------------------------------------+
| Spawned Documents                              |
|  instance_id              | doc_type | status  |
|  backend_api_foundation   | epic     | created |
|  content_management       | epic     | created |
|  assessment_engine        | epic     | updated |
+-----------------------------------------------+
```

### Step 4.2: Include instance_id in API response

**File:** `app/api/v1/routers/projects.py` or relevant execution detail endpoint

When returning execution details or document children, include `instance_id`:

```python
{
    "instance_id": child_doc.instance_id,
    "doc_type_id": child_doc.doc_type_id,
    "title": child_doc.title,
    "version": child_doc.version,
}
```

The audit drawer reads this data to populate the Spawned Documents table.

**Verification:**

- Open Workflow Studio, click Audit on an IPF workflow that has spawned epics
- Spawned Documents section shows each epic with its `instance_id`
- Instance IDs match the `epic_id` values in the IPF document content

---

## Prohibited Actions

- Do not include `parent_document_id` in either unique index (lineage is not identity)
- Do not remove the unique constraint entirely - DB must enforce "single latest" under concurrency
- Do not hardcode multi-instance logic per doc_type - use `cardinality` and `instance_key` from document_types
- Do not set `instance_id` on single-instance document types (must remain NULL)
- Do not backfill `instance_id` on existing documents in this migration (no multi-instance docs exist)
- Do not modify the IPP (Primary) workflow definition
- Do not modify the master POW definition
- Do not add a Lineage ID field to any document viewer

## Verification Checklist

1. **Migration applies:** `alembic upgrade head` succeeds, `alembic downgrade -1` succeeds, `alembic upgrade head` succeeds again
2. **Single-instance preserved:** Creating a second `project_discovery` with `is_latest=TRUE` for the same project still fails
3. **Multi-instance works:** Creating 7 epic documents with distinct `instance_id` values for the same project succeeds
4. **Per-instance versioning:** Creating a second epic with `instance_id='backend_api_foundation'` and `is_latest=TRUE` fails (enforces one latest per instance)
5. **Spawn succeeds:** IPF stabilization creates N epic documents with correct `instance_id`, `parent_document_id`, and content
6. **Idempotency:** Re-stabilizing same IPF updates existing epics (version bumped), no duplicates
7. **Drift:** Re-stabilizing with fewer epics marks removed ones stale, does not delete
8. **Stations visible:** Production floor shows DRAFT/QA/DONE for IPF track
9. **Audit drawer:** Spawned Documents section shows instance_ids in Workflow Studio
10. **Doc-type metadata:** `document_types` table has correct `cardinality` and `instance_key` for epic and feature
11. **Tests pass:** All existing tests pass (`python -m pytest tests/ -x -q`)

## Definition of Done

- `instance_id` column exists on documents with two partial unique indexes enforcing correct uniqueness
- `document_types` table has `cardinality` and `instance_key` metadata for multi-instance types
- Epic documents spawn successfully from IPF stabilization with `instance_id` set
- Spawn idempotency uses `instance_id` column (not JSONB content lookup)
- IPF shows DRAFT/QA/DONE stations on the production floor
- Audit drawer shows Idempotency Key for spawned documents
- All changes covered by tests
- SPA builds clean

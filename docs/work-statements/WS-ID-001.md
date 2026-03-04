# WS-ID-001: Schema Migration for Document Identity Standard

## Status: Accepted

## Parent: WP-ID-001
## Governing ADR: ADR-055

## Objective

Create the alembic migration that adds `display_id` to `documents`, adds `display_prefix` to `document_types`, drops `instance_key`, and creates the new unique index. Update SQLAlchemy models to match. Fix pre-existing model/DB index mismatch. `instance_id` is left untouched.

## Preconditions

1. Current alembic head is `20260301_001`
2. ADR-055 accepted

## Do No Harm Findings (Incorporated)

1. **Model/DB index mismatch (pre-existing):** Document model `__table_args__` (line 316) defines `idx_documents_unique_latest` but DB actually has `idx_documents_latest_single` + `idx_documents_latest_multi` (from migration 20260216_002). This WS fixes the model to match the new index.
2. **14 doc types exist, not 8:** Migration must assign `display_prefix` to ALL registered doc types.
3. **`DocumentType.to_dict()` serializes `instance_key` (line 182):** Must be updated when column is dropped.
4. **`WorkflowInstance.instance_id`** is a UUID FK (different semantic). Must NOT be touched.
5. **combine-config package.yaml files** reference `instance_key`. Must be updated.
6. **`instance_id` is NOT repurposed.** New `display_id` column added instead. `instance_id` stays as-is.

## Scope

### In Scope

- Alembic migration `20260304_001_document_identity_standard`
- Add `display_id` VARCHAR(20) NOT NULL to `documents` (with temporary default for existing rows)
- Add `display_prefix` VARCHAR(4) NOT NULL to `document_types`
- Populate `display_prefix` for ALL registered doc types
- Drop `instance_key` column from `document_types`
- Create `idx_documents_latest_display` unique index on `(space_type, space_id, doc_type_id, display_id) WHERE is_latest = TRUE`
- Fix Document model `__table_args__` (remove stale `idx_documents_unique_latest`, add new index)
- Update `Document` model: add `display_id` column
- Update `DocumentType` model: add `display_prefix`, remove `instance_key`, update `to_dict()`
- Update combine-config package.yaml files: replace `instance_key` with `display_prefix`

### Out of Scope

- Minting logic (WS-ID-002)
- Wiring minting into creation paths (WS-ID-003)
- Changes to `derive_wp_id` or `generate_ws_id` (WS-ID-004)
- Any changes to the `projects` table (`project_id` already serves as slug)
- `instance_id` column — not modified, not dropped, not touched
- `WorkflowInstance.instance_id` — completely separate semantic

## Implementation

### Step 1: Create alembic migration

**File:** `alembic/versions/20260304_001_document_identity_standard.py`

Revision: `20260304_001`, revises: `20260301_001`

**Upgrade operations (in order):**

1. Add `display_id` to `documents` (nullable first for existing rows):
```sql
ALTER TABLE documents ADD COLUMN display_id VARCHAR(20);
```

2. Backfill existing rows with temporary values:
```sql
UPDATE documents SET display_id = 'LEGACY-' || LEFT(id::text, 8) WHERE display_id IS NULL;
```

3. Make `display_id` NOT NULL:
```sql
ALTER TABLE documents ALTER COLUMN display_id SET NOT NULL;
```

4. Create unique index:
```sql
CREATE UNIQUE INDEX idx_documents_latest_display
ON documents (space_type, space_id, doc_type_id, display_id)
WHERE is_latest = TRUE;
```

5. Add `display_prefix` to `document_types`:
```sql
ALTER TABLE document_types ADD COLUMN display_prefix VARCHAR(4);
```

6. Populate prefixes for ALL doc types:
```sql
UPDATE document_types SET display_prefix = 'PD' WHERE doc_type_id = 'project_discovery';
UPDATE document_types SET display_prefix = 'TA' WHERE doc_type_id = 'technical_architecture';
UPDATE document_types SET display_prefix = 'IP' WHERE doc_type_id = 'implementation_plan';
UPDATE document_types SET display_prefix = 'CI' WHERE doc_type_id = 'concierge_intake';
UPDATE document_types SET display_prefix = 'INT' WHERE doc_type_id = 'intent_packet';
UPDATE document_types SET display_prefix = 'XP' WHERE doc_type_id = 'execution_plan';
UPDATE document_types SET display_prefix = 'PX' WHERE doc_type_id = 'plan_explanation';
UPDATE document_types SET display_prefix = 'PR' WHERE doc_type_id = 'pipeline_run';
UPDATE document_types SET display_prefix = 'BLI' WHERE doc_type_id = 'backlog_item';
UPDATE document_types SET display_prefix = 'WPC' WHERE doc_type_id = 'work_package_candidate';
UPDATE document_types SET display_prefix = 'WP' WHERE doc_type_id = 'work_package';
UPDATE document_types SET display_prefix = 'WS' WHERE doc_type_id = 'work_statement';
UPDATE document_types SET display_prefix = 'EP' WHERE doc_type_id = 'epic';
UPDATE document_types SET display_prefix = 'FT' WHERE doc_type_id = 'feature';
```

7. Make `display_prefix` NOT NULL:
```sql
ALTER TABLE document_types ALTER COLUMN display_prefix SET NOT NULL;
```

8. Drop `instance_key`:
```sql
ALTER TABLE document_types DROP COLUMN instance_key;
```

**Downgrade operations (reverse order):**
1. Add `instance_key` back to `document_types`, repopulate known values
2. Drop `display_prefix` from `document_types`
3. Drop `idx_documents_latest_display`
4. Drop `display_id` column from `documents`

### Step 2: Update Document model

**File:** `app/api/models/document.py`

**2a.** Add `display_id` column (after `instance_id`):
```python
display_id: Mapped[str] = Column(
    String(20),
    nullable=False,
    doc="Human-readable identity in {TYPE}-{NNN} format (e.g., PD-001, WP-003). Immutable after creation."
)
```

**2b.** Fix `__table_args__` index definitions (lines 311-332). Replace the stale `idx_documents_unique_latest` with the new index:
```python
__table_args__ = (
    Index("idx_documents_space", "space_type", "space_id"),
    Index(
        "idx_documents_latest_display",
        "space_type", "space_id", "doc_type_id", "display_id",
        unique=True,
        postgresql_where=(is_latest == True)
    ),
    Index("idx_documents_search", "search_vector", postgresql_using="gin"),
    Index(
        "idx_documents_acceptance",
        "accepted_at", "rejected_at",
        postgresql_where=(is_latest == True)
    ),
)
```

### Step 3: Update DocumentType model

**File:** `app/api/models/document_type.py`

**3a.** Add `display_prefix`, remove `instance_key` (lines 90-103):
```python
display_prefix = Column(
    String(4),
    nullable=False,
    doc="Uppercase prefix for display_id (e.g., 'PD', 'WPC', 'WP')"
)
```

**3b.** Update `to_dict()` (line 182): replace `"instance_key": self.instance_key` with `"display_prefix": self.display_prefix`.

### Step 4: Update combine-config package.yaml files

Replace `instance_key` with `display_prefix` in all package.yaml files:

| File | Change |
|------|--------|
| `combine-config/document_types/work_package_candidate/releases/1.0.0/package.yaml` | `instance_key: wpc_id` → `display_prefix: WPC` |
| `combine-config/document_types/work_package/releases/1.0.0/package.yaml` | `instance_key: wp_id` → `display_prefix: WP` |
| `combine-config/document_types/work_package/releases/1.1.0/package.yaml` | `instance_key: wp_id` → `display_prefix: WP` |
| `combine-config/document_types/work_statement/releases/1.0.0/package.yaml` | `instance_key: ws_id` → `display_prefix: WS` |
| `combine-config/document_types/work_statement/releases/1.1.0/package.yaml` | `instance_key: ws_id` → `display_prefix: WS` |

## Tier-1 Tests

- `display_prefix` populated correctly for all registered doc types
- `display_id` column exists and is NOT NULL
- New unique index prevents duplicate `(space_type, space_id, doc_type_id, display_id)` where `is_latest = TRUE`
- DocumentType model `to_dict()` includes `display_prefix`, excludes `instance_key`
- Document model `__table_args__` defines `idx_documents_latest_display` (not stale index names)
- `instance_id` column is unchanged (still nullable, still present)

## Allowed Paths

```
alembic/versions/
app/api/models/document.py
app/api/models/document_type.py
combine-config/document_types/*/releases/*/package.yaml
tests/tier1/
```

## Prohibited

- Do not change any document creation logic (WS-ID-003)
- Do not modify `derive_wp_id` or `generate_ws_id` (WS-ID-004)
- Do not modify the `projects` table
- Do not modify any router or service files
- Do not modify `instance_id` on `documents` (leave as-is)
- Do not modify `WorkflowInstance.instance_id` (different semantic)
- Do not backfill real display_ids for existing documents (DB will be reset in WS-ID-005)

## Verification

- `alembic upgrade head` succeeds
- `alembic downgrade -1` succeeds
- `alembic upgrade head` succeeds again
- All existing tests pass
- Document model `__table_args__` matches actual DB indexes

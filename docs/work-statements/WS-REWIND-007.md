# WS-REWIND-007 — Document Versioning Schema Migration

**Status:** Draft
**Parent WP:** WP-REWIND-002
**Governing ADR:** ADR-063
**Prerequisite:** WS-REWIND-000 audit report

## Objective

Migrate the documents table to support multiple versions per document type while maintaining backward compatibility with existing queries.

## Scope

### In Scope
- Drop `idx_documents_latest_single` partial unique index
- Drop `idx_documents_latest_multi` partial unique index
- Create new version-aware unique indexes
- Maintain `is_latest` column as computed/maintained flag
- Ensure existing data is preserved and valid after migration

### Out of Scope
- Changing application query patterns (WS-REWIND-008)
- Regeneration logic
- New tables beyond index changes

## Procedure

### Step 1: Create alembic migration
- Create new migration: `add_versioned_document_support`
- Drop `idx_documents_latest_single` (space_type, space_id, doc_type_id where is_latest and instance_id IS NULL)
- Drop `idx_documents_latest_multi` (space_type, space_id, doc_type_id, instance_id where is_latest and instance_id IS NOT NULL)
- Create `idx_documents_version_single`: (space_type, space_id, doc_type_id, version) unique where instance_id IS NULL
- Create `idx_documents_version_multi`: (space_type, space_id, doc_type_id, instance_id, version) unique where instance_id IS NOT NULL
- Keep `is_latest` column — it will be maintained by application logic for backward compat

### Step 2: Verify migration safety
- Run migration against dev database
- Verify all existing documents remain accessible
- Verify no data loss or constraint violations

### Step 3: Write downgrade migration
- Reverse: drop new indexes, recreate old partial unique indexes
- Verify downgrade works cleanly

### Step 4: Update model annotations
- Update `app/api/models/document.py` __table_args__ to reflect new indexes
- Add comments explaining the version-aware constraint model

## Verification Criteria
- Migration runs without errors on dev database
- All existing documents remain accessible after migration
- Multiple versions of same doc type can now be inserted
- `is_latest` column still exists and is queryable
- Downgrade migration reverses cleanly
- Model annotations match actual schema

## Allowed Paths
- alembic/versions/ (new migration)
- app/api/models/document.py (annotation update only)

## Prohibited Actions
- Do not delete existing data
- Do not remove `is_latest` column
- Do not change Document model fields (only __table_args__)
- Do not modify application query patterns in this WS

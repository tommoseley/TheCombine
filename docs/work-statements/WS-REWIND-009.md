# WS-REWIND-009 — Non-Destructive Regeneration Persistence

**Status:** Draft
**Parent WP:** WP-REWIND-002
**Governing ADR:** ADR-063

## Objective

Ensure that regeneration creates new document versions rather than overwriting existing ones, preserving full history for lineage and audit.

## Scope

### In Scope
- Update plan_executor document creation to increment version from max existing
- Update child document upsert to create new versions instead of mutating in place
- Link new versions to prior versions via supersedes relationship
- Mark prior versions as superseded when new version is created

### Out of Scope
- Rewind trigger logic (WP-REWIND-001)
- Regeneration entrypoint/orchestration (WP-REWIND-003)
- Schema migration (WS-REWIND-007)

## Procedure

### Step 1: Update plan_executor document creation
- In `_persist_produced_documents()`, query max existing version for (project_id, doc_type_id)
- Set new document version = max_version + 1 (instead of hardcoded 1)
- Set new document status = 'current'
- Mark previous version as superseded (if it exists and is current)
- Update is_latest flags accordingly

### Step 2: Update child document upsert
- In `_upsert_child_document()`, instead of mutating existing document:
  - Create new document with incremented version
  - Mark old document as superseded
  - Link via document_relations (supersedes)
- Preserve existing behavior when no prior version exists (create as v1)

### Step 3: Record supersedes relationship
- Use existing `DocumentRelation` with relation_type 'supersedes'
- New document supersedes the prior current version

### Step 4: Write tests
- Test: first creation sets version=1, status=current
- Test: second creation sets version=2, status=current; version=1 becomes superseded
- Test: child document regeneration creates new version, preserves old
- Test: supersedes relationship is recorded
- Test: is_latest flag is correct on both old and new versions

## Verification Criteria
- New documents get correct incremented version numbers
- Prior documents are marked superseded, not overwritten
- Supersedes relationships are recorded
- is_latest flag is maintained correctly
- First-time creation still works (v1)
- Tests pass

## Allowed Paths
- app/domain/workflow/plan_executor.py
- app/api/services/document_service.py
- tests/tier1/test_regeneration_persistence.py

## Prohibited Actions
- Do not overwrite or delete existing documents
- Do not modify document content of prior versions
- Do not remove backward-compatible version=1 behavior for new projects

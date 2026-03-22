# WS-REWIND-008 — Current Artifact Resolution

**Status:** Draft
**Parent WP:** WP-REWIND-002
**Governing ADR:** ADR-063

## Objective

Implement deterministic rules for resolving the current artifact per document type, replacing `is_latest == True` queries with version-aware resolution that respects the artifact status model.

## Scope

### In Scope
- Refactor `DocumentService.get_latest()` to use version-aware resolution
- Resolution rule: max version where status == 'current' (or fallback to is_latest for compat)
- Update repository `get_by_scope_type()` to use new resolution
- Backward compatibility: existing callers get the same result without code changes
- Legacy compatibility layer for callers using `is_latest`

### Out of Scope
- Schema migration (WS-REWIND-007)
- Updating all 25+ API endpoints (WS-REWIND-010 handles query filtering)
- Regeneration logic

## Procedure

### Step 1: Update DocumentService.get_latest()
- Change from `WHERE is_latest == True` to `ORDER BY version DESC LIMIT 1 WHERE status = 'current'`
- Fallback: if no 'current' document exists, fall back to `is_latest == True` for backward compat
- Log warning when fallback is used (indicates migration incomplete)

### Step 2: Update repository get_by_scope_type()
- When `version=None`, use max-version resolution instead of `is_latest == True`
- When `version` is specified, return exact version match
- Maintain backward compat: same return type, same behavior for existing callers

### Step 3: Maintain is_latest flag
- When a new version is created as 'current', set `is_latest=True` on new, `is_latest=False` on old
- This keeps all legacy queries working without modification
- Document that `is_latest` is now a computed/maintained flag, not the source of truth

### Step 4: Write tests
- Test: get_latest returns max version with status=current
- Test: when no current version exists, fallback to is_latest works
- Test: get_by_scope_type(version=2) returns exact version
- Test: creating new version updates is_latest on both old and new
- Test: existing callers get same results as before migration

## Verification Criteria
- get_latest() returns correct document for both old and new data
- Backward compatibility maintained for all existing callers
- is_latest is kept in sync as a maintained flag
- Fallback to is_latest logged as warning
- Tests cover both old-model and new-model data

## Allowed Paths
- app/api/services/document_service.py
- app/persistence/pg_repositories.py
- tests/tier1/test_current_artifact_resolution.py

## Prohibited Actions
- Do not remove `is_latest` column or queries (backward compat)
- Do not modify schema (handled by WS-REWIND-007)
- Do not change API endpoint signatures

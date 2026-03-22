# Do No Harm Audit: Document Versioning Assumptions

**Date:** 2026-03-21
**WS:** WS-REWIND-000
**ADR:** ADR-063

---

## Executive Summary

The current document model enforces single-document-per-type via partial unique indexes on `is_latest`. Changing to versioned documents impacts 4 layers: schema (2 indexes), services (1 critical method), API (25+ endpoints), and workflow (2 persistence paths). Existing infrastructure (`version` column, `is_latest` flag, `pinned_version` on relations) provides a foundation.

**Blast Radius: HIGH but concentrated.** The fix is mostly mechanical — change `is_latest == True` queries to version-aware resolution across ~25 locations.

---

## Database Constraints

### Partial Unique Indexes (Blocking)

| Index | Columns | Condition | Effect |
|-------|---------|-----------|--------|
| `idx_documents_latest_single` | space_type, space_id, doc_type_id | `is_latest=true AND instance_id IS NULL` | One current doc per single-instance type |
| `idx_documents_latest_multi` | space_type, space_id, doc_type_id, instance_id | `is_latest=true AND instance_id IS NOT NULL` | One current doc per multi-instance type |

**Migration:** Drop both, replace with version-aware uniqueness.

### Existing Helpful Infrastructure

- `Document.version` column exists (int, default 1)
- `Document.is_latest` column exists (bool, default True)
- `Document.status` column exists (string: draft/active/stale/archived)
- `Document.is_stale` column exists (bool)
- `DocumentRelation.pinned_version` exists
- `Document.lifecycle_state` exists (generating/partial/complete/stale)

---

## Repository Layer — LOW Blast Radius

| Method | File:Line | Assumes Single? | Notes |
|--------|-----------|-----------------|-------|
| `get_by_scope_type()` | pg_repositories.py:125 | YES | Uses `scalar_one_or_none()` with `is_latest==True`. Already has optional `version` param. |
| `save()` mark-old logic | pg_repositories.py:98 | YES | Unsets `is_latest` on all other docs of same type on save. |

**Fix:** Change `is_latest==True` to `ORDER BY version DESC LIMIT 1`. Already version-aware in interface.

---

## Service Layer — MEDIUM Blast Radius

| Method | File:Line | Assumes Single? | Callers |
|--------|-----------|-----------------|---------|
| `get_latest()` | document_service.py:189 | YES | 20+ indirect via create_document |
| `list_by_space()` | document_service.py:206 | NO | Returns list, already multi-doc safe |
| `mark_downstream_stale()` | document_service.py:316 | NO | Works by document ID, not type lookup |

**Fix:** Refactor `get_latest()` to use max-version resolution. Maintain `is_latest` as computed flag for backward compat.

---

## API Layer — HIGH Blast Radius

**25+ endpoints** use `scalar_one_or_none()` with `is_latest == True`:

| Router | Approx. Count | Key Endpoints |
|--------|---------------|---------------|
| projects.py | 15+ | /tree, /documents/{id}, /documents/{id}/render |
| work_binder.py | 8 | /binder, stabilization endpoints |
| documents.py | 2 | Document CRUD |

**Fix:** Batch refactor — either add `.order_by(version.desc()).limit(1)` subquery, or centralize through `get_latest()` which gets fixed once.

---

## Workflow Layer — HIGH Blast Radius

| Location | File:Line | Issue |
|----------|-----------|-------|
| Document creation | plan_executor.py:1843 | Hardcodes `version=1`, `is_latest=True` |
| Child document upsert | plan_executor.py:1953 | Mutates existing doc in-place, increments version |

**Fix:** Query max existing version before creation, increment. Child upsert creates new doc instead of mutating.

---

## Stabilization — HIGH Blast Radius

| Concern | Current State | Impact |
|---------|---------------|--------|
| Stabilization tracking | On Document: lifecycle_state, accepted_at/accepted_by | Per-document, not per-version |
| WP stabilization | Calls validate_stabilization on single WP doc | Assumes one WP per type |
| Destabilization | No destabilization path exists | Must be created |

**Decision needed:** Is stabilization per-document-instance or per-version?
**Recommendation:** Per-version. Each version has its own lifecycle_state and acceptance state.

---

## Binder Renderer — MEDIUM Blast Radius

| Concern | Current State |
|---------|---------------|
| Document collection | Queries `is_latest==True` per type for binder assembly |
| Version selection | No version selection — always "latest" |

**Fix:** Use current-artifact resolution (max version where status=current). No API change needed if resolution is centralized.

---

## Key Architectural Decisions

| # | Decision | Recommendation |
|---|----------|----------------|
| 1 | Keep `is_latest` flag? | YES — maintain as computed/synced flag for backward compat |
| 2 | Stabilization per-document or per-version? | Per-version — each version owns its lifecycle |
| 3 | Display_id uniqueness with versions? | Keep unique at latest-only (current partial index approach, just change the filter) |
| 4 | How to determine "current"? | Max version where status='current', fallback to is_latest for compat |

---

## Migration Complexity Assessment

| Component | Complexity | Effort |
|-----------|-----------|--------|
| Schema migration (drop/create indexes) | LOW | 1 migration |
| Repository refactor | LOW | 1 method change |
| DocumentService.get_latest() | MEDIUM | 1 method + 20 callers verified |
| API endpoint batch refactor | MEDIUM-HIGH | 25+ sites, mostly mechanical |
| plan_executor versioning | MEDIUM | 2 methods |
| Stabilization model | MEDIUM | Design decision + implementation |
| Binder renderer | LOW | Follows from get_latest() fix |

**Overall: Contained migration, not a document-model refactor.** The existing `version`, `is_latest`, and `status` columns provide the foundation. The work is primarily query pattern updates, not schema redesign.

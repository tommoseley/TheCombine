# WP-REWIND-002 — Versioned Document Storage

**Status:** Draft
**Date:** 2026-03-21
**Governing ADR:** ADR-063
**Priority:** HIGH — execute after WP-REWIND-001
**Prerequisite:** WS-REWIND-000 audit report

## Objective

Modify the document storage layer to support multiple versions of a document per type per project, with deterministic current-artifact resolution, non-destructive regeneration, and backward-compatible query behavior.

## Scope

### In Scope
- Schema migration: relax unique constraints for versioned documents
- Current artifact resolution logic (max version where status=current)
- Non-destructive regeneration persistence
- Default query filtering (current-only unless audit mode)
- Backward compatibility layer for existing callers

### Out of Scope
- Rewind logic (WP-REWIND-001)
- Enforcement gates (WP-REWIND-003)
- UX (WP-REWIND-004)

## Dependencies
- WS-REWIND-000 audit report (blast radius assessment)
- WS-REWIND-002 artifact status model

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-REWIND-007 | Document Versioning Schema Migration | a0 |
| WS-REWIND-008 | Current Artifact Resolution | a1 |
| WS-REWIND-009 | Non-Destructive Regeneration Persistence | a2 |
| WS-REWIND-010 | Stale Artifact Query Filtering | a3 |

## Verification Criteria
- Multiple versions of same doc type can coexist in database
- Current artifact resolution is deterministic
- Regeneration creates new documents, does not overwrite
- Default queries return only current artifacts
- Existing callers continue to work (backward compat)
- All tests pass (Tier 0)

## Allowed Paths
- app/api/models/document.py
- app/persistence/pg_repositories.py
- app/api/services/document_service.py
- app/domain/workflow/plan_executor.py
- alembic/versions/
- tests/

## Prohibited Actions
- Do not delete or overwrite existing documents during migration
- Do not remove `is_latest` column (maintain for backward compat)
- Do not implement rewind or regeneration business logic
- Do not build UX components

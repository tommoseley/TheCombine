# WP-REWIND-001 — Rewind Core Semantics

**Status:** Draft
**Date:** 2026-03-21
**Governing ADR:** ADR-063 (Pipeline Rewind, Invalidation, and Regeneration Semantics)
**Priority:** HIGH — execute first

## Objective

Implement the semantic foundation for pipeline rewind: canonical stage model, artifact status model, linear rewind impact evaluation, rewind service, and lineage event recording. This WP does NOT require versioned document storage — it operates on status transitions of existing documents.

## Scope

### In Scope
- Canonical pipeline stage enum and ordering
- Artifact status model (current / stale / superseded)
- Linear rewind impact evaluator
- Rewind service contract and implementation
- Lineage event recording

### Out of Scope
- Document versioning schema migration (WP-REWIND-002)
- Stabilization revocation (WP-REWIND-003 — depends on versioned storage)
- Regeneration entrypoint (WP-REWIND-003)
- UX controls (WP-REWIND-004)

## Dependencies
- ADR-063 accepted
- WS-REWIND-000 (Do No Harm audit) completed before WS-007+

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-REWIND-000 | Do No Harm Audit: Document Versioning Assumptions | a0 |
| WS-REWIND-001 | Canonical Pipeline Stage Model | a1 |
| WS-REWIND-002 | Artifact Status Model | a2 |
| WS-REWIND-003 | Linear Rewind Impact Evaluator | a3 |
| WS-REWIND-004 | Rewind Service | a4 |
| WS-REWIND-006 | Lineage Event Recording | a5 |

## Verification Criteria
- Stage model is authoritative and enforced
- Status transitions are deterministic
- Rewind at stage N marks all downstream artifacts stale
- Lineage events are persisted and queryable
- All tests pass (Tier 0)

## Allowed Paths
- app/domain/services/
- app/domain/models/
- app/api/v1/routers/
- tests/tier1/
- docs/work-statements/

## Prohibited Actions
- Do not modify document table schema (deferred to WP-REWIND-002)
- Do not implement regeneration logic
- Do not build UX components
- Do not implement automatic rewind triggers (manual only for now)

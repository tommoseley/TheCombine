# WP-REWIND-003 — Regeneration Controls and Gate Enforcement

**Status:** Draft
**Date:** 2026-03-21
**Governing ADR:** ADR-063
**Priority:** HIGH — execute after WP-REWIND-002
**Prerequisites:** WP-REWIND-001 (core semantics), WP-REWIND-002 (versioned storage)

## Objective

Make rewind operational: regeneration entrypoint, downstream progression guards, QA rejection of stale artifacts, automatic destabilization, and human-readable failure messages.

## Scope

### In Scope
- Automatic destabilization of dependent artifacts on rewind
- Regeneration entrypoint (restart generation from rewind stage)
- Downstream progression guard (only current artifacts proceed)
- QA rejection of stale artifact inputs
- Human-readable reason-visible failure messages

### Out of Scope
- Automatic rewind triggers (manual only for now)
- Fine-grained dependency graphs
- UX (WP-REWIND-004)

## Dependencies
- WP-REWIND-001 (rewind service, status model, lineage)
- WP-REWIND-002 (versioned storage, current resolution, stale filtering)

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-REWIND-005 | Automatic Destabilization | a0 |
| WS-REWIND-011 | Regeneration Entrypoint | a1 |
| WS-REWIND-012 | Downstream Progression Guard | a2 |
| WS-REWIND-013 | QA Rejection of Stale Artifacts | a3 |
| WS-REWIND-015 | Reason-Visible Failure Messages | a4 |

## Verification Criteria
- Rewind automatically destabilizes downstream WPs/WSs
- Regeneration restarts pipeline from correct stage
- Stale artifacts cannot progress through the pipeline
- QA gates reject stale inputs with clear error messages
- All failure messages identify cause and required action
- All tests pass (Tier 0)

## Allowed Paths
- app/domain/services/
- app/domain/workflow/
- app/api/v1/routers/
- tests/tier1/

## Prohibited Actions
- Do not implement automatic rewind triggers
- Do not build UX components
- Do not implement fine-grained dependency graphs

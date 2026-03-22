# WP-REWIND-004 — Minimal Rewind UX

**Status:** Draft
**Date:** 2026-03-21
**Governing ADR:** ADR-063
**Priority:** MEDIUM — execute after WP-REWIND-003
**Prerequisites:** WP-REWIND-001, WP-REWIND-002, WP-REWIND-003

## Objective

Provide minimal user-facing controls for pipeline rewind: a rewind action, status badges for current/stale/superseded, a rewind summary panel, and basic lineage/audit visibility.

## Scope

### In Scope
- Rewind action control in pipeline UI
- Status badges (current/stale/superseded) on documents
- Rewind summary panel showing what changed and what's stale
- Minimal lineage/audit view for rewind events

### Out of Scope
- Branch/thread visualization
- Diff views between versions
- Automatic regeneration triggers from UI
- Advanced lineage graph rendering

## Dependencies
- WP-REWIND-001 (rewind service, status model)
- WP-REWIND-002 (versioned storage)
- WP-REWIND-003 (enforcement gates — for error display)

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-REWIND-016 | Rewind Action UI | a0 |
| WS-REWIND-017 | Status Badges | a1 |
| WS-REWIND-018 | Rewind Summary Panel | a2 |
| WS-REWIND-019 | Audit/History View | a3 |

## Verification Criteria
- User can trigger rewind from the pipeline UI
- Document status is visible as badges
- Rewind summary shows what changed and what's stale
- Lineage events are visible in audit view
- All error states from WP-REWIND-003 are surfaced in UI

## Allowed Paths
- spa/src/
- app/api/v1/routers/ (if new endpoints needed)
- tests/

## Prohibited Actions
- Do not implement branch/thread visualization
- Do not build diff/comparison views
- Do not add automatic regeneration triggers

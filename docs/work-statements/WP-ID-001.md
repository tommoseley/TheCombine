# WP-ID-001: Document Identity Standard

## Status: Accepted

## Governing ADR

ADR-055 — Document Identity Standard

## Objective

Implement universal `display_id` (`{TYPE}-{NNN}`) for all documents, replace incompatible ID formats (`wp_wb_NNN`, `WS-WB-NNN`), and enable deep linking by giving every document a stable, speakable, human-readable identity.

## Work Statements

| WS | Title | Depends On | Parallelizable |
|----|-------|------------|----------------|
| WS-ID-001 | Schema Migration | — | No (foundation) |
| WS-ID-002 | Minting Service + Prefix Resolution | WS-ID-001 | No |
| WS-ID-003 | Wire Minting into Document Creation | WS-ID-002 | Yes (with WS-ID-004) |
| WS-ID-004 | Eliminate derive_wp_id + generate_ws_id | WS-ID-002 | Yes (with WS-ID-003) |
| WS-ID-005 | DB Reset + Pipeline Validation | WS-ID-003, WS-ID-004 | No |

## Dependency Chain

```
WS-ID-001 → WS-ID-002 → WS-ID-003 ─┐
                          └→ WS-ID-004 ─┤→ WS-ID-005
```

WS-ID-003 and WS-ID-004 can run in parallel (non-overlapping allowed_paths).

## Preconditions

1. ADR-055 accepted
2. Current alembic head is `20260301_001`
3. No production data (greenfield — dev/test databases will be reset)

## Definition of Done

- `display_prefix` column exists on `document_types` with correct prefixes for all 8 doc types
- `instance_id` is NOT NULL on `documents`, stores display_id for all document types
- Single unified unique index replaces the two partial indexes
- `instance_key` column dropped from `document_types`
- `mint_display_id()` service mints sequential IDs per (space_id, doc_type_id)
- `resolve_display_id()` resolves prefix → doc_type_id via `display_prefix` registry
- All document creation paths call `mint_display_id()`
- `derive_wp_id()` and old-format `generate_ws_id()` eliminated
- Dev/test databases reset and pipeline regenerated under new identity scheme
- All tests pass, SPA builds clean

# WP-AUTH-001 — Durable Authority Context (ADR-064 MVP)

**Status:** Draft
**Date:** 2026-03-23
**Governing ADR:** ADR-064
**Priority:** HIGH — next priority after pipeline rewind completion
**Prerequisites:** ADR-063 pipeline rewind operational (WP-REWIND-003 complete)

## Objective

Implement durable, project-scoped authority records so that PGC answers survive pipeline rewind, regeneration skips already-answered questions, and QA gates can reference explicit authority bundles for compliance audits.

This is the ADR-064 MVP: authority_records table, persistence on PGC acceptance, hydration on regeneration, and QA bundle integration.

## Scope

### In Scope
- Authority records table (Alembic migration + ORM model)
- Authority repository (protocol + PostgreSQL + in-memory implementations)
- Authority service (persist, resolve current, supersede, mark historical)
- PGC answer persistence as authority records on acceptance
- Regeneration hydration from authority store (skip PGC when authority exists)
- QA authority bundle: explicit authority record references in compliance audit

### Out of Scope
- Bound constraint promotion from intake/discovery (future)
- User override authority type (future)
- Authority dashboard UI (future)
- Authority diff between paths (future)
- Artifact intake as authority records (future)
- Authority records display_ids (open question in ADR-064)
- PostgresLineageRepository (separate WS, not gated by this WP)

## Dependencies
- ADR-064 accepted (currently Draft — must be accepted before execution)
- ADR-063 pipeline rewind operational
- Alembic migration chain current (head: 20260321_001)

## Work Statements

| WS ID | Title | Order | Dependencies |
|-------|-------|-------|--------------|
| WS-AUTH-001 | Authority Records Table + ORM Model | a0 | None |
| WS-AUTH-002 | Authority Repository | a1 | WS-AUTH-001 |
| WS-AUTH-003 | Authority Service | a2 | WS-AUTH-002 |
| WS-AUTH-004 | PGC Answer Persistence as Authority | a3 | WS-AUTH-003 |
| WS-AUTH-005 | Regeneration Hydration from Authority Store | a4 | WS-AUTH-003 |
| WS-AUTH-006 | QA Authority Bundle Integration | a5 | WS-AUTH-003 |

**Parallelism:** WS-AUTH-004, WS-AUTH-005, and WS-AUTH-006 are independent of each other (all depend only on WS-AUTH-003). They may execute in parallel if allowed_paths do not overlap.

## Verification Criteria
- Authority records persist across execution boundaries
- PGC answers are stored as authority records on acceptance
- Regeneration after rewind skips PGC when current authority exists
- QA receives explicit authority bundle and can cite individual records
- Supersession: re-answering after rewind marks old answer as superseded
- Historical: path abandonment marks records as historical
- All tests pass (Tier 0)

## Allowed Paths
- app/domain/models/
- app/domain/repositories/
- app/domain/services/
- app/domain/workflow/
- app/api/models/
- app/core/database.py
- alembic/versions/
- tests/tier1/

## Prohibited Actions
- Do not modify PGC question generation logic
- Do not build authority dashboard UI
- Do not implement bound_constraint or user_override authority types (pgc_answer only for MVP)
- Do not implement PostgresLineageRepository (separate scope)
- Do not modify existing pgc_answers table structure

## MVP Surrogate: execution_id as lineage_path_id

ADR-064 defines `lineage_path_id` as the identifier for an accepted lineage path. True path identity requires PostgresLineageRepository (out of scope). For MVP, `execution_id` is used as a conservative surrogate. This is acceptable for the single-rewind regeneration use case but does not provide correct multi-rewind path semantics. See WS-AUTH-004 and WS-AUTH-005 for detailed impact analysis.

## Supersedes
- WS-REWIND-021 (authority context carry-forward) — absorbed into WS-AUTH-005

---

_End of WP-AUTH-001_

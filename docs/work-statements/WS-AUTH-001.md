# WS-AUTH-001: Authority Records Table + ORM Model

## Status: Draft

## Parent Work Package: WP-AUTH-001

## Governing References

- ADR-064 -- Durable Authority Context
- ADR-055 -- Document Identity Standard (model pattern reference)

## Verification Mode: A

## Allowed Paths

- app/api/models/
- app/domain/models/
- app/core/database.py
- alembic/versions/
- tests/tier1/

---

## Objective

Create the `authority_records` database table via Alembic migration and a corresponding SQLAlchemy ORM model. This is the persistence foundation for all authority context in the system.

---

## Preconditions

- Alembic migration chain is current (head: 20260321_001)
- PGCAnswer ORM model exists at app/api/models/pgc_answer.py (reference pattern)
- Document ORM model exists at app/api/models/document.py (reference pattern)

---

## Scope

### In Scope

- Alembic migration creating `authority_records` table
- SQLAlchemy ORM model (`AuthorityRecord`)
- Authority record dataclass (domain model, no SQLAlchemy dependency)
- Registration of ORM model in `app/core/database.py` `init_database()`
- Indexes for common query patterns:
  - `(project_id, status)` — current authority resolution
  - `(project_id, authority_type, key, status)` — supersession lookup (type-scoped)
  - `(lineage_path_id)` — path-historical bulk updates

### Out of Scope

- Repository layer (WS-AUTH-002)
- Service layer (WS-AUTH-003)
- Any wiring to PGC flow or QA

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **ORM model importable**: `AuthorityRecord` can be imported from `app.api.models.authority_record`
2. **Domain dataclass importable**: `AuthorityRecordDTO` can be imported from `app.domain.models.authority_record`
3. **Required columns present**: ORM model has all columns from ADR-064 Section 4.2 (id, project_id, authority_type, stage, key, value, source_execution_id, lineage_path_id, status, superseded_by, created_at, actor)
4. **Status enum values**: status column accepts "current", "superseded", "historical"
5. **Authority type enum values**: authority_type column accepts "pgc_answer" (MVP); schema allows future "bound_constraint", "user_override"
6. **Value is JSONB**: value column stores arbitrary JSON (not just strings)
7. **Migration applies cleanly**: Alembic upgrade from 20260321_001 creates the table without error
8. **Migration downgrades cleanly**: Alembic downgrade drops the table without error

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-8. Verify all fail.

### Phase 2: Implement

1. Create domain dataclass `AuthorityRecordDTO` at `app/domain/models/authority_record.py`
   - Fields per ADR-064 Section 4.2
   - UUID id (default factory)
   - status defaults to "current"
   - created_at defaults to utcnow
   - No SQLAlchemy dependency

2. Create ORM model `AuthorityRecord` at `app/api/models/authority_record.py`
   - Maps to `authority_records` table
   - Column types: UUID (id, project_id, source_execution_id, lineage_path_id, superseded_by), String (authority_type, stage, key, status, actor), JSONB (value), DateTime (created_at)
   - Indexes: (project_id, status), (project_id, authority_type, key, status), (lineage_path_id)
   - Foreign key to projects table on project_id (if projects table exists) or leave as UUID

3. Register ORM model import in `app/core/database.py` `init_database()`

4. Create Alembic migration `20260323_001_authority_records.py`
   - `down_revision = "20260321_001"`
   - Creates `authority_records` table with all columns and indexes
   - Downgrade drops the table

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not create repository or service layers (WS-AUTH-002, WS-AUTH-003)
- Do not modify existing tables or migrations
- Do not add foreign key constraints to tables that may not exist (workflow_executions)
- Do not implement query logic beyond what the ORM model provides

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] AuthorityRecordDTO dataclass created with all ADR-064 fields
- [ ] AuthorityRecord ORM model created with correct column types
- [ ] ORM model registered in init_database()
- [ ] Alembic migration created and applies cleanly
- [ ] Migration downgrades cleanly
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AUTH-001_

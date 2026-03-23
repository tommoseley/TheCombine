# WS-AUTH-002: Authority Repository

## Status: Draft

## Parent Work Package: WP-AUTH-001

## Governing References

- ADR-064 -- Durable Authority Context
- POL-CODE-001 -- Code Construction Standard (repository pattern)

## Verification Mode: A

## Allowed Paths

- app/domain/repositories/
- app/domain/models/
- tests/tier1/

---

## Objective

Create the authority repository layer: a Protocol definition, an InMemoryAuthorityRepository for Tier-1 tests, and a PostgresAuthorityRepository for runtime persistence. Follows the established repository pattern (async, no-commit, Protocol-based).

---

## Preconditions

- WS-AUTH-001 complete (AuthorityRecord ORM model and AuthorityRecordDTO exist)
- PGCAnswerRepository exists at app/domain/repositories/pgc_answer_repository.py (pattern reference)

---

## Scope

### In Scope

- `AuthorityRepository` Protocol with query methods
- `InMemoryAuthorityRepository` for Tier-1 tests
- `PostgresAuthorityRepository` for runtime
- Query methods:
  - `get_current_by_project(project_id)` — all current authority for a project
  - `get_current_by_project_type_key(project_id, authority_type, key)` — specific current authority record by type-scoped key (supersession lookup)
  - `get_by_lineage_path(lineage_path_id)` — all records on a lineage path
  - `add(record)` — persist a new authority record
  - `update_status(record_id, new_status, superseded_by=None)` — change status

### Out of Scope

- Business logic (resolution rules, supersession logic) — that is WS-AUTH-003
- Wiring to any workflow or service code

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Protocol importable**: `AuthorityRepository` Protocol can be imported from `app.domain.repositories.authority_repository`
2. **InMemory implements Protocol**: `InMemoryAuthorityRepository` satisfies `AuthorityRepository` Protocol
3. **add() persists**: adding a record makes it retrievable by project_id
4. **get_current_by_project() filters by status**: only returns records with status="current"
5. **get_current_by_project_type_key() returns matching record**: returns the correct current record for a given (project_id, authority_type, key) triple
6. **get_by_lineage_path() returns all path records**: returns all records sharing a lineage_path_id regardless of status
7. **update_status() changes status**: updates a record's status and optionally sets superseded_by
8. **update_status() on nonexistent record**: raises or returns None (no silent failure)
9. **Postgres repo importable**: `PostgresAuthorityRepository` can be imported (constructor takes AsyncSession)

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-9 using InMemoryAuthorityRepository. Verify all fail.

### Phase 2: Implement

1. Create Protocol at `app/domain/repositories/authority_repository.py`
   - All methods async
   - Type hints reference AuthorityRecordDTO
   - No implementation

2. Create `InMemoryAuthorityRepository` in same file (or separate test-support file)
   - List-backed storage
   - Implements all Protocol methods
   - Filtering by status, project_id, key, lineage_path_id

3. Create `PostgresAuthorityRepository` in same file
   - Constructor takes `AsyncSession`
   - Uses AuthorityRecord ORM model for queries
   - Converts between ORM model and AuthorityRecordDTO
   - Does NOT commit (caller owns transactions)

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not add business logic (resolution rules, supersession) — repository is pure CRUD
- Do not commit within repository methods
- Do not modify existing repositories
- Do not add dependencies on workflow or service code

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] AuthorityRepository Protocol defined
- [ ] InMemoryAuthorityRepository implements Protocol
- [ ] PostgresAuthorityRepository implements Protocol
- [ ] All query methods work correctly (tested via InMemory)
- [ ] No commits within repository methods
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AUTH-002_

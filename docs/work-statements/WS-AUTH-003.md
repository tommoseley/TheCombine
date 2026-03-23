# WS-AUTH-003: Authority Service

## Status: Draft

## Parent Work Package: WP-AUTH-001

## Governing References

- ADR-064 -- Durable Authority Context (Sections 4.2, 4.3)

## Verification Mode: A

## Allowed Paths

- app/domain/services/
- app/domain/models/
- tests/tier1/

---

## Objective

Create the authority service that implements ADR-064 resolution rules: persist new authority records, resolve current authority for a project, supersede records on re-answer, and mark records as historical on path abandonment. This is the business logic layer between the repository and the workflow integration points.

---

## Preconditions

- WS-AUTH-002 complete (AuthorityRepository Protocol and InMemoryAuthorityRepository exist)
- ADR-064 Section 4.3 resolution rules are the specification

---

## Scope

### In Scope

- `AuthorityService` class with repository dependency injection
- `record_authority(project_id, authority_type, stage, key, value, source_execution_id, lineage_path_id, actor)` — persist a new authority record; if a current record exists for the same `(project_id, authority_type, key)` triple, supersede it. Supersession is type-scoped: a pgc_answer record never collides with a future bound_constraint sharing the same key
- `get_current_authority(project_id)` — return all current authority records for a project
- `get_authority_bundle(project_id)` — return a structured dict suitable for injection into execution context (pgc_questions, pgc_answers, pgc_invariants keys)
- `supersede_record(old_record_id, new_record_id)` — mark old as superseded, link to new
- `mark_path_historical(lineage_path_id)` — mark all records on a path as historical
- Pure business logic, fully testable with InMemoryAuthorityRepository

### Out of Scope

- Wiring to PGC flow (WS-AUTH-004)
- Wiring to regeneration (WS-AUTH-005)
- Wiring to QA (WS-AUTH-006)
- bound_constraint and user_override authority types (future)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **record_authority creates current record**: new authority record has status="current"
2. **record_authority supersedes existing**: if a current record exists for same `(project_id, authority_type, key)`, old becomes "superseded" with superseded_by pointing to new record
3. **record_authority does not supersede cross-type**: a current pgc_answer record with key="X" is NOT superseded when a bound_constraint with key="X" is recorded (different authority_type)
4. **record_authority does not supersede historical**: a historical record for the same key is not touched when a new current record is created
5. **get_current_authority returns only current**: filters out superseded and historical records
6. **get_current_authority returns empty for unknown project**: returns empty list, not error
7. **get_authority_bundle structures correctly**: returns dict with canonical keys: `pgc_answers` (key→value mapping for pgc_answer type records), `pgc_questions` (list of question keys with current authority), `authority_record_ids` (list of record UUIDs for audit citation), `authority_source` (literal "durable_store")
8. **get_authority_bundle with no authority**: returns dict with empty `pgc_answers`, empty `pgc_questions`, empty `authority_record_ids`, `authority_source` = "none"
9. **supersede_record links records**: old record status="superseded", superseded_by=new_record_id
10. **mark_path_historical marks all records on path**: all records with matching lineage_path_id become "historical"
11. **mark_path_historical does not affect other paths**: records on different lineage_path_ids are unchanged

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-11 using InMemoryAuthorityRepository. Verify all fail.

### Phase 2: Implement

1. Create `AuthorityService` at `app/domain/services/authority_service.py`
   - Constructor takes `AuthorityRepository` (Protocol, not concrete class)
   - All methods async
   - `record_authority()`:
     - Check for existing current record with same (project_id, authority_type, key)
     - If found: supersede it (update_status to "superseded", set superseded_by)
     - Create new record with status="current"
     - Add via repository
   - `get_current_authority()`: delegate to repository `get_current_by_project()`
   - `get_authority_bundle()`:
     - Get current authority via `get_current_authority()`
     - Build dict with canonical keys:
       - `pgc_answers`: `{r.key: r.value for r in records if r.authority_type == "pgc_answer"}`
       - `pgc_questions`: `[r.key for r in records if r.authority_type == "pgc_answer"]`
       - `authority_record_ids`: `[r.id for r in records]`
       - `authority_source`: `"durable_store"` if records exist, `"none"` if empty
   - `supersede_record()`: update old status, set superseded_by
   - `mark_path_historical()`: get all records by lineage_path, update each to "historical"

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not wire into PGC, regeneration, or QA flows (WS-AUTH-004/005/006)
- Do not implement bound_constraint or user_override logic
- Do not commit transactions (service layer delegates to caller)
- Do not import workflow or plan_executor code

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] AuthorityService created with repository injection
- [ ] record_authority correctly creates and supersedes records
- [ ] get_current_authority filters correctly
- [ ] get_authority_bundle produces structured output
- [ ] supersede_record links records
- [ ] mark_path_historical scopes correctly to path
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AUTH-003_

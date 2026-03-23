# WS-AUTH-004: PGC Answer Persistence as Authority Records

## Status: Draft

## Parent Work Package: WP-AUTH-001

## Governing References

- ADR-064 -- Durable Authority Context (Section 3.1, 8.2)

## Verification Mode: A

## Allowed Paths

- app/domain/workflow/
- app/domain/services/authority_service.py
- tests/tier1/

---

## Objective

Wire PGC answer acceptance into the authority service so that every accepted PGC answer is persisted as a durable authority record. This is the ingress point: where transient execution-scoped answers become project-level authority.

---

## Preconditions

- WS-AUTH-003 complete (AuthorityService exists with record_authority method)
- PGC answer flow exists in plan_executor.py (context_state["pgc_answers"])
- PGCAnswerRepository persists to pgc_answers table (existing, execution-scoped)

---

## Scope

### In Scope

- After PGC answers are accepted and persisted to pgc_answers table, also persist each answer as an authority record via AuthorityService.record_authority()
- Map PGC answer fields to authority record fields:
  - authority_type = "pgc_answer"
  - stage = current pipeline stage
  - key = question_id
  - value = answer value (as JSON)
  - source_execution_id = current execution_id
  - lineage_path_id = current lineage path (or execution_id as proxy until lineage paths are implemented)
  - actor = "user" (PGC answers are always user-provided)
- Existing pgc_answers table continues to function (dual-write, not migration)

### Out of Scope

- Removing or modifying the existing pgc_answers table
- Modifying PGC question generation or UI
- Bound constraint extraction from intake/discovery
- Lineage path management (use execution_id as proxy — see MVP Surrogate note below)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **PGC answer persisted as authority**: when PGC answers are accepted, an authority record is created for each answer
2. **Authority record fields correct**: authority_type="pgc_answer", key=question_id, value=answer_value, stage matches current stage
3. **Dual write preserved**: existing pgc_answers table still receives the answer (no regression)
4. **Multiple answers create multiple records**: a PGC phase with 3 answers creates 3 authority records
5. **Re-answer supersedes (type-scoped)**: if the same question is answered again (same project_id + authority_type="pgc_answer" + key=question_id), the previous authority record is superseded
6. **Source execution tracked**: authority record's source_execution_id matches the current execution
7. **Missing authority service degrades gracefully**: if AuthorityService is not available (e.g., dependency injection not wired), PGC flow continues without authority persistence (log warning, don't crash)
8. **Fallback is operationally visible**: when authority persistence fails, the log entry includes a structured field (e.g., `authority_fallback=true`) that can be grepped/alerted on, not just a prose warning

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-7. Use InMemoryAuthorityRepository to verify authority records are created. Verify all fail.

### Phase 2: Implement

1. Identify the PGC answer acceptance point in plan_executor.py
   - Locate where pgc_answers are merged into context_state
   - This is the `_get_pgc_questions_for_merge()` / answer merge flow

2. After PGC answers are persisted to pgc_answers table, iterate answers and call:
   ```python
   await authority_service.record_authority(
       project_id=project_id,
       authority_type="pgc_answer",
       stage=current_stage,
       key=question_id,
       value=answer_value,
       source_execution_id=execution_id,
       lineage_path_id=execution_id,  # proxy until lineage paths exist
       actor="user"
   )
   ```

3. Inject AuthorityService into plan_executor (or access via service locator pattern matching existing code)

4. Add graceful degradation: wrap authority persistence in try/except, log warning on failure, don't block PGC flow

### Phase 3: Verify

1. All Tier 1 tests pass
2. Existing PGC tests still pass (no regression)
3. Tier 0 returns zero

---

## MVP Surrogate: execution_id as lineage_path_id

**This is an explicit MVP approximation, not true path identity.**

ADR-064 defines `lineage_path_id` as the identifier for an accepted lineage path through the pipeline. True path identity requires PostgresLineageRepository, which is out of scope for this WP.

For MVP, `execution_id` is used as a surrogate for `lineage_path_id`. This means:
- Each execution gets its own "path" — correct for fresh runs and single-rewind scenarios
- `mark_path_historical()` will mark records by execution_id, which is conservative but approximate
- Multi-rewind scenarios with complex path branching may not resolve correctly until true lineage paths are implemented
- **No code should treat execution_id as semantically equivalent to a lineage path** — variable names and comments must use `lineage_path_id` with a note that the value is an MVP surrogate

This surrogate is acceptable because the MVP only implements `pgc_answer` authority type, where the dominant use case is single-rewind regeneration.

---

## Prohibited Actions

- Do not modify PGC question generation logic
- Do not modify PGC user interaction flow or UI
- Do not remove or alter the existing pgc_answers table or PGCAnswerRepository
- Do not block PGC flow on authority persistence failure
- Do not implement lineage path management (use execution_id as proxy)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] PGC answer acceptance creates authority records
- [ ] Existing pgc_answers persistence unchanged (dual-write)
- [ ] Re-answer supersedes previous authority record
- [ ] Graceful degradation on authority service failure
- [ ] All existing PGC tests still pass
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AUTH-004_

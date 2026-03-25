# WS-AUTH-005: Regeneration Hydration from Authority Store

## Status: Draft

## Parent Work Package: WP-AUTH-001

## Governing References

- ADR-064 -- Durable Authority Context (Sections 3.4, 4.3 rules 4-5, 5)
- ADR-063 -- Pipeline Rewind

## Verification Mode: A

## Allowed Paths

- app/domain/workflow/plan_executor.py
- app/domain/workflow/nodes/
- app/domain/services/authority_service.py
- tests/tier1/

---

## Objective

When a pipeline stage regenerates after rewind, hydrate the execution context from the durable authority store instead of starting with empty context. If current authority exists for the project, skip the PGC phase and proceed directly to generation. This eliminates repeated questions and ensures regenerated artifacts are governed by the same authority.

**Supersedes:** WS-REWIND-021 (which proposed carrying forward context_state from prior execution — this WS uses the durable authority store instead).

---

## Preconditions

- WS-AUTH-003 complete (AuthorityService exists with get_authority_bundle method)
- Pipeline rewind operational (ADR-063 / WP-REWIND-003)
- plan_executor._load_pgc_answers_for_qa() exists (current injection point)
- plan_executor._build_context() exists (context assembly point)

---

## Scope

### In Scope

- On regeneration, call `AuthorityService.get_authority_bundle(project_id)` to hydrate context_state
- If authority bundle contains pgc_answers, inject them into context_state before PGC node executes
- PGC node detects pre-populated answers and auto-resolves (skips user interaction)
- Log that authority was inherited from durable store (not freshly gathered)
- input_documents must reference current upstream artifacts (not stale ones from prior execution)

### Out of Scope

- Modifying PGC question generation
- Authority record creation (WS-AUTH-004)
- QA bundle integration (WS-AUTH-006)
- Lineage path management beyond execution_id proxy

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Authority hydration on regeneration**: when regenerating a stage, context_state is populated with authority bundle from the durable store
2. **PGC skip when authority exists**: if context_state already contains pgc_answers from authority store, PGC node auto-resolves without user interaction
3. **Empty authority falls through**: if no current authority exists, PGC executes normally (no regression for fresh projects)
4. **Inherited authority logged**: log message indicates authority was inherited, including source record IDs
5. **Input documents use current upstream**: regeneration uses new upstream artifacts, not stale references from prior execution
6. **Authority bundle structure matches QA expectations**: hydrated context_state has pgc_questions, pgc_answers, pgc_invariants keys that QA node can consume
7. **No double-hydration**: if authority was already loaded (e.g., manual re-run), don't duplicate or overwrite

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-7. Use InMemoryAuthorityRepository pre-populated with authority records. Verify all fail.

### Phase 2: Implement

1. In plan_executor, identify the regeneration entry path
   - Currently: new execution starts with empty context_state
   - Target: before node execution begins, check for durable authority

2. Add authority hydration step in `_build_context()` or execution initialization:
   ```python
   authority_bundle = await authority_service.get_authority_bundle(project_id)
   if authority_bundle["authority_source"] == "durable_store":
       context_state["pgc_answers"] = authority_bundle["pgc_answers"]
       context_state["pgc_questions"] = authority_bundle["pgc_questions"]
       context_state["authority_record_ids"] = authority_bundle["authority_record_ids"]
       context_state["authority_source"] = "durable_store"
       log.info("Authority context inherited from durable store", record_ids=...)
   ```

3. In PGC node, add check: if context_state already has pgc_answers and authority_inherited=True, auto-resolve without asking user

4. Ensure _load_pgc_answers_for_qa() can consume authority-hydrated context (same keys, compatible format)

5. Inject AuthorityService into plan_executor (match existing DI pattern)

### Phase 3: Verify

1. All Tier 1 tests pass
2. Existing regeneration tests still pass
3. Tier 0 returns zero

---

## MVP Surrogate: execution_id as lineage_path_id

**This is an explicit MVP approximation, not true path identity.**

Authority hydration uses `get_authority_bundle(project_id)` which resolves by `status="current"`, not by lineage_path_id. This means hydration works correctly regardless of the lineage_path_id surrogate. However, `mark_path_historical()` (called on path abandonment) operates on the surrogate and may behave conservatively in multi-rewind scenarios.

**Practical impact for this WS:** Hydration is project-scoped (correct). Path-aware resolution is deferred. If a project has authority from multiple execution paths, all current records are hydrated — this is acceptable for MVP because only one path should be active at a time.

---

## Prohibited Actions

- Do not modify PGC question generation logic
- Do not create or modify authority records (WS-AUTH-004 handles creation)
- Do not carry forward stale input_documents from prior execution
- Do not remove existing PGC flow for fresh (non-regeneration) executions
- Do not implement true lineage path resolution (use execution_id surrogate per WS-AUTH-004)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] Regeneration hydrates context from authority store
- [ ] PGC auto-resolves when authority exists
- [ ] Fresh projects without authority work normally
- [ ] Authority inheritance is logged
- [ ] Input documents reference current upstream
- [ ] No double-hydration on re-runs
- [ ] All existing regeneration/PGC tests pass
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AUTH-005_

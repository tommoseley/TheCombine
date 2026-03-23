# WS-AUTH-006: QA Authority Bundle Integration

## Status: Draft

## Parent Work Package: WP-AUTH-001

## Governing References

- ADR-064 -- Durable Authority Context (Section 3.5)
- ADR-063 -- Pipeline Rewind (WS-REWIND-020 graceful degradation)

## Verification Mode: A

## Allowed Paths

- app/domain/workflow/nodes/qa.py
- app/domain/workflow/plan_executor.py
- app/domain/services/authority_service.py
- seed/prompts/                          # minimal prompt-contract tuning only
- combine-config/prompts/                # minimal prompt-contract tuning only
- tests/tier1/

---

## Objective

Wire QA gates to reference the durable authority bundle explicitly, so QA can distinguish between true noncompliance, missing authority, and superseded authority. Replace the heuristic-based graceful degradation (WS-REWIND-020) with authority-aware compliance validation.

---

## Preconditions

- WS-AUTH-003 complete (AuthorityService exists with get_authority_bundle method)
- QA node exists at app/domain/workflow/nodes/qa.py
- WS-REWIND-020 graceful degradation is in place (heuristic message matching, lines ~277-302 in qa.py)
- plan_executor._load_pgc_answers_for_qa() is the current QA context loading point

---

## Scope

### In Scope

- QA node receives authority bundle from durable store (via context_state or direct service call)
- QA can cite specific authority record IDs in compliance findings
- QA distinguishes three cases per ADR-064 Section 3.5:
  - "Document violates constraint X" (true noncompliance — authority record cited)
  - "Constraint X is missing from authority bundle" (incomplete authority — advisory)
  - "Constraint X was superseded by Y" (authority evolution — informational)
- Replace heuristic graceful degradation with authority-aware logic
- WS-REWIND-020 heuristic remains as fallback safety net (not removed, just deprioritized)
- Minimal QA prompt-contract tuning if needed: ensure the LLM has a way to express "authority incomplete" vs "authority violated" (targeted fix, not full prompt rewrite)

### Out of Scope

- Full QA prompt rewrite or version bump (requires separate WS per seed governance)
- Adding new QA validation checks beyond authority awareness
- Authority dashboard or reporting UI

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **QA receives authority bundle**: QA node has access to authority records (via context_state or injected service)
2. **True noncompliance cites authority**: when a document violates an authority-declared constraint, the finding includes the authority_record_id
3. **Missing authority is advisory**: when authority bundle is empty or incomplete, QA produces advisory finding (not hard fail)
4. **Authority-aware replaces heuristic**: QA checks for authority_inherited flag or authority_record_ids in context_state before falling back to heuristic message matching
5. **Full authority enables full audit**: when complete authority bundle is present, QA performs full semantic compliance (no graceful degradation)
6. **Superseded authority informational**: if QA encounters a superseded authority record, it logs informational note (not failure)
7. **Backward compatible**: projects without authority records still pass QA (graceful degradation preserved)

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-7. Use InMemoryAuthorityRepository to control authority state. Verify all fail.

### Phase 2: Implement

1. In `_load_pgc_answers_for_qa()` (plan_executor.py), augment the loading logic:
   - First try: load authority bundle from AuthorityService
   - If authority bundle has pgc_answers: use them (preferred path)
   - If not: fall back to existing PGCAnswerRepository.get_by_execution() (backward compat)
   - If neither: existing heuristic graceful degradation (WS-REWIND-020)

2. Authority bundle keys are canonical (defined in WS-AUTH-003):
   - `pgc_answers`: key→value mapping
   - `pgc_questions`: list of question keys
   - `authority_record_ids`: list of record UUIDs for audit citation
   - `authority_source`: `"durable_store"` | `"execution_scoped"` | `"none"`

   These keys are already in context_state if WS-AUTH-005 hydration ran. If not, set `authority_source` based on what `_load_pgc_answers_for_qa()` found:
   - PGC answers from authority store → `"durable_store"`
   - PGC answers from execution-scoped pgc_answers table → `"execution_scoped"`
   - Neither → `"none"`

3. In qa.py `_run_code_based_validation()` and `_run_drift_validation()`:
   - Check `context_state.get("authority_source")` to determine validation depth
   - If `"durable_store"`: full compliance audit, cite `authority_record_ids` in findings
   - If `"execution_scoped"`: full audit (existing behavior)
   - If `"none"`: advisory only (replace heuristic with explicit check)

4. Keep WS-REWIND-020 heuristic as tertiary fallback (defensive, not primary path)

### Phase 3: Verify

1. All Tier 1 tests pass
2. Existing QA tests still pass (backward compatibility)
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not perform a full QA prompt rewrite or version bump (that would require its own WS per seed governance)
- Minimal prompt-contract tuning IS permitted: if the QA prompt collapses "cannot audit" into an error-like finding, adjust the prompt instructions to distinguish "authority incomplete" from "authority violated" — this is a targeted contract fix, not a behavioral rewrite
- Do not remove WS-REWIND-020 heuristic entirely (keep as safety net)
- Do not add new validation checks beyond authority awareness
- Do not modify authority records from QA (QA is read-only for authority)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] QA receives authority bundle from durable store
- [ ] Compliance findings cite authority record IDs
- [ ] Missing authority produces advisory (not hard fail)
- [ ] Authority-aware logic takes precedence over heuristic
- [ ] Full audit when complete authority present
- [ ] Backward compatible with projects without authority
- [ ] WS-REWIND-020 heuristic preserved as fallback
- [ ] All existing QA tests pass
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AUTH-006_

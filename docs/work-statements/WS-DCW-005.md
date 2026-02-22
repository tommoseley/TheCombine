# WS-DCW-005: Seed Cleanup — Confirm combine-config Canonical, Deprecate Stale Seed Paths

## Status: Accepted

## Parent Work Package: WP-DCW-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- seed/
- combine-config/
- app/
- ops/
- tests/

---

## Objective

Confirm combine-config/ is the canonical runtime source for all workflow definitions, prompts, and schemas. Deprecate or remove stale seed/ paths and ops scripts that reference them. Assert that no runtime code falls back to seed/ when a combine-config/ artifact exists.

---

## Preconditions

- Current seed data lives in seed/registry/document_types.py and combine-config/
- ops/db/seed_data.py and ops/db/seed_acceptance_config.py are known stale (PROJECT_STATE flag)

---

## Scope

### In Scope

- Grep-based audit of app/ for any remaining seed/ path references in runtime code
- Delete or deprecate `ops/db/seed_data.py` and `ops/db/seed_acceptance_config.py`
- Verify no runtime code falls back to seed/ when combine-config/ artifact exists
- Decide fate of `seed/workflows/*.json` (keep as historical? delete? redirect with deprecation notice?)
- Confirm all document types are loadable from combine-config/ without seed fallback

### Out of Scope

- Seed governance changes (versioning, certification, manifest -- already established)
- Prompt content changes
- Schema content changes
- New seed data authoring
- Modifying combine-config/ content (this WS is cleanup, not creation)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **No runtime seed/workflows/ loading**: No runtime imports reference `seed/workflows/` for workflow loading (prompt assembler legacy fallback is the known exception — document or remove)
2. **Stale ops scripts cleaned**: `ops/db/seed_data.py` and `ops/db/seed_acceptance_config.py` are deleted or clearly marked deprecated with a pointer to the correct path
3. **All document types loadable from combine-config**: All document types loadable at runtime come from combine-config/ (no seed fallback needed)
4. **No broken imports**: No import statements reference deleted or moved seed modules
5. **Split-brain guard**: No workflow exists in `seed/workflows/` without a counterpart in `combine-config/workflows/` — structural invariant test passes
6. **Existing tests pass**: No regressions from seed path changes

---

## Procedure

### Phase 1: Audit

1. Grep app/, ops/, tests/ for all references to seed paths, seed scripts, and seed loading patterns
2. Classify each reference:
   - **Active**: Runtime depends on this, must work
   - **Stale**: Dead code, can be deleted or redirected
   - **Ambiguous**: Needs investigation
3. Produce audit report

### Phase 2: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-4. Verify they fail.

### Phase 3: Implement

1. Delete confirmed stale seed scripts
2. Redirect any active references to correct paths
3. Verify combine-config/ contains all needed configuration
4. Update any ops scripts that referenced old paths

### Phase 4: Verify

1. All Tier 1 tests pass
2. Existing tests pass
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify prompt content or schema content
- Do not change seed governance rules
- Do not delete seed/registry/document_types.py (that is the canonical source)
- Do not delete seed/prompts/ or seed/schemas/ (those are governed inputs)
- Do not create new seed loading mechanisms

---

## Verification Checklist

- [ ] Audit report produced
- [ ] Stale ops seed scripts deleted or deprecated
- [ ] No runtime code loads workflows from seed/
- [ ] No broken imports from seed path changes
- [ ] All document types loadable from combine-config/ without seed fallback
- [ ] Split-brain guard test passes (no seed workflow without combine-config counterpart)
- [ ] All Tier 1 tests pass after implementation
- [ ] Existing tests pass
- [ ] Tier 0 returns zero

---

_End of WS-DCW-005_

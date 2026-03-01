# WS-IAV-002: Fix IP Document Output Shape to Match Schema Authority

**Parent:** Standalone (follows WS-IAV-001 findings)
**Objective:** Patch the Implementation Plan handler and task prompt so emitted document JSON conforms to the governing schema (`combine-config/schemas/implementation_plan/releases/1.0.0/schema.json`). The WS-IAV-001 re-run found 7 FAIL findings — all caused by the handler emitting post-promotion WP structure instead of pre-promotion candidate structure.

**Depends on:** WS-IAV-001 (complete)

---

## Context

The IA verification report (`docs/audits/2026-03-01-ia-verification-ip-portfolio-agent.md`) identified a single systemic root cause: the IP handler/prompt emits `work_packages` with WP-level fields (`wp_id`, `governance_pins`, `source_candidate_ids`, `transformation`, `transformation_notes`) instead of `work_package_candidates` with candidate-level fields (`candidate_id` in WPC-### pattern). It also emits an undeclared `candidate_reconciliation` field and has `meta.schema_version` set to `"1.0"` instead of the schema-required `"3.0"`.

---

## Scope

**In scope:**
- Locate the IP task prompt and handler that assemble/emit IP document JSON
- Patch output shape to match schema:
  - Emit `work_package_candidates` (not `work_packages`) with `candidate_id` (WPC-### pattern) and candidate-only fields per `definitions.work_package_candidate`
  - Remove `candidate_reconciliation` from output (undeclared, `additionalProperties: false`)
  - Fix `risk_summary[].affected_candidates` to use WPC-### IDs (not `affected_wps` with WP IDs)
  - Set `meta.schema_version = "3.0"` per schema `const`
  - Remove `meta.workflow_id` (undeclared, `additionalProperties: false`)
- Add/adjust Tier-1 tests for:
  - `additionalProperties: false` violations (top-level, meta, candidate items)
  - `meta.schema_version` const = `"3.0"`
  - `risk_summary[].affected_candidates` field name and WPC-### pattern
  - `work_package_candidates` field name and `candidate_id` required field
- Re-run IA verification against a sample/fixture IP document to confirm all 7 FAILs resolve

**Out of scope:**
- Schema changes (the schema is correct; the document is wrong)
- Changes to other document type handlers or prompts
- Changes to the IA verification skill itself
- Fixing optional field absence (LOW findings from WS-IAV-001)

---

## Steps

### Step 1: Locate the IP handler and task prompt

Find:
- The handler that assembles/persists IP documents (likely in `app/domain/handlers/`)
- The task prompt that instructs the LLM what shape to emit (likely in `seed/prompts/tasks/` or `combine-config/prompts/tasks/`)
- Any post-processing or schema mapping in the handler that transforms LLM output before persistence

### Step 2: Write failing Tier-1 tests

Write tests that validate IP document output shape against the schema authority. These tests MUST fail before the fix (Bug-First Rule).

Tests to write:
1. **Top-level field compliance:** Assert `work_package_candidates` is present, `work_packages` is absent, `candidate_reconciliation` is absent
2. **meta compliance:** Assert `meta.schema_version == "3.0"`, assert `meta.workflow_id` is absent, assert only declared meta fields present
3. **Candidate item compliance:** Assert each item in `work_package_candidates` has `candidate_id` matching `^WPC-[0-9]{3}$`, assert no `wp_id`/`governance_pins`/`source_candidate_ids`/`transformation`/`transformation_notes`
4. **risk_summary compliance:** Assert each risk_summary item has `affected_candidates` (not `affected_wps`), assert each entry matches `^WPC-[0-9]{3}$`
5. **additionalProperties enforcement:** Assert no undeclared fields at top level, in meta, or in candidate items (validate against schema `properties{}` keys)

### Step 3: Fix the handler/prompt

Patch the output shape:
- If the handler post-processes LLM output: fix the field mapping
- If the prompt instructs the LLM to emit wrong field names: fix the prompt (with version bump per seed governance)
- If both: fix both

Specific changes:
- `work_packages` → `work_package_candidates`
- `wp_id` → `candidate_id` (with WPC-### pattern)
- Remove `governance_pins`, `source_candidate_ids`, `transformation`, `transformation_notes` from candidate items
- Remove `candidate_reconciliation` from output
- `risk_summary[].affected_wps` → `risk_summary[].affected_candidates` (with WPC-### values)
- `meta.schema_version` → `"3.0"`
- Remove `meta.workflow_id`

### Step 4: Verify tests pass

Run the Tier-1 tests from Step 2. All must pass.

### Step 5: Re-run IA verification

Run the ia-verification skill (Phase 1.1 only) against a fixture or sample IP document that exercises the fixed handler output. Confirm all 7 FAIL findings from WS-IAV-001 are resolved.

---

## Verification

- [ ] IP handler/prompt identified and patched
- [ ] Tier-1 tests written and passing for all 5 test categories
- [ ] `work_package_candidates` emitted with `candidate_id` (WPC-### pattern)
- [ ] `candidate_reconciliation` removed from output
- [ ] `risk_summary[].affected_candidates` uses WPC-### IDs
- [ ] `meta.schema_version = "3.0"`, `meta.workflow_id` absent
- [ ] No `additionalProperties: false` violations at any nesting level
- [ ] IA verification re-run produces 0 FAIL findings

---

## Allowed Paths

```
app/domain/handlers/
seed/prompts/tasks/
combine-config/prompts/tasks/
tests/tier1/
docs/audits/
```

---

## Prohibited

- Do not modify the IP schema (`combine-config/schemas/implementation_plan/`)
- Do not modify other document type handlers or prompts
- Do not modify the IA verification skill
- Do not modify active_releases.json or registry entries
- Do not change the WP, WS, or WPC schemas

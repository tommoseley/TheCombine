---
name: prompt-tuning
description: Run measured prompt improvement cycles per PROC-PROMPT-TUNING-001. Use when evaluator defects are found, new prompt versions need validation, or baseline measurements are needed for WP or WS artifact types.
---

# Prompt Tuning Skill

Controlled prompt improvement driven by measured defects. One defect per cycle, replay before and after, no guessing.

**Governing document:** `docs/governance/PROC-PROMPT-TUNING-001.md`

---

## When to Use

- Evaluator reports a defect class with >10% fail rate
- New prompt version created but not yet validated
- New evaluator rules added (T2 trigger — need fresh baseline)
- Operator requests baseline measurement or prompt improvement
- Dataset expanded with new scenarios

## When NOT to Use

- No measurable defects exist
- Dataset is saturated (all checks pass)
- System changes would confound results (e.g., evaluator and prompt changed simultaneously)

---

## Quick Commands

```bash
# Run WP baseline with active prompt version
cd ~/dev/TheCombine && python3 ops/scripts/wp_baseline_runner.py

# Run WP baseline with specific prompt version (A/B test)
cd ~/dev/TheCombine && python3 ops/scripts/wp_baseline_runner.py 1.1.1

# Results are saved to:
#   docs/audits/wp-baseline-v1.0.json
```

---

## Process Steps

### Step 1 — Baseline

Run the baseline runner against the fixed dataset. Record the defect distribution.

```bash
python3 ops/scripts/wp_baseline_runner.py
```

Read the output table. Identify any check with Fail > 0.

### Step 2 — Select One Defect

Pick the defect class with:
- Highest frequency (most scenarios affected), OR
- Highest impact (blocks downstream work)

**Only one defect per cycle.** Do not combine improvements.

### Step 3 — Draft Micro-WS

Create a minimal Work Statement targeting the defect:
- Target field (e.g., `scope_in`)
- Expected behavior change (e.g., "vague scope decomposed into investigation activities")
- Acceptance criteria (e.g., "semantic_scope fail rate drops to 0%")

### Step 4 — Modify Prompt

Create a new prompt version with a minimal, targeted change.

```
combine-config/prompts/tasks/{artifact_type}/releases/{new_version}/task.prompt.txt
```

Rules:
- Copy from current active version
- Add only the section needed for the target defect
- No unrelated changes
- No verbosity inflation
- Version increment (e.g., 1.1.1 → 1.1.2)

### Step 5 — Replay

Run the same dataset with the new prompt version:

```bash
python3 ops/scripts/wp_baseline_runner.py {new_version}
```

### Step 6 — Verify

Compare baseline vs new run:

| Check | Must Confirm |
|-------|-------------|
| Target defect | Reduced or eliminated |
| All other checks | No regressions (fail count same or lower) |
| New critical defects | None introduced |

### Step 7 — Promote or Revert

**If PASS:**
1. Activate in `combine-config/_active/active_releases.json` (tasks section)
2. Sync package-local prompt copy:
   ```
   combine-config/document_types/{type}/releases/{version}/prompts/task.prompt.txt
   ```
3. Run registry integrity tests: `python3 -m pytest tests/tier1/config/test_registry_integrity.py -v`
4. Commit with evidence

**If FAIL:**
- Do not activate
- Revert prompt or iterate on the same defect only

---

## Evaluators

### WP Evaluator

**Module:** `app/domain/services/wp_defect_evaluator.py` (v1.1)

| Check ID | Type | Description |
|----------|------|-------------|
| governance_pins_populated | structural | ta_version_id and policy_refs present |
| required_sections_present | structural | wp_id, title, rationale, governance_pins, scope |
| policy_floor_present | structural | POL-ADR-EXEC-001 in policy_refs |
| contradiction_disclosure_present | structural | contradiction_notes field present with content |
| ws_index_present | structural | ws_index exists (advisory only) |
| semantic_rationale | semantic | Rationale is meaningful (≥15 chars, not placeholder) |
| semantic_scope | semantic | Scope items are meaningful (≥20 chars, not placeholder) |
| semantic_definition_of_done | semantic | DoD items are meaningful (≥20 chars, not placeholder) |

### WS Evaluator

**Module:** `app/domain/services/ws_defect_evaluator.py` (v1.1)

| Check ID | Type | Description |
|----------|------|-------------|
| governance_pins_populated | structural | ta_version_id and policy_refs present |
| required_sections_present | structural | All 7 required WS sections present |
| tests_before_implementation | structural | Test steps precede implementation steps |
| step_grounding_heuristic | advisory | Steps reference upstream artifacts |
| contradiction_disclosure_present | structural | contradiction_notes present with content |
| semantic_objective | semantic | Objective is meaningful (≥15 chars, not placeholder) |
| semantic_scope | semantic | Scope items are meaningful (≥20 chars, not placeholder) |
| semantic_procedure | semantic | Procedure steps are meaningful (≥30 chars, not placeholder) |
| semantic_verification_criteria | semantic | Criteria are meaningful (≥20 chars, not placeholder) |

### Shared Classifier

**Module:** `app/domain/services/field_classifier.py`

`classify_field_content(value, min_length)` → `ABSENT` | `EMPTY` | `WEAK` | `MEANINGFUL`

- ABSENT: None
- EMPTY: empty string/list/whitespace
- WEAK: below min_length, or matches placeholder pattern (TBD, N/A, TODO, etc.)
- MEANINGFUL: passes all checks

---

## Prompt Locations

| Artifact | Active Release Config | Global Prompt | Package-Local Prompt |
|----------|----------------------|---------------|---------------------|
| WP | `combine-config/_active/active_releases.json` → tasks.work_package | `combine-config/prompts/tasks/work_package/releases/{v}/task.prompt.txt` | `combine-config/document_types/work_package/releases/{v}/prompts/task.prompt.txt` |
| WS | `combine-config/_active/active_releases.json` → tasks.work_statement | `combine-config/prompts/tasks/work_statement/releases/{v}/task.prompt.txt` | `combine-config/document_types/work_statement/releases/{v}/prompts/task.prompt.txt` |

**Both copies must stay in sync.** Registry integrity test catches divergence.

---

## Evidence Trail

Each tuning cycle should produce:
1. Baseline snapshot (runner output or JSON)
2. Defect selection (which check, which scenario)
3. Prompt diff (what changed)
4. Replay result (runner output with new version)
5. Delta comparison (before/after table)

Store in `docs/audits/` or commit message.

---

## Validation History

| Version | Defect Targeted | Result | Commit |
|---------|----------------|--------|--------|
| WS v1.1.0 | governance_pins empty (7/7 fail) | 7→0 failures | 63f2b92 |
| WP v1.1.0 | governance_pins empty (2/2 fail) | 2→0 failures | 63f2b92 |
| WP v1.1.1 | semantic_scope WEAK (1/5 fail) | 1→0 failures | c490ae3 |

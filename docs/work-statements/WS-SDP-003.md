# WS-SDP-003: Align IPF DCW Inputs and Prompt to ADR-053 Order

## Status: Draft

## Governing References

- ADR-053 -- Planning Before Architecture in Software Product Development
- ADR-050 -- Work Statement Verification Constitution
- WS-SDP-001 -- Reorder software_product_development POW (completed)

## Verification Mode: A

## Allowed Paths

- combine-config/document_types/implementation_plan/
- combine-config/workflows/implementation_plan/
- tests/

---

## Purpose

WS-SDP-001 reordered the POW so IPF runs before TA. The SPD POW step correctly
provides Discovery + IPP as inputs to the IPF step. However, the IPF's own
DCW definition, task prompt, and schema were not updated — they still reference
Technical Architecture as a required input and enforce TA-derived governance fields.

This causes the LLM to receive empty `input_documents` (TA doesn't exist yet)
and refuse to produce output.

---

## Scope

### In Scope

- IPF DCW workflow definition: remove `technical_architecture` from `requires_inputs`
- IPF task prompt: replace TA input references with Discovery input references
- IPF output schema: make `governance_pins.ta_version_id` optional (TA not yet produced)
- IPF package.yaml: add `project_discovery` to `required_inputs`
- Tests asserting correct input alignment

### Out of Scope

- POW definition (already correct per WS-SDP-001)
- Other document type definitions
- Handler changes
- Runtime code changes

---

## Do No Harm Audit

Before executing, verify:

1. SPD POW `implementation_plan` step inputs are `[project_discovery, implementation_plan_primary]`
2. IPF DCW `requires_inputs` currently contains `technical_architecture`
3. IPF task prompt currently references "Technical Architecture" as a required input
4. IPF schema currently requires `governance_pins.ta_version_id`
5. No other workflow or handler references `technical_architecture` as an input to `implementation_plan`

If any assumption is materially wrong, STOP and report.

---

## Procedure

### Step 1: Write Failing Tests

Add tests in `tests/tier1/` asserting:

1. IPF DCW `requires_inputs` does NOT include `technical_architecture`
2. IPF DCW `requires_inputs` includes `primary_implementation_plan`
3. IPF package.yaml `required_inputs` matches DCW `requires_inputs`
4. IPF task prompt does NOT reference "Technical Architecture" as a required input document
5. IPF schema `governance_pins.ta_version_id` is NOT in `required` array

Verify all 5 tests fail before proceeding.

### Step 2: Update IPF DCW workflow definition

**File:** `combine-config/workflows/implementation_plan/releases/1.0.0/definition.json`

Change `requires_inputs` from:
```json
["primary_implementation_plan", "technical_architecture"]
```
to:
```json
["primary_implementation_plan"]
```

### Step 3: Update IPF task prompt

**File:** `combine-config/document_types/implementation_plan/releases/1.0.0/prompts/task.prompt.txt`

- Replace the "Inputs Provided" section: IPF now receives Primary Implementation Plan
  (and optionally Project Discovery for context). Remove Technical Architecture as a
  required input.
- Remove or relax references to TA-derived constraints (e.g., "informed by Technical
  Architecture decisions").
- Update governance pinning rules: `ta_version_id` becomes optional (set to
  `"pending_ta"` or similar sentinel when TA is not yet available).
- Update failure conditions: remove "Empty/missing governance_pins.ta_version_id"
  as an automatic reject.

### Step 4: Update IPF output schema

**File:** `combine-config/document_types/implementation_plan/releases/1.0.0/schemas/output.schema.json`

- Remove `ta_version_id` from `governance_pins.required` array
- Keep the field definition (it will be populated when TA exists, empty when not)

### Step 5: Update IPF package.yaml

**File:** `combine-config/document_types/implementation_plan/releases/1.0.0/package.yaml`

Change `required_inputs` from:
```yaml
required_inputs:
  - primary_implementation_plan
```
to:
```yaml
required_inputs:
  - primary_implementation_plan
  - project_discovery
```

This aligns with what the SPD POW actually provides.

### Step 6: Verify

1. All 5 tests from Step 1 pass
2. Existing tests pass (no regressions)
3. Tier 0 passes

---

## Prohibited Actions

- Do not modify the SPD POW definition (already correct)
- Do not modify runtime code (handlers, orchestrator, executors)
- Do not modify other document type definitions
- Do not change the IPF schema structure beyond relaxing `ta_version_id` requirement
- Do not bump the prompt or schema version (this is a defect fix, not a new version)

---

## Verification Checklist

- [ ] Do No Harm audit passes (5 assumptions verified)
- [ ] All 5 tests fail before implementation
- [ ] IPF DCW `requires_inputs` has only `primary_implementation_plan`
- [ ] IPF task prompt references Discovery + IPP inputs (not TA)
- [ ] IPF schema does not require `governance_pins.ta_version_id`
- [ ] IPF package.yaml `required_inputs` includes `project_discovery`
- [ ] All 5 tests pass after implementation
- [ ] Existing tests pass
- [ ] Tier 0 passes

---

## Expected Blast Radius

Medium. Config-only changes across 4 files. No runtime code. The IPF will produce
different output (reconciling WP candidates without TA constraints), which is the
intended ADR-053 behavior.

---

_End of WS-SDP-003_

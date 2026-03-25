# WS-EVAL-002: TA Component Registry Schema Enrichment

## Status: Draft

## Parent Work Package: WP-EVAL-001

## Governing References

- ADR-061 -- Cross-Layer Contradiction Detection
- ADR-045 -- System Ontology

## Verification Mode: A

## Allowed Paths

- combine-config/document_types/technical_architecture/
- combine-config/prompts/tasks/technical_architecture/
- tests/tier1/test_cross_layer_evaluator.py

---

## Objective

Add an optional `owns` field to the TA component schema and adjust the TA prompt to instruct the LLM to populate it. This creates a machine-readable mapping from component → code paths that the cross-layer evaluator and future WS validation can use. Currently the TA declares components by name only — there's no way to validate that WSs' `allowed_paths` align with declared component ownership.

---

## Preconditions

- TA output schema exists at combine-config/document_types/technical_architecture/releases/1.0.0/schemas/output.schema.json
- TA prompt v1.1.0 exists at combine-config/prompts/tasks/technical_architecture/releases/1.1.0/task.prompt.txt
- TA prompt already mandates exhaustive component coverage

---

## Scope

### In Scope

- Add optional `owns` field (array of strings) to the component object in TA output schema
- Adjust TA prompt component registry rules to instruct LLM to populate `owns` with directory/file paths the component is responsible for
- Add test verifying schema accepts components with and without `owns`
- Minimal prompt adjustment (add instruction line, not a full rewrite)

### Out of Scope

- Cross-layer evaluator changes to consume `owns` (future WS)
- WS allowed_paths validation against component ownership (future)
- Changes to existing TA documents in the database

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Schema accepts owns field**: a TA component with `owns: ["src/trading/", "src/orders/"]` passes schema validation
2. **Schema allows empty owns**: a TA component without `owns` still passes validation (field is optional)
3. **Prompt instructs ownership**: TA prompt contains instruction to populate `owns` with code paths
4. **Existing schema tests pass**: no regression in TA schema validation

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-2 (schema validation with and without `owns`). Verify criterion 1 fails (schema rejects unknown field).

### Phase 2: Implement

1. In `combine-config/document_types/technical_architecture/releases/1.0.0/schemas/output.schema.json`:
   - Add to the component object properties:
     ```json
     "owns": {
       "type": "array",
       "items": { "type": "string" },
       "description": "Directory or file paths this component is responsible for"
     }
     ```
   - Do NOT add `owns` to `required` array — it's optional

2. In `combine-config/prompts/tasks/technical_architecture/releases/1.1.0/task.prompt.txt`:
   - Add to the Component Registry Rules section:
     ```
     - OWNERSHIP PATHS: Each component should declare an `owns` array listing the directory or file paths it is responsible for (e.g., `["src/trading/", "src/orders/"]`). This enables downstream validation that Work Statements' allowed_paths align with component boundaries.
     ```

### Phase 3: Verify

1. All new tests pass
2. Existing TA tests pass
3. Tier 0 returns zero

---

## Governance Note

PGC context and TA prompt are governed prompt fragments (ADR-045). Adding the `owns` instruction is a behavioral enrichment. Per seed governance rules, this requires a version bump on the TA prompt (1.1.0 → 1.2.0), re-certification, and manifest update.

## Prohibited Actions

- Do not make `owns` a required field
- Do not modify existing TA documents in the database
- Do not modify the cross-layer evaluator to consume `owns` (future scope)

---

## Verification Checklist

- [ ] Schema accepts components with `owns` field
- [ ] Schema accepts components without `owns` field
- [ ] TA prompt instructs LLM to populate `owns`
- [ ] All existing TA tests pass
- [ ] Tier 0 returns zero

---

_End of WS-EVAL-002_

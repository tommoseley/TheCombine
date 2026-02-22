# WS-DCW-003: Rewrite software_product_development POW for WP/WS Ontology

## Status: Accepted

## Parent Work Package: WP-DCW-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline WP/WS Integration
- ADR-053 -- Planning Before Architecture in Software Product Development

## Verification Mode: A

## Allowed Paths

- combine-config/workflows/
- combine-config/_active/
- tests/
- seed/workflows/          # parity only, not primary

---

## Objective

Rewrite the software_product_development POW definition to replace all Epic/Feature ontology with WP/WS. Scopes, document types, entity types, and iteration blocks must reference Work Packages and Work Statements. Step ordering must conform to ADR-053 (Discovery -> IPP -> IPF -> TA -> WP production -> WS decomposition).

---

## Preconditions

- WS-DCW-001 complete (WP DCW exists)
- WS-DCW-002 complete (WS DCW exists)
- Current POW definition at `combine-config/workflows/software_product_development/releases/1.0.0/definition.json` (runtime canonical source)

---

## Scope

### In Scope

- Replace scopes: epic/feature -> work_package/work_statement
- Replace document_types: epic/feature -> work_package/work_statement
- Replace entity_types: epic/feature -> work_package/work_statement
- Replace per_epic iteration with per_work_package iteration
- Replace feature_decomposition step with work_statement_decomposition step
- Confirm step ordering matches ADR-053
- Update all input references to use new document type names

### Out of Scope

- Handler modifications (already WP/WS aware)
- Schema changes to WP/WS documents
- DCW definitions (WS-DCW-001 and WS-DCW-002)
- UI changes (WS-SDP-002)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **No Epic references in POW**: POW definition contains zero references to "epic" as a scope, document type, or entity type
2. **No Feature references in POW**: POW definition contains zero references to "feature" as a scope, document type, or entity type
3. **WP scope exists**: Scopes include work_package with parent "project"
4. **WS scope exists**: Scopes include work_statement with parent "work_package"
5. **Step ordering matches ADR-053**: Steps execute in order: discovery, primary_plan, implementation_plan, technical_architecture, per_work_package
6. **Iteration block references WP**: per_work_package iterates over implementation_plan collection_field producing work_packages
7. **WS decomposition step exists**: Inside per_work_package, a step produces work_statement documents
8. **POW validates clean**: Workflow definition in combine-config passes schema validation with no warnings
9. **TA inputs include IPF**: Technical architecture step receives implementation_plan as input (per ADR-053, TA sees committed WPs)
10. **Split-brain guard**: If POW exists in `seed/workflows/` but not `combine-config/workflows/`, test fails

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-9. Verify all fail.

### Phase 2: Implement

1. Rewrite scopes section (project -> work_package -> work_statement)
2. Rewrite document_types section (replace epic/feature with work_package/work_statement)
3. Rewrite entity_types section (replace epic/feature with work_package/work_statement)
4. Rewrite steps in `combine-config/workflows/software_product_development/releases/1.0.0/definition.json`:
   - Keep discovery, primary_plan unchanged
   - Keep implementation_plan, update creates_entities to work_package
   - Update technical_architecture inputs to include implementation_plan
   - Replace per_epic block with per_work_package block
   - Replace feature_decomposition with work_statement_decomposition
5. Validate workflow definition against schema
6. Update `seed/workflows/` parity copy if maintaining dual copies

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify DCW definitions (those are WS-DCW-001 and WS-DCW-002)
- Do not modify handlers
- Do not modify prompts or schemas
- Do not keep Epic/Feature references as backward compatibility (clean break)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] Scopes reference work_package/work_statement
- [ ] Document types reference work_package/work_statement
- [ ] Entity types reference work_package/work_statement
- [ ] No epic/feature references remain in POW
- [ ] Step ordering matches ADR-053
- [ ] Iteration block produces WPs and decomposes into WSs
- [ ] POW validates clean (combine-config copy)
- [ ] Split-brain guard test passes (no seed workflow without combine-config counterpart)
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-DCW-003_

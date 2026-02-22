# WS-DCW-001: Work Package Document Creation Workflow

## Status: Accepted

## Parent Work Package: WP-DCW-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline WP/WS Integration

## Verification Mode: A

## Allowed Paths

- combine-config/workflows/
- combine-config/document_types/
- combine-config/prompts/
- combine-config/schemas/
- combine-config/_active/
- app/domain/handlers/
- tests/
- seed/workflows/          # parity only, not primary

---

## Objective

Create the DCW that produces Work Package documents from committed IPF output. The DCW defines how the system takes IPF work_package_candidates and produces governed WP documents with state, governance pins, scope, and Definition of Done.

---

## Preconditions

- work_package document type registered (WS-ONTOLOGY-001 -- complete)
- work_package handler exists (WS-ONTOLOGY-001 -- complete)
- IPF produces work_package_candidates (WS-ONTOLOGY-004/005 -- complete)

---

## Scope

### In Scope

- DCW definition (JSON workflow) for work_package production
- Task prompt for WP production (role: Project Manager)
- Output schema for WP document content
- Handler wiring to DCW
- Integration with IPF output (work_package_candidates as input)

### Out of Scope

- WP state machine changes (already built)
- WP UI rendering (already built)
- WS decomposition (that is WS-DCW-002)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **DCW definition valid**: work_package DCW passes workflow schema validation with no warnings
2. **Task prompt exists**: WP production task prompt is loadable and certified
3. **Output schema exists**: WP output schema validates a well-formed WP document
4. **IPF output consumed**: DCW input references IPF work_package_candidates correctly
5. **Handler produces valid WP**: Given IPF candidate input, handler produces a document that passes WP schema validation
6. **Governance pins populated**: Produced WP includes governance_pins from the current project context (TA version, ADR IDs)
7. **Runtime loadable**: DCW definition loadable by PlanRegistry from combine-config
8. **Split-brain guard**: If workflow exists in `seed/workflows/` but not `combine-config/workflows/`, test fails

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-6. Verify all fail.

### Phase 2: Implement

1. Author WP production task prompt in `combine-config/prompts/tasks/work_package/releases/1.0.0/`
2. Author WP output schema in `combine-config/document_types/work_package/releases/1.0.0/` (or `combine-config/schemas/work_package/releases/1.0.0/`)
3. Author work_package DCW definition in `combine-config/workflows/work_package/releases/1.0.0/definition.json`
4. Wire handler to consume IPF work_package_candidates and produce WP documents
5. Certify prompt + update `active_releases.json`
6. Update `seed/workflows/` parity copy if maintaining dual copies

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify the WP state machine
- Do not modify the WP handler's existing render/render_summary logic
- Do not create new document types
- Do not modify IPF output schema (consume what exists)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] DCW definition authored and valid
- [ ] Task prompt authored and certified
- [ ] Output schema authored and valid
- [ ] Handler wired to DCW
- [ ] Produced WPs include governance pins
- [ ] DCW definition loadable by PlanRegistry from combine-config
- [ ] Split-brain guard test passes (no seed workflow without combine-config counterpart)
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-DCW-001_

# WS-DCW-002: Work Statement Document Creation Workflow

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

Create the DCW that decomposes a committed Work Package into Work Statement documents. Each WS includes objective, scope, allowed paths, acceptance criteria, procedure, and verification checklist -- sufficient for Claude Code or a human executor to execute without ambiguity.

---

## Preconditions

- work_statement document type registered (WS-ONTOLOGY-002 -- complete)
- work_statement handler with parent WP enforcement exists (WS-ONTOLOGY-002 -- complete)
- WP documents can be produced (WS-DCW-001)

---

## Scope

### In Scope

- DCW definition (JSON workflow) for work_statement production
- Task prompt for WS decomposition (role: Business Analyst or Project Manager)
- Output schema for WS document content
- Handler wiring to DCW
- Parent WP reference enforcement (every WS links to its parent WP)
- TA constraints as input (WS decomposition should be architecture-aware per ADR-053)

### Out of Scope

- WS state machine changes (already built)
- WS execution by Claude Code (that is downstream of this DCW)
- Logbook transactional append (already wired, activates on runtime acceptance)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **DCW definition valid**: work_statement DCW passes workflow schema validation with no warnings
2. **Task prompt exists**: WS decomposition task prompt is loadable and certified
3. **Output schema exists**: WS output schema validates a well-formed WS document
4. **WP input consumed**: DCW input references parent WP document correctly
5. **TA input consumed**: DCW input includes TA constraints for architecture-aware decomposition
6. **Handler produces valid WSs**: Given WP input, handler produces documents that pass WS schema validation
7. **Parent enforcement holds**: Every produced WS references its parent WP ID
8. **Allowed paths populated**: Produced WSs include allowed_paths field (may be empty but field exists)
9. **Runtime loadable**: DCW definition loadable by PlanRegistry from combine-config
10. **Split-brain guard**: If workflow exists in `seed/workflows/` but not `combine-config/workflows/`, test fails

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-8. Verify all fail.

### Phase 2: Implement

1. Author WS decomposition task prompt in `combine-config/prompts/tasks/work_statement/releases/1.0.0/`
2. Author WS output schema in `combine-config/document_types/work_statement/releases/1.0.0/` (or `combine-config/schemas/work_statement/releases/1.0.0/`)
3. Author work_statement DCW definition in `combine-config/workflows/work_statement/releases/1.0.0/definition.json`
4. Wire handler to consume WP document and TA constraints, produce WS documents
5. Ensure parent WP enforcement on every produced WS
6. Certify prompt + update `active_releases.json`
7. Update `seed/workflows/` parity copy if maintaining dual copies

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify the WS state machine
- Do not modify parent WP enforcement logic (consume it, do not change it)
- Do not create new document types
- Do not modify WP schema or handler

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] DCW definition authored and valid
- [ ] Task prompt authored and certified
- [ ] Output schema authored and valid
- [ ] Handler wired to DCW
- [ ] Every produced WS references parent WP
- [ ] Allowed paths field present on produced WSs
- [ ] DCW definition loadable by PlanRegistry from combine-config
- [ ] Split-brain guard test passes (no seed workflow without combine-config counterpart)
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-DCW-002_

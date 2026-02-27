# WS-PIPELINE-001: Pipeline Config & Doc Type Consolidation

## Status: Complete

## Parent Work Package: WP-PIPELINE-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-053 -- Planning Before Architecture in Software Product Development
- POL-WS-001 -- Work Statement Standard

## Verification Mode: A

## Allowed Paths

- combine-config/
- app/domain/handlers/
- app/domain/handlers/registry.py
- app/web/static/spa/
- spa/src/components/DocumentNode.jsx
- tests/

---

## Objective

Collapse IPP and IPF into a single Implementation Plan (IP) document type. Fix the POW step ordering so that Work Packages are created after Technical Architecture, not before. Add execution mode metadata to POW steps (auto vs manual) so the runtime can distinguish pipeline-sequenced steps from user-initiated ones. Audit schemas and prompts to document what needs updating (prompt changes are out of scope).

---

## Preconditions

- POW definition exists: combine-config/workflows/software_product_development/releases/1.0.0/definition.json
- IPP package: combine-config/document_types/primary_implementation_plan/releases/1.0.0/
- IPF package: combine-config/document_types/implementation_plan/releases/1.0.0/
- TA package: combine-config/document_types/technical_architecture/releases/1.0.0/
- WP package: combine-config/document_types/work_package/releases/1.0.0/

---

## Current State (What Is Wrong)

### Pipeline Step Order (Current)
```
Step 1: discovery              -> PD   (inputs: none)
Step 2: primary_plan           -> IPP  (inputs: PD)
Step 3: implementation_plan    -> IPF  (inputs: PD, IPP)  ** creates_entities: work_package **
Step 4: technical_architecture -> TA   (inputs: PD, IPP, IPF)
Step 5: per_work_package       -> WS   (inputs: WP entity, TA)
```

### Problems

1. **IPP and IPF are redundant.** Same role prompt (project_manager:1.0.0), IPF takes IPP as input, no PGC between them. No new user decision is captured. This is waste.

2. **IPF creates WP entities at Step 3, before TA exists at Step 4.** WPs cannot reference architectural components they don't know about yet.

3. **WP required_inputs is only [implementation_plan].** Missing technical_architecture.

4. **IPP schema uses epic_set_summary.** Old ontology term. Should be plan_summary.

5. **No execution mode on steps.** All steps auto-fire sequentially. WP and WS creation should be user-initiated (manual) from the Work Binder.

---

## Target State

### Pipeline Step Order (Corrected)
```
Step 1: discovery              -> PD   (auto, inputs: none)
Step 2: implementation_plan    -> IP   (auto, inputs: PD)
Step 3: technical_architecture -> TA   (auto, inputs: PD, IP)
Step 4: work_package_creation  -> WP   (manual, inputs: PD, IP, TA)
Step 5: per_work_package       -> WS   (manual, inputs: WP entity, TA)
```

### Key Changes

- `primary_implementation_plan` doc type repurposed into `implementation_plan`. Single doc type carries: phasing, value sequencing, risk analysis, constraints, candidate WPs (advisory).
- `implementation_plan` no longer creates WP entities. Candidate WPs are output fields, not governed artifacts.
- New Step 4 (work_package_creation) runs after TA. Execution mode = manual. User initiates from WB.
- WP required_inputs includes technical_architecture + implementation_plan.
- POW steps carry execution_mode: "auto" (pipeline fires when inputs ready) or "manual" (user triggers from UI).

---

## Scope

### In Scope

1. **Consolidate IP document type:**
   - Repurpose primary_implementation_plan as the single implementation_plan
   - Merge schema: combine phasing/sequencing (from IPP) with risk/constraints/reconciliation (from IPF) and candidate WPs
   - Update package.yaml for the merged IP
   - Update IA definition for merged IP
   - Remove old IPF document type directory (or mark deprecated)
   - Update active_releases.json

2. **Fix POW definition.json:**
   - Remove primary_plan step
   - Update implementation_plan step to take only PD as input
   - Remove creates_entities from implementation_plan step
   - Update technical_architecture step to take PD + IP as inputs (not PD + IPP + IPF)
   - Add work_package_creation step after TA with execution_mode: manual
   - Add execution_mode: auto to PD, IP, TA steps
   - Add execution_mode: manual to per_work_package step
   - Update document_types section (remove primary_implementation_plan, update implementation_plan)
   - Update scopes section if needed

3. **Update WP package.yaml:**
   - Add technical_architecture to required_inputs
   - Verify implementation_plan is in required_inputs

4. **Update app code:**
   - primary_implementation_plan_handler.py -> merge into implementation_plan handler or remove
   - handler registry (app/domain/handlers/registry.py) -> remove primary_implementation_plan registration
   - DocumentNode.jsx -> remove primary_implementation_plan from DOC_TYPE_DISPLAY_NAMES

5. **Schema and prompt audit (documentation only):**
   - Audit IPP task prompt (prompts/tasks/primary_implementation_plan/)
   - Audit IPF task prompt (prompts/tasks/implementation_plan/)
   - Audit WP task prompt
   - Document what needs changing for follow-up WS-PIPELINE-004
   - Produce: docs/audits/WS-PIPELINE-001-prompt-audit.md

6. **Update tests:**
   - Update tests referencing primary_implementation_plan (9 test files)
   - Update tests referencing old POW step order

### Out of Scope

- Modifying LLM task prompts (audit only, changes go to WS-PIPELINE-004)
- Floor layout changes (WS-PIPELINE-002)
- Epic/feature/backlog removal (WS-PIPELINE-003)
- SPA rendering changes beyond DocumentNode display name fix

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

### POW Definition

1. No step produces primary_implementation_plan
2. implementation_plan step has no creates_entities field
3. work_package_creation step exists after technical_architecture
4. work_package_creation step inputs include technical_architecture
5. work_package_creation step inputs include implementation_plan
6. work_package_creation step has execution_mode: manual
7. Steps appear in order: discovery, implementation_plan, technical_architecture, work_package_creation, per_work_package
8. PD, IP, TA steps have execution_mode: auto
9. per_work_package step has execution_mode: manual
10. POW document_types section has no primary_implementation_plan entry

### Package Configs

11. No primary_implementation_plan directory in document_types (or marked deprecated)
12. implementation_plan package.yaml does not have creates_children: [work_package]
13. work_package package.yaml required_inputs includes technical_architecture
14. work_package package.yaml required_inputs includes implementation_plan
15. active_releases.json has no primary_implementation_plan in document_types
16. active_releases.json has no primary_implementation_plan in schemas

### App Code

17. No handler registration for primary_implementation_plan in registry.py
18. DocumentNode.jsx has no primary_implementation_plan in display names

### Schema

19. IP output schema has plan_summary (not epic_set_summary)
20. IP output schema has candidate_work_packages section

### Audit

21. Prompt audit report exists at docs/audits/WS-PIPELINE-001-prompt-audit.md

---

## Procedure

### Phase 1: Audit (Read-Only)

1. Read IPP output schema (primary_implementation_plan/schemas/output.schema.json)
2. Read IPF output schema (implementation_plan/schemas/output.schema.json)
3. Read IPP task prompt
4. Read IPF task prompt
5. Read WP task prompt
6. Catalog all fields, note old ontology terms (epic_set_summary, etc.)
7. Note instructions that reference old ordering or WP creation from IPF
8. Write audit report to docs/audits/WS-PIPELINE-001-prompt-audit.md

### Phase 2: Write Failing Tests

Write tests for criteria 1-21. Verify all fail.

### Phase 3: Implement Config Changes

1. Create merged IP schema:
   - Start from IPF schema (it has the richer structure)
   - Add phasing/sequencing fields from IPP
   - Rename epic_set_summary to plan_summary
   - Rename work_packages to candidate_work_packages
   - Remove any entity-spawning semantics from candidate_work_packages

2. Create merged IP package.yaml:
   - Combine IA sections from IPP and IPF
   - required_inputs: [project_discovery] only (no more IPP as input)
   - Remove creates_children: [work_package]
   - Update description

3. Update POW definition.json (see Target State above)

4. Update WP package.yaml:
   - required_inputs: [implementation_plan, technical_architecture]

5. Update active_releases.json:
   - Remove primary_implementation_plan from all sections
   - Remove primary_implementation_plan from workflows section

6. Update app code:
   - Remove or merge primary_implementation_plan_handler.py
   - Update handler registry
   - Update DocumentNode.jsx display names

7. Update test code:
   - Fix 9 test files referencing primary_implementation_plan

### Phase 4: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero
3. Prompt audit report is complete

---

## Prohibited Actions

- Do not modify LLM task prompt content (document needed changes in audit report)
- Do not modify floor layout or SPA components (except DocumentNode display name)
- Do not remove epic/feature/backlog references (that is WS-PIPELINE-003)
- Do not create new document types
- Do not modify TA inputs or schema (TA is correct, just needs IP instead of IPP+IPF)

---

## Expected Follow-Up Work

- **WS-PIPELINE-004**: Update task prompts to reflect merged IP and new pipeline ordering (based on audit report)
- **Tech debt**: IP task prompt needs to combine phasing + risk analysis + candidate WPs into single generation pass

---

_End of WS-PIPELINE-001_

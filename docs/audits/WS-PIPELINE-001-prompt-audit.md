# WS-PIPELINE-001 Prompt & Schema Audit

## Date: 2026-02-25

## Purpose

Catalog all prompt fragments and schemas that reference the two-step IPP/IPF model
or old ontology terms (epic/feature/story). This audit informs WS-PIPELINE-004
(prompt content updates). WS-PIPELINE-001 does NOT modify prompt content -- it only
restructures config, handlers, and the POW definition.

---

## Artifacts Audited

| # | File | Status |
|---|------|--------|
| 1 | IPP task prompt | Needs revision (WS-PIPELINE-004) |
| 2 | IPF task prompt | Absorbed into single IP (WS-PIPELINE-004) |
| 3 | IPP PGC context | Needs revision (WS-PIPELINE-004) |
| 4 | IPP QA prompt | Does not exist (TODO in package.yaml) |
| 5 | IPF PGC/QA prompts | Do not exist (null in package.yaml) |
| 6 | WP task prompt | Minor rename only |
| 7 | TA task prompt | Minor rename only |
| 8 | IPP output schema | Merge with IPF schema (WS-PIPELINE-001) |
| 9 | IPF output schema | Becomes unified schema (WS-PIPELINE-001) |
| 10 | POW definition.json | Restructure steps (WS-PIPELINE-001) |

---

## 1. IPP Task Prompt

**Path:** `combine-config/document_types/primary_implementation_plan/releases/1.0.0/prompts/task.prompt.txt`

**Old ontology references:**
- "MUST NOT: Decompose WP candidates into features, stories, tasks"
- "Stories, tasks, features, or implementation detail appear"
- "Epic candidates appear (output must use Work Package candidates only)"

**Two-step model references:**
- Frames candidates as "sufficient to guide downstream refinement without implying commitment"
- "not to create a delivery backlog"
- Implies IPF follows to reconcile candidates into committed WPs

**Action for WS-PIPELINE-004:**
- Remove "preliminary" / "not commitments" framing
- Remove epic/feature/story terminology
- Integrate reconciliation logic from IPF task prompt
- Output should produce committed WPs, not candidates

---

## 2. IPF Task Prompt

**Path:** `combine-config/document_types/implementation_plan/releases/1.0.0/prompts/task.prompt.txt`

**References to IPP as separate input:**
- "Produce the Final Implementation Plan by reconciling Primary Implementation Plan WP candidates"
- "Primary Implementation Plan - contains work_package_candidates[]"
- Full candidate-to-WP traceability rules (30+ lines)

**Old ontology references:**
- "Epic candidates or Epics appear (output must use Work Package candidates only)"

**Valuable content to preserve:**
- Candidate reconciliation rules (kept/split/merged/dropped)
- Referential consistency constraints (every candidate accounted for)
- Governance pinning structure (ta_version_id, adr_refs, policy_refs)

**Action for WS-PIPELINE-004:**
- Merge reconciliation rules into single IP task prompt
- Remove IPP as separate input reference
- Decide: keep candidate_reconciliation[] as inline audit trail or simplify

---

## 3. IPP PGC Context Prompt

**Path:** `combine-config/document_types/primary_implementation_plan/releases/1.0.0/prompts/pgc_context.prompt.txt`

**Two-step model references:**
- "will become committed Work Packages after architecture review via IPF reconciliation"
- "Commit to specific Work Packages (that happens via IPF reconciliation)"

**Action for WS-PIPELINE-004:**
- Remove IPF reconciliation references
- Update "Next Document" title
- Clarify WPs are committed in this step

---

## 4-5. IPP QA / IPF PGC / IPF QA Prompts

**Status:** Do not exist. IPP QA has a TODO comment. IPF has null for both.

**Action:** Create as part of WS-PIPELINE-004 if needed.

---

## 6. WP Task Prompt

**Path:** `combine-config/document_types/work_package/releases/1.0.0/prompts/task.prompt.txt`

**Minor references:**
- "Final Implementation Plan (IPF)"
- "Implementation Plan (Final) - the committed plan"

**Action for WS-PIPELINE-004:**
- Rename "Implementation Plan (Final)" to "Implementation Plan"
- Minimal change, no structural impact

---

## 7. TA Task Prompt

**Path:** `combine-config/document_types/technical_architecture/releases/1.0.0/prompts/task.prompt.txt`

**Minor references:**
- "Primary Implementation Plan (epic candidates and planning context)"

**Action for WS-PIPELINE-004:**
- Update to "Implementation Plan (Work Package candidates)"
- Minimal change

---

## 8. IPP Output Schema

**Path:** `combine-config/document_types/primary_implementation_plan/releases/1.0.0/schemas/output.schema.json`

**Fields requiring change (WS-PIPELINE-001 scope):**
- `epic_set_summary` -> rename to `plan_summary`
- `work_package_candidates[]` -> merge with IPF's `work_packages[]` structure
- `candidate_id` (WPC-\d format) -> align with wp_id (snake_case)
- Description: "Preliminary implementation plan" -> "Implementation Plan"
- Description: "Not yet commitments" -> remove

**Fields to preserve:**
- `risks_overview[]` (risk_id, description, affected_candidates, mitigation_direction)
- `recommendations_for_architecture[]`
- `associated_risks` computed field (handler transform)

---

## 9. IPF Output Schema

**Path:** `combine-config/document_types/implementation_plan/releases/1.0.0/schemas/output.schema.json`

**Structure (becomes the unified schema base):**
- `plan_summary` (overall_intent, mvp_definition, key_constraints, sequencing_rationale)
- `work_packages[]` with governance_pins, transformation, source_candidate_ids
- `candidate_reconciliation[]` (audit trail)
- `cross_cutting_concerns[]`
- `risk_summary[]`

**Decision point:** candidate_reconciliation[] and source_candidate_ids reference IPP candidates.
In single-IP model, these become internal consistency checks rather than cross-document references.
Recommend keeping the structure for auditability (ADR-009) but updating descriptions.

---

## 10. POW Definition

**Path:** `combine-config/workflows/software_product_development/releases/1.0.0/definition.json`

**Current steps:**
1. discovery -> project_discovery
2. primary_plan -> primary_implementation_plan (inputs: PD)
3. implementation_plan -> implementation_plan (inputs: PD, IPP) [creates_entities: work_package]
4. technical_architecture -> TA (inputs: PD, IPP, IPF)
5. per_work_package -> WS (inputs: WP, TA)

**Target steps (WS-PIPELINE-001):**
1. discovery -> project_discovery (auto)
2. implementation_plan -> implementation_plan (auto, inputs: PD)
3. technical_architecture -> TA (auto, inputs: PD, IP)
4. work_package_creation -> WP (manual, inputs: PD, IP, TA)
5. per_work_package -> WS (manual, inputs: WP, TA)

---

## Summary: What WS-PIPELINE-001 Changes vs What WS-PIPELINE-004 Changes

### WS-PIPELINE-001 (config/structure -- this WS):
- POW definition.json: merge steps, add execution_mode
- IPP output schema: rename epic_set_summary -> plan_summary, merge candidate fields
- IPP package.yaml: update IA sections, remove creates_children
- IPF package.yaml: deprecate or archive
- WP package.yaml: add technical_architecture to required_inputs
- active_releases.json: remove primary_implementation_plan
- Handler registry: remove primary_implementation_plan registration
- Handler code: merge associated_risks transform into implementation_plan handler

### WS-PIPELINE-004 (prompt content -- future WS):
- IPP task prompt: rewrite for single-IP model, remove epic references
- IPF task prompt: merge reconciliation rules into single task
- IPP PGC context: remove IPF reconciliation references
- WP task prompt: rename "Implementation Plan (Final)"
- TA task prompt: update input references
- Create QA prompt for IP (currently TODO)

---

_End of audit_

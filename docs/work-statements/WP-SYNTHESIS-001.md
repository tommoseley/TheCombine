# WP-SYNTHESIS-001 — Binder Synthesis: Composition Quality Step

**Status:** Draft
**Date:** 2026-04-07
**Governing ADR:** ADR-070 (Binder Synthesis)
**Priority:** NORMAL

## Objective

Implement the binder synthesis step: dual-instance analysis of a completed binder, mechanical comparison and classification of findings, structured delta output (actions + questions), and operator review UI. Synthesis runs once per binder version at project level, producing a governed delta artifact.

## Scope

### In Scope
- Synthesis workflow definition and prompt
- Synthesis action DSL schema (5 action types)
- Synthesis finding schema (4 question lenses)
- Dual-instance LLM execution and mechanical comparison
- Finding normalization and agreement scoring
- Mechanical/judgment lane classification
- Synthesis Delta persistence as governed artifact
- Operator review UI (accept/reject per finding)
- Wiring accepted actions to correction gate (ADR-069)

### Out of Scope
- Changes to existing DCW workflows (PGC, Generation, QA, Stabilize)
- Per-project configuration of action types or lenses
- Auto-execution of proposed actions
- Changes to existing evaluators (ADR-061, ADR-062, WS-EVAL-003)

## Dependencies
- ADR-070 accepted
- ADR-069 (Correction Gate) implemented — accepted actions route through corrections
- Binder renderer functional (provides input content)

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-SYNTHESIS-001 | Synthesis Action DSL and Finding Schemas | a0 |
| WS-SYNTHESIS-002 | Synthesis Analysis Prompt | a1 |
| WS-SYNTHESIS-003 | Dual-Instance Execution and Comparison | a2 |
| WS-SYNTHESIS-004 | Synthesis Delta Persistence and Operator UI | a3 |
| WS-SYNTHESIS-005 | Action Application via Correction Gate | a4 |

## Verification Criteria
- Synthesis runs on a complete binder and produces a Synthesis Delta
- Two independent LLM instances produce findings that are compared mechanically
- Actions conform to restricted DSL (5 types only, each with post-condition)
- Questions conform to lens schema (4 lenses only)
- Operator can accept/reject each finding independently
- Accepted actions produce correction briefs via ADR-069
- Tier 0 passes

## Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- combine-config/schemas/
- combine-config/workflows/
- combine-config/prompts/
- spa/src/
- tests/

## Definition of Done
- Synthesis step operational end-to-end on a real binder
- Dual-instance comparison produces meaningful agreement/disagreement signals
- Operator review UI functional
- All tests pass (Tier 0)

---

# WS-SYNTHESIS-001 — Synthesis Action DSL and Finding Schemas

## Purpose

Define the JSON schemas for the synthesis action DSL (5 action types with post-conditions) and the judgment finding schema (4 question lenses). These schemas govern what synthesis may produce and are the mechanical guardrails that prevent free-form LLM output.

## Governing References
- ADR-070 (Restricted Action Set, Judgment Questions)
- POL-WS-001

## Verification Mode
A

## Allowed Paths
- combine-config/schemas/synthesis/
- tests/tier1/config/

## Scope
### In Scope
- JSON Schema for synthesis actions: MERGE_WS, SPLIT_WS, DEFER_COMPONENT, REMOVE_WS, NORMALIZE_BOUNDARY
- JSON Schema for judgment questions: platform_realism, mvp_discipline, authority_hygiene, execution_readiness
- JSON Schema for the Synthesis Delta envelope (actions + questions + metadata)
- Validation tests: valid actions accepted, invalid actions rejected, unknown action types rejected

### Out of Scope
- LLM prompt design
- Execution logic
- UI components

## Preconditions
- ADR-070 accepted

## Procedure
1. Create `combine-config/schemas/synthesis/releases/1.0.0/` directory structure
2. Define `action.schema.json` with the 5 action types, each requiring action_type, targets, rationale, post_condition
3. Define `question.schema.json` with the 4 lenses, each requiring finding_id, lens, severity, artifacts, question, confidence
4. Define `synthesis_delta.schema.json` envelope containing actions array, questions array, and binder metadata
5. Add NORMALIZE_BOUNDARY constraint: may only reference scope_in, scope_out, allowed_paths, dependency fields — not objective, procedure, or definition_of_done
6. Write validation tests: valid action passes, missing post_condition rejected, unknown action_type rejected, unknown lens rejected
7. Run tests

## Verification Criteria
1. All 5 action types validate against schema
2. All 4 question lenses validate against schema
3. Unknown action types are rejected
4. Actions missing post_condition are rejected
5. NORMALIZE_BOUNDARY with prohibited fields (objective, procedure) is rejected
6. Synthesis Delta envelope validates with mixed actions and questions

## Definition of Done
- Schemas created, versioned, and tested
- Validation rejects invalid actions and unknown types

## Prohibited Actions
- Do not add action types beyond the 5 defined in ADR-070
- Do not add question lenses beyond the 4 defined in ADR-070
- Do not make schemas configurable per project

---

# WS-SYNTHESIS-002 — Synthesis Analysis Prompt

## Purpose

Create the governed prompt that instructs the LLM to analyze a complete binder and produce findings conforming to the action DSL and question schemas. This prompt is the primary control surface for synthesis quality.

## Governing References
- ADR-070 (Core Principles, Restricted Action Set, Judgment Questions)
- ADR-040 (Stateless Execution)
- POL-WS-001

## Verification Mode
A

## Allowed Paths
- combine-config/prompts/tasks/binder_synthesis/
- combine-config/document_types/synthesis_delta/
- tests/tier1/config/

## Scope
### In Scope
- Task prompt for binder synthesis analysis
- Role prompt reference (reuse existing quality_assurance role or define new)
- Document type package for synthesis_delta
- Prompt instructs: restricted action set, post-condition requirement, judgment-vs-mechanical classification
- Prompt self-check section mirroring WS/TA prompt patterns

### Out of Scope
- Execution infrastructure
- UI components
- Dual-instance comparison logic

## Preconditions
- WS-SYNTHESIS-001 complete (schemas exist for output validation)

## Procedure
1. Create `combine-config/prompts/tasks/binder_synthesis/releases/1.0.0/` with task prompt and meta.yaml
2. Prompt receives full binder content as input
3. Prompt specifies the 5 allowed action types with examples
4. Prompt specifies the 4 question lenses with examples
5. Prompt requires post-condition on every action; if LLM cannot produce one, emit as question instead
6. Prompt includes self-check: all actions have post-conditions, all questions have lens, no free-form recommendations
7. Prompt includes failure conditions: unknown action type, missing post-condition, action on prohibited fields
8. Create `combine-config/document_types/synthesis_delta/releases/1.0.0/package.yaml` referencing the schemas
9. Register in active_releases.json
10. Add registry integrity tests

## Verification Criteria
1. Prompt references correct schema versions
2. Prompt instructs restricted action set explicitly
3. Prompt failure conditions cover all ADR-070 restrictions
4. Document type package resolves through package loader
5. Registry integrity tests pass

## Definition of Done
- Synthesis analysis prompt created, versioned, and registered
- Document type package created for synthesis_delta
- Prompt enforces ADR-070 restrictions in self-check and failure conditions

## Prohibited Actions
- Do not allow free-form recommendations in the prompt
- Do not allow the prompt to propose actions outside the restricted set
- Do not embed project-specific context in the prompt

---

# WS-SYNTHESIS-003 — Dual-Instance Execution and Comparison

## Purpose

Implement the synthesis execution path: invoke two independent LLM instances on the same binder, collect findings, apply canonical normalization, score agreement, and classify findings into mechanical actions vs judgment questions.

## Governing References
- ADR-070 (Dual Instance, Scoped Memory, Finding Normalization)
- ADR-040 (Stateless Execution — scoped exception for structured state within synthesis)
- ADR-010 (LLM Execution Logging)
- POL-WS-001

## Verification Mode
A

## Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- tests/tier1/
- tests/tier2/

## Scope
### In Scope
- Synthesis service: orchestrates dual-instance execution
- Two independent LLM calls with full binder as input
- Finding normalization: canonical matching on artifact IDs and finding type
- Agreement scoring: both flagged (high), one flagged (moderate)
- Lane classification: action-type findings → mechanical lane, others → judgment lane
- Structured memory within synthesis step (findings from prior calls, not transcripts)
- LLM execution logging per ADR-010

### Out of Scope
- Persistence of the Synthesis Delta (WS-SYNTHESIS-004)
- Operator UI (WS-SYNTHESIS-004)
- Action application (WS-SYNTHESIS-005)
- Changes to existing task execution service

## Preconditions
- WS-SYNTHESIS-001 complete (schemas for validation)
- WS-SYNTHESIS-002 complete (prompt for LLM calls)

## Procedure
1. Create `app/domain/services/synthesis_service.py`
2. Implement `execute_synthesis(binder_content) -> SynthesisDelta`
3. Invoke LLM twice independently with the synthesis prompt and full binder content
4. Parse each response against synthesis action/question schemas
5. Implement finding normalization: match findings by artifact IDs and type
6. Score agreement: both → high confidence, one → moderate confidence
7. Classify: findings with valid action_type and post_condition → mechanical lane; others → judgment lane
8. Assemble SynthesisDelta from classified findings
9. Log both LLM invocations per ADR-010
10. Write tests: dual-instance produces independent results, normalization merges equivalent findings, classification routes correctly, schema-invalid responses are rejected

## Verification Criteria
1. Two independent LLM calls execute with the same prompt and binder
2. Findings are normalized before comparison
3. Agreement scoring correctly labels high/moderate confidence
4. Mechanical lane contains only findings with valid action_type and post_condition
5. Judgment lane contains findings without valid post_conditions
6. Schema-invalid LLM responses are rejected, not silently accepted
7. Both LLM calls are logged per ADR-010
8. Tests cover normalization, classification, and error paths

## Definition of Done
- Synthesis service executes dual-instance analysis and produces a classified SynthesisDelta
- Finding normalization and agreement scoring functional
- All tests pass

## Prohibited Actions
- Do not share context between the two LLM instances
- Do not pass transcripts between calls (structured findings only)
- Do not auto-execute any proposed actions
- Do not modify the existing task execution service

---

# WS-SYNTHESIS-004 — Synthesis Delta Persistence and Operator UI

## Purpose

Persist the Synthesis Delta as a governed artifact with lineage, and provide an operator review UI where each finding can be independently accepted, rejected, or modified.

## Governing References
- ADR-070 (Output Shape, Operator Decides)
- ADR-009 (Project Audit — state changes explicit and traceable)
- POL-WS-001

## Verification Mode
A

## Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- spa/src/
- tests/

## Scope
### In Scope
- API endpoint: POST synthesis execution trigger
- API endpoint: GET synthesis delta for a project
- Synthesis Delta stored as a governed document with lineage
- SPA component: display synthesis delta (actions and questions separately)
- SPA component: accept/reject/modify controls per finding
- Accepted findings persisted with operator decision audit trail

### Out of Scope
- Synthesis execution logic (WS-SYNTHESIS-003)
- Action application logic (WS-SYNTHESIS-005)

## Preconditions
- WS-SYNTHESIS-003 complete (synthesis service produces SynthesisDelta)

## Procedure
1. Add API endpoint: `POST /api/v1/projects/{project_id}/synthesis` — triggers synthesis execution
2. Add API endpoint: `GET /api/v1/projects/{project_id}/synthesis` — returns latest Synthesis Delta
3. Add API endpoint: `PATCH /api/v1/projects/{project_id}/synthesis/findings/{finding_id}` — operator decision (accept/reject/modify)
4. Persist Synthesis Delta as document with doc_type_id `synthesis_delta`
5. Record operator decisions with timestamps and rationale
6. Create SPA SynthesisReview component: two-lane display (actions | questions)
7. Each finding shows: type, targets, rationale, confidence, post-condition (for actions) or question (for judgment)
8. Accept/reject buttons per finding with optional operator note
9. Wire trigger button into binder view (run synthesis after binder is assembled)
10. Write tests: API endpoints, persistence, operator decision recording

## Verification Criteria
1. Synthesis can be triggered via API and produces a persisted delta
2. Delta is retrievable via GET endpoint
3. Operator can accept/reject individual findings
4. Decisions are persisted with audit trail
5. SPA displays actions and questions in separate lanes
6. Tests cover API, persistence, and decision recording

## Definition of Done
- Synthesis Delta persisted as governed artifact
- Operator review UI functional with per-finding accept/reject
- Audit trail for all operator decisions

## Prohibited Actions
- Do not auto-accept any findings
- Do not allow synthesis to modify documents directly
- Do not skip audit trail for operator decisions

---

# WS-SYNTHESIS-005 — Action Application via Correction Gate

## Purpose

Wire accepted mechanical actions back into the pipeline as correction briefs (ADR-069), enabling the operator to apply synthesis findings by rewinding and regenerating with the correction encoded as a binding constraint.

## Governing References
- ADR-070 (Action Application)
- ADR-069 (Correction Gate — corrections become authority records)
- POL-WS-001

## Verification Mode
A

## Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- tests/

## Scope
### In Scope
- Convert accepted MERGE_WS action to correction brief targeting WS stage
- Convert accepted SPLIT_WS action to correction brief targeting WS stage
- Convert accepted DEFER_COMPONENT action to correction brief targeting TA stage
- Convert accepted REMOVE_WS action to correction brief targeting WS stage
- Convert accepted NORMALIZE_BOUNDARY action to correction brief targeting WS stage
- Apply correction via existing rewind + correction gate (ADR-069)
- Post-condition verification after regeneration

### Out of Scope
- Direct document mutation (all changes go through correction gate)
- Changes to the correction gate itself
- Changes to the rewind mechanism

## Preconditions
- WS-SYNTHESIS-004 complete (operator has accepted findings)
- ADR-069 correction gate functional

## Procedure
1. Create `app/domain/services/synthesis_action_applier.py`
2. Implement action-to-correction mapping for each of the 5 action types
3. MERGE_WS → correction brief: "Merge WS-X and WS-Y into a single WS covering [combined scope]" targeting WS stage
4. SPLIT_WS → correction brief: "Split WS-X into N separate WSs: [scope descriptions]" targeting WS stage
5. DEFER_COMPONENT → correction brief: "Mark component X as deferred in mvp_scope.deferred" targeting TA stage
6. REMOVE_WS → correction brief: "Remove WS-X — [rationale]" targeting WS stage
7. NORMALIZE_BOUNDARY → correction brief: "Adjust scope boundaries: [specific field changes]" targeting WS stage
8. Wire to rewind endpoint with correction brief and applies_to_stages
9. After regeneration, verify post-conditions from the original action
10. Report post-condition verification results to operator
11. Write tests: each action type produces correct correction brief, post-condition checking works

## Verification Criteria
1. Each of the 5 action types maps to a well-formed correction brief
2. Correction briefs target the correct pipeline stage
3. Corrections are persisted as authority records (ADR-069)
4. Post-conditions from the original action can be checked against regenerated output
5. Post-condition verification results are reported to operator
6. Tests cover all 5 action types

## Definition of Done
- All 5 action types convert to correction briefs and apply through the correction gate
- Post-condition verification operational
- All tests pass

## Prohibited Actions
- Do not mutate documents directly — all changes go through correction gate
- Do not bypass the rewind mechanism
- Do not auto-apply corrections without operator acceptance

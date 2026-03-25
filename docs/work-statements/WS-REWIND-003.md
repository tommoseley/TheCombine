# WS-REWIND-003 — Linear Rewind Impact Evaluator

**Status:** Draft
**Parent WP:** WP-REWIND-001
**Governing ADR:** ADR-063

## Objective

Given a rewind trigger at stage N, determine the complete invalidation set using the linear dependency model: everything at N and after becomes stale.

## Scope

### In Scope
- Pure function: `evaluate_rewind_impact(rewind_stage) → list[PipelineStage]`
- Uses canonical stage model from WS-REWIND-001
- Returns all stages at and downstream of the rewind point
- Document query: given a project_id and list of affected stages, return all document IDs that will be marked stale

### Out of Scope
- Actually marking documents stale (WS-REWIND-004)
- Fine-grained dependency graphs
- Automatic trigger detection

## Procedure

### Step 1: Implement impact evaluator
- Create `app/domain/services/rewind_impact_evaluator.py`
- `evaluate_rewind_impact(rewind_stage: PipelineStage) → list[PipelineStage]`
  - Returns `[rewind_stage] + rewind_stage.downstream_stages()`
- `get_affected_documents(project_id: UUID, affected_stages: list[PipelineStage], db) → list[UUID]`
  - Query documents table for current documents at affected stages
  - Map stage to doc_type_id using PipelineStage.doc_type_id

### Step 2: Handle conservative default
- If `rewind_stage` is ambiguous or unknown, default to CI (earliest stage)
- Log a warning when conservative default is used

### Step 3: Write tests
- Test: rewind at TA → [TA, IP, WP, WS]
- Test: rewind at CI → [CI, PD, TA, IP, WP, WS] (full pipeline)
- Test: rewind at WS → [WS] (terminal stage)
- Test: conservative default when stage is invalid

## Verification Criteria
- Impact evaluator correctly identifies all downstream stages
- Document query returns correct IDs for affected stages
- Conservative default works for ambiguous input
- Pure function with no side effects
- Tests pass

## Allowed Paths
- app/domain/services/rewind_impact_evaluator.py
- tests/tier1/test_rewind_impact_evaluator.py

## Prohibited Actions
- Do not mark documents stale (that's WS-REWIND-004)
- Do not implement dependency graphs
- Do not query or modify document content

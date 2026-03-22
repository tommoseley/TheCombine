# WS-REWIND-001 — Canonical Pipeline Stage Model

**Status:** Draft
**Parent WP:** WP-REWIND-001
**Governing ADR:** ADR-063

## Objective

Define and implement the authoritative pipeline stage enum and ordering used by all rewind, invalidation, and regeneration logic.

## Scope

### In Scope
- Python enum defining canonical stages: CI, PD, TA, IP, WP, WS
- Stage ordering function (given two stages, which is upstream?)
- Encoding that PGC is cross-cutting and NOT a rewind target
- Stage metadata: doc_type_id mapping per stage

### Out of Scope
- Rewind logic (WS-REWIND-003/004)
- Status model (WS-REWIND-002)
- UI representation

## Procedure

### Step 1: Create pipeline stage enum
- Create `app/domain/models/pipeline_stage.py`
- Define `PipelineStage` enum with ordered members: CI, PD, TA, IP, WP, WS
- Add `doc_type_id` property mapping each stage to its document type
- Add `is_downstream_of(other)` comparison method
- Add `downstream_stages()` returning all stages after this one

### Step 2: Add PGC guard
- `PGC` must not appear in the enum
- Add explicit docstring: "PGC is cross-cutting, not a rewind target"

### Step 3: Write tests
- Test ordering: PD is downstream of CI, WS is downstream of all
- Test downstream_stages: TA.downstream_stages() == [IP, WP, WS]
- Test doc_type_id mapping
- Test that PGC is not a valid stage

## Verification Criteria
- Enum defines exactly 6 stages in correct order
- Ordering comparisons are correct
- downstream_stages() returns correct sets
- PGC is not representable as a pipeline stage
- Tests pass

## Allowed Paths
- app/domain/models/pipeline_stage.py
- tests/tier1/test_pipeline_stage.py

## Prohibited Actions
- Do not add PGC as a stage
- Do not implement rewind logic in this WS
- Do not modify existing models

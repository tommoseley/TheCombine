# WS-BCP-004: Backlog Compilation Pipeline — End-to-End Integration & Observability

## Status: Draft

## Purpose

Wire the full Backlog Compilation Pipeline end-to-end: a single API call that triggers the complete sequence from IntentPacket through validated, ordered ExecutionPlan with human-readable explanation. Add replay metadata for determinism verification.

This is the fourth and final work statement. WS-BCP-001 delivered schemas and backlog generation. WS-BCP-002 delivered graph validation and ordering. WS-BCP-003 delivered the explanation generator. This work statement integrates them into a single pipeline and adds observability.

## Governing References

- **Backlog Compilation Pipeline Implementation Plan** (`docs/implementation-plans/BACKLOG-COMPILATION-PIPELINE-Implementation-Plan.md`)
- **WS-BCP-001** (complete): Foundation — schemas, intent intake, backlog generator DCW
- **WS-BCP-002** (complete): Graph validation, ordering engine, ExecutionPlan derivation
- **WS-BCP-003** (complete): Plan Explanation Generator DCW
- **ADR-009**: Project Audit (all state changes explicit and traceable)
- **ADR-010**: LLM Execution Logging (inputs, outputs, replay capability)
- **ADR-040**: Stateless LLM Execution
- **DQ-2**: Fail-fast in graph layer, no self-heal
- **DQ-3**: Waves derived, non-authoritative; total order authoritative

## Scope

### In Scope

- **Task 9**: Pipeline integration service — orchestrates the full BCP sequence
- **Task 10**: Replay metadata — stored with every pipeline run for determinism verification
- API endpoint: `POST /api/v1/backlog-pipeline/run` — triggers full pipeline from intent_id
- API endpoint: `GET /api/v1/backlog-pipeline/runs/{run_id}` — retrieves run result and metadata
- Mechanical execution_plan step (graph validation + derivation, no DCW — pure function)
- `backlog_hash` deduplication — if existing plan matches, return it instead of re-deriving
- Pipeline run document type (`pipeline_run`) for storing run metadata and replay hashes
- Structured error responses with error bucket (dependency / hierarchy / cycle / generation_failed)
- Tier-1 tests for pipeline service logic

### Out of Scope

- Auto-regeneration loops (re-prompt LLM on graph validation failure) — future work
- Pipeline run history UI or dashboard — future work
- Backlog editing or dependency editing UI — explicit non-goal
- Retry/resume of partial pipeline runs — future work (pipeline runs are atomic)
- Integration with the existing ProjectOrchestrator full-line run — future work (BCP is a standalone pipeline for now)
- SPA pages for pipeline triggering or result display — future work

## Preconditions

1. WS-BCP-001 complete: `intent_packet` document type, `IntentPacketHandler`, `/intents` API
2. WS-BCP-002 complete: `graph_validator.validate_backlog()`, `backlog_ordering.derive_execution_plan()`, `execution_plan` document type
3. WS-BCP-003 complete: `plan_explanation` DCW and handler
4. PlanExecutor can run DCWs (backlog_generator, plan_explanation) to completion
5. All document handlers registered in registry

---

## Phase 1: Pipeline Service

**Objective:** Create the domain service that orchestrates the full BCP sequence. This is the core integration logic.

### Step 1.1: Create pipeline service

**File:** `app/domain/services/backlog_pipeline.py`

```python
class BacklogPipelineService:
    """
    Orchestrates the full Backlog Compilation Pipeline.

    Sequence:
    1. Load IntentPacket by intent_id
    2. Run Backlog Generator DCW → BacklogItemList
    3. Validate graph (dependency, hierarchy, cycles) — fail hard
    4. Derive ExecutionPlan (mechanical) — check backlog_hash for dedup
    5. Run Plan Explanation DCW (optional)
    6. Store pipeline_run metadata

    All steps produce documents. Failure at any stage halts downstream.
    """
```

#### Pipeline sequence (detailed)

**Step 1: Load IntentPacket**
- Query `documents` table for `intent_id` (doc_type_id='intent_packet', is_latest=True)
- Fail if not found: `{"status": "failed", "error": "intent_not_found"}`

**Step 2: Run Backlog Generator DCW**
- Use PlanExecutor to start and run the `backlog_generator` workflow
- Pass IntentPacket content as initial context (`input_documents.intent_packet`)
- Wait for terminal outcome
- If `blocked`: return `{"status": "failed", "stage": "generation", "error": "backlog_generation_failed"}`
- If `stabilized`: extract the produced BacklogItemList content from the document

**Step 3: Validate graph**
- Call `validate_backlog(items)` from `graph_validator.py`
- If not valid, return structured error response:
  ```python
  {
      "status": "failed",
      "stage": "validation",
      "dependency_errors": [...],   # From validate_dependencies
      "hierarchy_errors": [...],    # From validate_hierarchy
      "cycle_traces": [...],        # From detect_dependency_cycles
  }
  ```
- Error bucket is explicit — caller knows exactly what failed and in which bucket

**Step 4: Derive ExecutionPlan**
- Call `derive_execution_plan(items, intent_id, run_id)` from `backlog_ordering.py`
- Check if `backlog_hash` already exists as an `execution_plan` document for this project
  - If yes: return existing plan (no re-derivation)
  - If no: persist as new `execution_plan` document
- This step is mechanical — no LLM, no DCW

**Step 5: Run Plan Explanation DCW (optional)**
- Use PlanExecutor to start and run the `plan_explanation` workflow
- Pass execution plan + backlog items as initial context
- If `blocked`: log warning but don't fail the pipeline — explanation is optional
- If `stabilized`: explanation document persisted

**Step 6: Store pipeline run metadata**
- Persist `pipeline_run` document with replay hashes (see Phase 3)

#### Return value

```python
@dataclass
class PipelineResult:
    status: str          # "completed" | "failed"
    run_id: str          # Unique pipeline run identifier
    stage: str           # Last completed stage (or stage that failed)
    intent_id: str
    backlog_hash: str | None
    plan_id: str | None  # execution_plan document ID
    explanation_id: str | None  # plan_explanation document ID (may be None)
    errors: dict | None  # Structured errors if failed
    metadata: dict       # Replay metadata (Task 10)
```

### Step 1.2: Create pipeline result types

Define the structured result and error types as dataclasses in the same module. Keep them simple — these are data transfer objects, not domain entities.

**Verification:**

- Pipeline runs end-to-end when all steps succeed
- Pipeline halts at step 2 if backlog generation fails (blocked)
- Pipeline halts at step 3 with structured errors if graph validation fails
- Pipeline completes even if explanation fails (step 5 is optional)
- backlog_hash deduplication works: same structural backlog → same execution plan returned
- Each step's output is persisted as a document before the next step runs

---

## Phase 2: API Endpoints

**Objective:** Expose the pipeline via REST API.

### Step 2.1: Create pipeline router

**File:** `app/api/v1/routers/backlog_pipeline.py`

**`POST /api/v1/backlog-pipeline/run`**

Request body:
```json
{
  "project_id": "uuid",
  "intent_id": "uuid",
  "skip_explanation": false
}
```

Response (success):
```json
{
  "status": "completed",
  "run_id": "run-xxxxxxxxxxxx",
  "intent_id": "uuid",
  "backlog_hash": "abc123...",
  "plan_id": "uuid",
  "explanation_id": "uuid",
  "metadata": {
    "intent_hash": "...",
    "backlog_hash": "...",
    "plan_hash": "...",
    "prompt_version": "1.0.0",
    "generator_version": "1.0.0"
  }
}
```

Response (validation failure):
```json
{
  "status": "failed",
  "run_id": "run-xxxxxxxxxxxx",
  "stage": "validation",
  "dependency_errors": [
    {"item_id": "F003", "error_type": "missing_reference", "detail": "..."}
  ],
  "hierarchy_errors": [],
  "cycle_traces": []
}
```

**`GET /api/v1/backlog-pipeline/runs/{run_id}`**

Returns the pipeline_run document content — full metadata and result.

### Step 2.2: Register router

**File:** `app/api/v1/__init__.py`

Mount the pipeline router.

**Verification:**

- `POST /backlog-pipeline/run` with valid intent_id triggers full pipeline
- `POST /backlog-pipeline/run` with invalid intent_id returns 404
- `POST /backlog-pipeline/run` with skip_explanation=true skips step 5
- `GET /backlog-pipeline/runs/{run_id}` returns stored metadata
- Error responses include structured error buckets

---

## Phase 3: Pipeline Run Metadata & Replay (Task 10)

**Objective:** Store replay metadata with every pipeline run for determinism verification.

### Step 3.1: Create pipeline_run schema

**File:** `combine-config/schemas/pipeline_run/releases/1.0.0/schema.json`

```json
{
  "type": "object",
  "required": ["run_id", "intent_id", "status", "stages", "replay_metadata"],
  "properties": {
    "run_id": { "type": "string" },
    "intent_id": { "type": "string" },
    "status": { "type": "string", "enum": ["completed", "failed"] },
    "stage_reached": { "type": "string" },
    "stages": {
      "type": "object",
      "description": "Per-stage timing and outcome",
      "properties": {
        "generation": { "$ref": "#/$defs/stage_result" },
        "validation": { "$ref": "#/$defs/stage_result" },
        "derivation": { "$ref": "#/$defs/stage_result" },
        "explanation": { "$ref": "#/$defs/stage_result" }
      }
    },
    "replay_metadata": {
      "type": "object",
      "required": ["intent_hash", "backlog_hash", "generator_version"],
      "properties": {
        "intent_hash": { "type": "string", "description": "SHA-256 of IntentPacket content" },
        "backlog_hash": { "type": ["string", "null"], "description": "SHA-256 of structural backlog fields" },
        "plan_hash": { "type": ["string", "null"], "description": "SHA-256 of ordered_backlog_ids + waves" },
        "prompt_version": { "type": "string" },
        "model_version": { "type": ["string", "null"] },
        "generator_version": { "type": "string" }
      }
    },
    "errors": {
      "type": ["object", "null"],
      "description": "Structured errors if pipeline failed"
    }
  }
}
```

### Step 3.2: Create document type and handler

**File:** `combine-config/document_types/pipeline_run/releases/1.0.0/package.yaml`

```yaml
doc_type_id: pipeline_run
display_name: Pipeline Run
version: 1.0.0
description: >
  Metadata record for a Backlog Compilation Pipeline run.
  Stores replay hashes, per-stage results, and timing.
  Used for determinism verification.
authority_level: descriptive
creation_mode: constructed
production_mode: construct
scope: project
```

**File:** `app/domain/handlers/pipeline_run_handler.py`

Minimal handler — renders run metadata, stage results, and replay hashes.

### Step 3.3: Create database migration

**File:** `alembic/versions/YYYYMMDD_NNN_add_pipeline_run_document_type.py`

```sql
INSERT INTO document_types (doc_type_id, display_name, cardinality, instance_key)
VALUES ('pipeline_run', 'Pipeline Run', 'multi', 'run_id');
```

Note: `pipeline_run` is multi-instance keyed by `run_id` — each pipeline execution produces a separate record.

### Step 3.4: Implement replay hash computation

**Functions in `app/domain/services/backlog_pipeline.py`:**

```python
def compute_intent_hash(intent_content: dict) -> str:
    """SHA-256 of canonical JSON of intent content."""

def compute_plan_hash(ordered_ids: list[str], waves: list[list[str]]) -> str:
    """SHA-256 of ordered_backlog_ids + waves (canonical JSON)."""
```

These hashes enable determinism verification:
- Same `intent_hash` + same `backlog_hash` should produce same `plan_hash`
- If a replay produces a different `backlog_hash`, the LLM generated a structurally different backlog
- If same `backlog_hash` but different `plan_hash` — ordering engine bug (should never happen)

### Step 3.5: Update active_releases.json

Add `pipeline_run` to document_types and schemas.

**Verification:**

- Every pipeline run (success or failure) produces a `pipeline_run` document
- Replay metadata includes all required hashes
- Same intent content → same `intent_hash`
- Same structural backlog → same `backlog_hash` → same `plan_hash`
- Hash mismatch detection is possible by comparing replay_metadata across runs

---

## Phase 4: Unit Tests

**Objective:** Tier-1 tests for the pipeline service and hash functions. Pipeline integration tests use mocked PlanExecutor (no real LLM calls).

### Step 4.1: Pipeline service tests

**File:** `tests/tier1/services/test_backlog_pipeline.py`

Tests with mocked PlanExecutor:
- Happy path: all steps succeed → PipelineResult(status="completed")
- Generation failure: DCW returns blocked → PipelineResult(status="failed", stage="generation")
- Validation failure: graph validator returns errors → structured error response
- Explanation failure: DCW returns blocked → pipeline still completes (explanation optional)
- backlog_hash dedup: same hash → existing plan returned, no re-derivation
- Intent not found → PipelineResult(status="failed", error="intent_not_found")

### Step 4.2: Hash function tests

**File:** `tests/tier1/services/test_backlog_pipeline.py` (same file)

- `compute_intent_hash`: same content → same hash; different content → different hash
- `compute_plan_hash`: same ordered_ids + waves → same hash; deterministic
- Replay invariant: derive_execution_plan output → compute_plan_hash → stable across runs

**Verification:**

- All tests are tier-1 (mocked dependencies, no DB, no LLM)
- Pipeline failure modes tested explicitly
- Hash determinism verified
- `python -m pytest tests/tier1/services/test_backlog_pipeline.py -v` — all pass
- Full suite passes: `python -m pytest tests/ -x -q`

---

## Prohibited Actions

- Do not silently correct graph validation errors — fail hard, return all errors with bucket
- Do not allow the pipeline to continue past a failed validation step
- Do not use LLM for ordering, wave grouping, or plan derivation — mechanical only
- Do not store replay metadata inside the ExecutionPlan document — separate `pipeline_run` document
- Do not integrate with ProjectOrchestrator full-line run yet — BCP is standalone for now
- Do not build pipeline run history UI or retry/resume capability
- Do not modify graph validation or ordering logic — those are complete (WS-BCP-002)
- Do not modify DCW definitions — those are complete (WS-BCP-001, WS-BCP-003)

## Verification Checklist

1. **Pipeline runs end-to-end:** Valid intent → backlog → validation → plan → explanation → pipeline_run metadata
2. **Generation failure halts:** DCW blocked → pipeline fails with stage="generation"
3. **Validation failure halts:** Graph errors → pipeline fails with structured error buckets
4. **Explanation failure doesn't halt:** Blocked explanation → pipeline still completes
5. **backlog_hash dedup works:** Same structural backlog → existing plan returned
6. **Replay metadata stored:** Every run produces pipeline_run document with all hashes
7. **Hash determinism:** Same intent → same intent_hash; same structure → same backlog_hash → same plan_hash
8. **API endpoints work:** POST triggers pipeline; GET retrieves run metadata
9. **Error responses structured:** Dependency/hierarchy/cycle errors in separate buckets
10. **Router registered:** Pipeline router mounted in v1 API
11. **Document types registered:** pipeline_run in DB and active_releases.json
12. **All tests pass:** `python -m pytest tests/ -x -q` — no regressions

## Definition of Done

- `BacklogPipelineService` orchestrates the full sequence: intent → backlog → validate → plan → explain → metadata
- Pipeline halts on generation or validation failure with structured errors
- Pipeline completes even if explanation fails (optional step)
- backlog_hash deduplication prevents redundant plan derivation
- `POST /backlog-pipeline/run` triggers the pipeline; `GET /backlog-pipeline/runs/{run_id}` retrieves results
- `pipeline_run` documents store replay metadata (intent_hash, backlog_hash, plan_hash, versions)
- Replay invariant testable: same inputs → same hashes
- All new code covered by tier-1 tests with mocked LLM dependencies
- All existing tests continue to pass
- The Backlog Compilation Pipeline is a real, working product capability

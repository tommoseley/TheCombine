# WP-WB-002: Work Binder — LLM Proposal Station Primitive (WS Draft Generation)

## Intent

Introduce the first governed LLM-driven station inside the Work Binder: **Propose Work Statements**.

This requires establishing reusable platform primitives (document readiness gating, task execution outside the workflow engine, schema alignment) so we don't create a one-off "LLM call in a router" anti-pattern.

## Scope In

- Define a **mechanical** readiness gate for "TA is ready for downstream consumption"
- Ensure **schema/code alignment** for WP `ws_index[]` (no phantom fields)
- Implement a reusable **Task Execution Primitive** callable from WB services/routers that:
  - loads certified task prompts
  - executes LLM calls under ADR-010 logging expectations
  - validates output against JSON schema before persistence
- Add governed WB endpoint + SPA flow to propose WS drafts:
  - explicit operator trigger
  - DRAFT-only WS artifacts
  - no silent destruction / no overwrite of existing WSs
  - full audit events

## Scope Out

- No automatic WS proposal during WP promotion
- No background jobs / agent loops / auto-regeneration
- No "force_regenerate" behavior
- No stabilization automation (operator stabilizes WS separately)
- No broad "document lifecycle redesign" beyond what's needed to define readiness checks

## Dependencies

- Existing WP/WPC/WS doc types and handlers (post WP-WB-001)
- Active releases / registry plumbing already in place

---

# Work Statements

## WS-WB-020: Define Mechanical Document Readiness Gate for TA Consumption

### Problem
"TA stabilized" is ambiguous in current model (status vs lifecycle_state). We need a deterministic condition for "TA can be used as binding input".

### Deliverable
A single, testable predicate used by WB and future stations.

### Requirements
- Implement `is_doc_ready_for_downstream(doc)` (or TA-specific variant) with explicit rules.
- Rules must use fields that actually exist in the document model.
- Add Tier-1 tests covering:
  - ready state
  - draft/active/stale/archived combinations as applicable
  - missing fields behavior (hard fail vs not-ready)

### Acceptance
- Predicate is used by WB propose station gate (later WS)
- Tests prove semantics and prevent regressions

---

## WS-WB-021: Fix WP Schema Drift — Declare ws_index[] and Version Bump

### Problem
Code relies on `ws_index[]` but schema may not declare it (phantom field risk). IA verification should pass.

### Deliverables
- Update global WP schema to include `ws_index[]` with the correct shape
- Bump schema release version as required
- Add schema tests confirming:
  - `ws_index[]` is allowed and validated
  - additionalProperties:false is preserved

### Acceptance
- IA verification passes for WP doc type
- No runtime writes of undeclared fields remain

---

## WS-WB-022: Implement Task Execution Primitive for Non-Workflow Call Sites

### Problem
We cannot let routers invent their own prompt loading / logging / validation path. We need a reusable service primitive.

### Deliverables
Create a small service module, e.g.:
- `app/domain/services/task_execution_service.py`

With a function like:
- `execute_task(task_id, version, inputs, expected_schema_id) -> dict`

### Requirements
- Uses certified prompt loading convention (from combine-config task path)
- Centralizes:
  - prompt resolution
  - LLM invocation
  - ADR-010-aligned logging hooks (whatever your system uses today)
  - output JSON parsing
  - schema validation before returning
- Tier-1 tests:
  - missing prompt → hard fail
  - invalid JSON → hard fail
  - schema violation → hard fail
  - happy path with stubbed LLM client → returns validated output

### Acceptance
- WB propose endpoint (later WS) uses this service, not inline prompt handling
- No duplicate prompt-loading logic added to routers

---

## WS-WB-023: Add Dedicated Task Prompt — propose_work_statements@1.0.0

### Deliverables
- `combine-config/prompts/tasks/propose_work_statements/releases/1.0.0/task.prompt.txt`
- `meta.yaml`
- active release registration as needed

### Requirements
- Inputs explicitly limited: WP + TA (and only declared optional context)
- Output shape: list of WS JSON objects conforming to work_statement schema
- Must produce DRAFT-ready artifacts (no claims of execution)
- Must not emit WP fields or mutate ws_index
- No ambiguity: this is the only prompt used by the propose station

### Acceptance
- Task resolves through the task execution primitive (WS-WB-022)
- Schema validation passes for typical outputs in test harness

---

## WS-WB-024: Audit Events for Proposal Station

### Deliverables
- Add event types and structured payload definitions to WB audit service:
  - `WB_WS_PROPOSAL_REQUESTED`
  - `WB_WS_PROPOSAL_REJECTED` (gate failures)
  - `WB_WS_PROPOSED` (per WS persisted)
  - `WB_WP_WS_INDEX_UPDATED`

### Requirements
- Events emitted for all mutation paths and for rejection paths
- Tier-1 tests assert audit events are written

### Acceptance
- Every propose run is reconstructible from audit stream

---

## WS-WB-025: Propose WS Endpoint + SPA Wiring (DRAFT-Only)

### Backend
Add `POST /work-binder/propose-ws`

#### Gate rules (mechanical)
- TA must satisfy readiness predicate (WS-WB-020)
- WP must have empty ws_index
- If ws_index non-empty → HARD_STOP (no mutation)
- If ws_index has dangling refs (shouldn't happen, but check) → HARD_STOP

#### Behavior
- Call task execution primitive with:
  - task_id: `propose_work_statements`, version: `1.0.0` (separate args)
  - inputs: WP + TA
  - expected_schema_id: `work_statement`
- Persist WS docs as DRAFT
- Update WP ws_index in new WP edition (WP-level bump)
- Emit audit events (WS-WB-024)

### SPA
- Add "PROPOSE STATEMENTS" button for eligible promoted WPs
- Display WS drafts in list with DRAFT state clearly visible
- Handle HARD_STOP responses with non-chatty error UI

### Acceptance
- Happy path creates WS drafts, updates ws_index, emits audit events
- Failure paths do not mutate anything
- Tier-1 tests cover all gates and the happy path
- SPA builds clean

---

## Definition of Done

- All WSs completed with Tier-1 tests passing
- No router-level ad hoc LLM execution remains
- Readiness gate is defined once and reused
- Schema/handler alignment verified (IA verification passes)
- Propose station is explicit, DRAFT-only, and auditable

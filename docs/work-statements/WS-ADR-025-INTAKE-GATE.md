# WS-ADR-025: Intake Gate Implementation

**Status:** Draft
**Date:** 2026-01-17
**Related ADRs:** ADR-025 (Intake Gate), ADR-026 (Concierge Role), ADR-038 (Workflow Plan Schema), ADR-039 (Document Interaction Workflow Model)
**Depends On:** WS-INTAKE-ENGINE-001 (Complete)

---

## 1. Objective

Implement the Concierge Intake Gate (ADR-025) using the Document Interaction Workflow Engine (ADR-039, WS-INTAKE-ENGINE-001).

This work statement connects the existing workflow engine to real LLM executors and integrates it with the Concierge UI to create a governed intake boundary.

This Work Statement relies on ADR-026 to constrain Concierge behavior to advisory and option-selection roles only. The Concierge facilitates clarity; it does not route, decide, or bypass governance gates.

---

## 2. Current State

### What Exists

| Component | Status | Location |
|-----------|--------|----------|
| Workflow Engine | Complete | `app/domain/workflow/` |
| PostgreSQL Persistence | Complete | `app/domain/workflow/pg_state_persistence.py` |
| Workflow Plan | Complete | `seed/workflows/concierge_intake.v1.json` |
| API Endpoints | Complete | `app/api/v1/routers/document_workflows.py` |
| Concierge UI | Exists (separate flow) | `app/api/routers/concierge_routes.py` |
| Task Prompts | Exist | `seed/prompts/tasks/Concierge Intake v1.0.txt`, `Concierge Intent Reflection v1.0.txt` |
| Mock Executors | In use | `app/domain/workflow/nodes/mock_executors.py` |

### Gap Analysis

1. **Mock Executors** - Workflow engine uses mocks, not real LLM calls
2. **Separate Systems** - Concierge UI uses `concierge_intake_session` tables, not workflow engine
3. **No Artifact Schema** - Concierge Intake Document schema not registered
4. **No Dual Outcome** - Gate outcome vs terminal outcome not recorded together

---

## 3. Scope

### In Scope

1. Real LLM executors for workflow nodes
2. Concierge UI integration with workflow engine
3. Concierge Intake Document artifact schema
4. Dual outcome recording (governance + execution)
5. Thread ownership (conversation persistence)

### Out of Scope

- New UI design (reuse existing Concierge UI patterns)
- Additional workflow plans (Discovery, Epic, etc.)
- Workflow visualization/management UI
- Multi-entry workflow support

---

## 4. Implementation Phases

### Phase 1: LLM Node Executors

Replace mock executors with real LLM integration.

**Deliverables:**

| File | Purpose |
|------|---------|
| `app/domain/workflow/nodes/llm_task_executor.py` | Real LLM task execution |
| `app/domain/workflow/nodes/llm_concierge_executor.py` | Concierge conversation with LLM |
| `app/domain/workflow/nodes/llm_qa_executor.py` | QA validation via LLM |

**Key Requirements:**

- Load task prompts from `role_tasks` table (seeded from `seed/prompts/tasks/`)
- Use existing LLM providers (`app/llm/providers/`)
- Integrate with ADR-010 logging (`LLMExecutionLogger`)
- Thread ownership per ADR-035 (conversation continuity)

**Control Boundary Invariant:**

- User language SHALL NOT directly advance workflow execution.
- LLM executors MUST NOT emit routing decisions or terminal outcomes.
- Workflow advancement occurs only via explicit option selection
  where `option_id ∈ available_options[]` (ADR-037).
- Attempts to bypass the gate via natural language MUST be logged
  and result in no state transition.

**Node Type Mapping:**

| Node Type | Executor | LLM Interaction |
|-----------|----------|-----------------|
| `concierge` | `LLMConciergeExecutor` | Multi-turn conversation |
| `task` | `LLMTaskExecutor` | Single generation |
| `qa` | `LLMQAExecutor` | Validation pass/fail |
| `gate` | `GateExecutor` (existing) | No LLM - user choice |
| `end` | `EndExecutor` (existing) | No LLM - terminal |

---

### Phase 2: Concierge Intake Document Schema

Register the Concierge Intake Document as a governed artifact.

**Deliverables:**

| File | Purpose |
|------|---------|
| `seed/schemas/concierge_intake_document.v1.json` | JSON Schema |
| `seed/registry/concierge_intake_schema.py` | Schema seeder |

**Schema Fields (per ADR-025):**

```json
{
  "captured_intent": { "type": "string" },
  "constraints": { "type": "array", "items": { "type": "string" } },
  "known_unknowns": { "type": "array", "items": { "type": "string" } },
  "project_type": {
    "type": "string",
    "enum": ["greenfield", "enhancement", "migration", "integration", "replacement", "unknown"]
  },
  "gate_outcome": {
    "type": "string",
    "enum": ["qualified", "not_ready", "out_of_scope", "redirect"]
  },
  "conversation_summary": { "type": "string" }
}
```

**Schema Invariant:**

`conversation_summary` MUST be derived (synthesized by LLM), not copied verbatim from the thread transcript.

---

### Phase 3: Thread Ownership & Conversation Persistence

Implement thread ownership per ADR-035.

**Deliverables:**

| File | Changes |
|------|---------|
| `app/domain/workflow/nodes/llm_concierge_executor.py` | Thread creation/reuse |
| `app/persistence/llm_thread_repositories.py` | Thread persistence |

**Thread Lifecycle:**

1. Workflow starts → Create thread (`thread_purpose: intake_conversation`)
2. Each concierge turn → Append to thread
3. Workflow completes → Thread finalized (immutable)

---

### Phase 4: Dual Outcome Recording

Record both governance outcome and execution outcome per ADR-025 §8.

**Authority:**

The Intake Gate outcome (ADR-025) is the authoritative governance decision.
The terminal outcome (ADR-039) is derived deterministically and SHALL NOT
contradict the gate outcome.

**Deliverables:**

| File | Changes |
|------|---------|
| `app/domain/workflow/document_workflow_state.py` | Add `intake_gate_outcome` field |
| `app/domain/workflow/pg_state_persistence.py` | Persist both outcomes |
| `alembic/versions/YYYYMMDD_add_intake_gate_outcome.py` | Migration |

**Outcome Pairs:**

| Gate Outcome (ADR-025) | Terminal Outcome (ADR-039) |
|------------------------|---------------------------|
| `qualified` | `stabilized` |
| `not_ready` | `blocked` |
| `out_of_scope` | `abandoned` |
| `redirect` | `abandoned` |

---

### Phase 5: UI Integration

Connect Concierge UI to workflow engine, replacing direct LLM calls.

**Approach:** Adapter pattern - existing UI routes call workflow engine APIs.

**Deliverables:**

| File | Changes |
|------|---------|
| `app/api/routers/concierge_routes.py` | Replace direct LLM with workflow engine calls |
| `app/web/routes/public/concierge_routes.py` | Update to use workflow execution state |

**Key Changes:**

1. **Start Conversation** → `POST /api/v1/document-workflows/start`
   - `document_type: "concierge_intake"`
   - Returns `execution_id`

2. **Send Message** → `POST /api/v1/document-workflows/executions/{id}/input`
   - User message as `user_input`
   - Returns next prompt/response

3. **Run to Pause** → `POST /api/v1/document-workflows/executions/{id}/run`
   - Engine executes until user input needed

4. **Get Status** → `GET /api/v1/document-workflows/executions/{id}`
   - Shows current node, pending input, etc.

**State Mapping:**

| Current UI State | Workflow State |
|------------------|----------------|
| Session active | `status: running`, `current_node_id: clarification` |
| Ready for discovery | `status: paused`, `current_node_id: consent_gate` |
| Document generated | `status: completed`, `terminal_outcome: stabilized` |

**Endpoint Restriction:**

Concierge UI MUST use `/run` + `/input` endpoints only. The `/step` endpoint is for debug/test purposes and MUST NOT be wired into UI flows. This prevents manual-stepping UX patterns that could create bypass opportunities.

---

## 5. Migration Strategy

### Database Changes

1. Add `intake_gate_outcome` column to `workflow_executions`
2. No changes to existing `concierge_intake_session` tables (deprecated but retained)

### Cutover

1. Feature flag: `USE_WORKFLOW_ENGINE_FOR_CONCIERGE`
2. Default: `false` (existing behavior)
3. Enable after testing: `true` (workflow engine)
4. Deprecate old flow after validation

**Deprecated Table Invariant:**

Deprecated `concierge_intake_session` and `concierge_intake_event` tables MUST NOT be written to when `USE_WORKFLOW_ENGINE_FOR_CONCIERGE` is enabled. This prevents dual-writing bugs and ensures single source of truth.

---

## 6. Testing Strategy

### Unit Tests

- LLM executor tests with mock providers
- Schema validation tests
- Outcome mapping tests

### Integration Tests

- Full workflow execution (start → clarification → consent → generation → QA → outcome)
- Circuit breaker behavior (QA failure → remediation → escalation)
- Thread persistence and replay

### E2E Tests

- Concierge UI → Workflow Engine → LLM → Document artifact
- All gate outcome paths (qualified, not_ready, out_of_scope, redirect)

---

## 7. Acceptance Criteria

1. **LLM Integration** - Workflow nodes execute real LLM calls via certified prompts
2. **Conversation Flow** - Multi-turn concierge conversation persisted in threads
3. **Document Generation** - Concierge Intake Document produced with valid schema
4. **Gate Enforcement** - Only `qualified` outcomes produce artifacts eligible for Discovery
5. **Dual Recording** - Both gate outcome and terminal outcome recorded and auditable
6. **UI Continuity** - Existing Concierge UI works with workflow engine backend
7. **Audit Trail** - Full execution log per ADR-010
8. **Control Boundary** - User language cannot bypass gates; advancement only via explicit option selection

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| LLM latency affects UX | Streaming responses, progress indicators |
| Prompt quality variance | Certified prompts from role_tasks table |
| Thread state corruption | Immutable append-only thread model |
| Migration disruption | Feature flag cutover, parallel systems |
| Language bypass attempts | Control Boundary Invariant enforced; bypass attempts logged, no state transition |

---

## 9. Dependencies

| Dependency | Status |
|------------|--------|
| WS-INTAKE-ENGINE-001 | Complete |
| PostgreSQL persistence | Complete |
| LLM providers | Existing |
| ADR-010 logging | Existing |
| Task prompts | Existing |

---

## 10. Deliverables Summary

| Phase | Deliverable | Type |
|-------|-------------|------|
| 1 | LLM Node Executors | New code |
| 2 | Concierge Intake Document Schema | Seed data |
| 3 | Thread Ownership & Conversation Persistence | Code changes |
| 4 | Dual Outcome Recording | Schema + code |
| 5 | UI Integration | Code changes |

---

## 11. Estimated Effort

| Phase | Complexity | Notes |
|-------|------------|-------|
| Phase 1 | Medium | Core LLM integration |
| Phase 2 | Low | Schema definition |
| Phase 3 | Medium | Thread lifecycle |
| Phase 4 | Low | Additional field |
| Phase 5 | Medium | Adapter pattern, state mapping |

---

## 12. Success Metrics

- Concierge conversations execute via workflow engine
- Intake documents conform to registered schema
- Gate outcomes correctly block/allow downstream Discovery
- Execution logs capture full audit trail
- No regression in existing Concierge UX

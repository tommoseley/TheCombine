# WS-INTAKE-ENGINE-001: Implementation Summary

**Status:** Complete (Phases 1-5)
**Date:** 2026-01-16
**Related ADR:** ADR-039 (Document Interaction Workflow Model)

---

## Overview

WS-INTAKE-ENGINE-001 implemented the **Document Interaction Workflow Engine** for ADR-039 - a graph-based execution engine that runs workflow plans with nodes, edges, and conditional routing.

---

## What Was Built

### Phase 1: Plan Loading & Validation

| File | Purpose |
|------|---------|
| `app/domain/workflow/plan_loader.py` | Loads workflow-plan.v1.json files |
| `app/domain/workflow/plan_validator.py` | Schema + semantic validation (edge targets exist, no orphans, etc.) |
| `app/domain/workflow/plan_registry.py` | Caches loaded plans |
| `app/domain/workflow/plan_models.py` | Data models for plans, nodes, edges |

### Phase 2: Node Executors

| File | Purpose |
|------|---------|
| `app/domain/workflow/nodes/base.py` | Abstract `NodeExecutor` interface |
| `app/domain/workflow/nodes/task.py` | LLM generation tasks |
| `app/domain/workflow/nodes/gate.py` | Decision points (consent, outcome gates) |
| `app/domain/workflow/nodes/concierge.py` | Thread-based conversation |
| `app/domain/workflow/nodes/qa.py` | Validation with remediation loops |
| `app/domain/workflow/nodes/end.py` | Terminal outcomes |
| `app/domain/workflow/nodes/mock_executors.py` | Test doubles for e2e testing |

### Phase 3: Edge Router & State Management

| File | Purpose |
|------|---------|
| `app/domain/workflow/edge_router.py` | Conditional routing logic |
| `app/domain/workflow/document_workflow_state.py` | Tracks execution (current node, history, retries) |
| `app/domain/workflow/outcome_mapper.py` | Maps gate outcomes → terminal outcomes |

### Phase 4: Plan Executor (Orchestrator)

| File | Purpose |
|------|---------|
| `app/domain/workflow/plan_executor.py` | Main orchestrator |

Key methods:
- `start_execution()` - Begin workflow
- `execute_step()` - Execute single node
- `run_to_completion_or_pause()` - Execute until user input needed or completion
- `submit_user_input()` - Resume with user input
- `handle_escalation_choice()` - Handle circuit breaker escalation
- `get_execution_status()` - Get current state
- `list_executions()` - List active/all executions

### Phase 5: API Integration

| File | Purpose |
|------|---------|
| `app/api/v1/routers/document_workflows.py` | REST endpoints |

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/document-workflows/plans` | List workflow plans |
| `GET` | `/api/v1/document-workflows/plans/{id}` | Get plan details |
| `GET` | `/api/v1/document-workflows/executions` | List executions |
| `GET` | `/api/v1/document-workflows/executions/{id}` | Get execution status |
| `POST` | `/api/v1/document-workflows/start` | Start execution |
| `POST` | `/api/v1/document-workflows/executions/{id}/step` | Execute single step |
| `POST` | `/api/v1/document-workflows/executions/{id}/run` | Run to pause/completion |
| `POST` | `/api/v1/document-workflows/executions/{id}/input` | Submit user input |
| `POST` | `/api/v1/document-workflows/executions/{id}/escalation` | Handle escalation |

---

## Key Capabilities

1. **Graph-based execution** - Nodes + edges, not linear steps
2. **Conditional routing** - Edges evaluated by outcome + conditions
3. **Circuit breaker** - Max retries enforced, escalation surfaced
4. **Thread ownership** - ADR-035 integration for durable execution
5. **Pause/resume** - Stops at gates requiring user input
6. **Deterministic outcomes** - Gate outcome → terminal outcome mapping
7. **Headless execution** - Works without HTTP context (CLI, background jobs)

---

## Reference Implementation

The engine was tested against `seed/workflows/concierge_intake.v1.json` workflow with paths for:

| Gate Outcome | Terminal Outcome | Description |
|--------------|------------------|-------------|
| `qualified` | `stabilized` | Project accepted, ready for discovery |
| `out_of_scope` | `abandoned` | Polite rejection, project not suitable |
| `needs_clarification` | (loops back) | More info needed from user |

---

## Architectural Invariants

### Separation of Concerns

- **Executors perform work, not control** — they produce outcomes, not routing decisions
- **Router performs control, not work** — it selects edges, not generates content
- **Plans define legality, not behavior** — they constrain what is possible, not what happens

### Execution Invariants

- Workflow execution is **deterministic** given: plan version + initial inputs + user responses
- Node execution is **idempotent** where possible
- Execution state is **persisted after every node completion**
- Replay of persisted state produces identical routing decisions

### Audit Invariants

Every workflow execution produces:
- Ordered execution log (node_id, timestamp, outcome)
- Node outcomes (per execution)
- Retry counts (per retriable node)
- Escalation events (if circuit breaker tripped)
- Final terminal outcome + gate outcome

---

## Current Limitations

1. **In-memory persistence** - `InMemoryStatePersistence` is used; needs DB persistence for production
2. **Mock executors** - Node executors use mocks; real LLM integration pending
3. **No UI** - API-only; no workflow visualization or management UI
4. **Single workflow** - Only `concierge_intake.v1.json` is implemented

---

## Next Steps

1. Implement database persistence for `DocumentWorkflowState`
2. Connect real node executors (replace mocks with LLM calls)
3. Add workflow management UI
4. Implement additional workflow plans (Project Discovery, Epic Backlog, etc.)

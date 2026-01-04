# Phase 8: API Integration & Real-Time Progress

## Overview

Phase 8 wires the execution engine to API endpoints and adds real-time progress updates. This phase makes the workflow execution accessible via HTTP APIs with live status updates via Server-Sent Events (SSE).

## Goals

1. **Execution API**: Endpoints to start, monitor, and manage workflow executions
2. **Real-Time Progress**: SSE for live execution status updates
3. **Database Persistence**: Connect execution to PostgreSQL repositories
4. **Workflow Management**: CRUD endpoints for workflow operations
5. **Cost Tracking API**: Expose telemetry and cost data

## Timeline: 5 Days

| Day | Focus | Estimated Tests |
|-----|-------|-----------------|
| 1 | Execution API endpoints | 15 |
| 2 | SSE progress streaming | 12 |
| 3 | PostgreSQL repositories | 10 |
| 4 | Workflow management API | 12 |
| 5 | Cost/telemetry API & integration | 10 |
| **Total** | | **~59** |

**Target: 793 tests (734 + 59)**

---

## Day 1: Execution API Endpoints

### Deliverables

1. **Execution Router** (app/api/v1/executions.py)

- POST /executions/ - Start new workflow execution
- GET /executions/{id} - Get execution details
- GET /executions/{id}/steps - Get step statuses
- POST /executions/{id}/steps/{step}/clarification - Submit answers
- POST /executions/{id}/cancel - Cancel execution

2. **Request/Response Models** (app/api/models/execution.py)

- StartExecutionRequest: workflow_id, scope_type, scope_id
- ExecutionResponse: execution_id, workflow_id, status, created_at
- StepStatusResponse: step_id, status, clarification info
- ClarificationAnswers: Dict of question -> answer

3. **Execution Service** (app/api/services/execution_service.py)

- start_execution(): Create context and begin workflow
- execute_next_step(): Run next pending step
- submit_clarification(): Continue after clarification

### Tests (15)
- Start execution endpoint
- Get execution details
- Get step statuses
- Submit clarification
- Cancel execution
- Authentication required
- Invalid workflow_id handling
- Execution not found

---

## Day 2: SSE Progress Streaming

### Deliverables

1. **SSE Endpoint** (app/api/v1/executions.py)

- GET /executions/{id}/stream - Server-Sent Events stream
- Events: step_started, step_completed, clarification_needed, complete

2. **Progress Publisher** (app/execution/progress.py)

- ProgressPublisher class with subscribe/unsubscribe
- ProgressEvent dataclass: event_type, step_id, data, timestamp
- Multiple subscriber support
- Async queue-based delivery

3. **Executor Integration**

- LLMStepExecutor publishes progress events
- Events on step start, complete, error, clarification

### Tests (12)
- SSE endpoint returns EventSource
- Progress events published on step start
- Progress events published on step complete
- Clarification event published
- Client disconnect handled
- Multiple subscribers supported
- Event ordering preserved

---

## Day 3: PostgreSQL Repositories

### Deliverables

1. **PostgresDocumentRepository** (app/persistence/pg_repositories.py)

- save(): Insert/update with versioning
- get(): Retrieve by ID
- get_by_scope_type(): Query by scope and type
- list_by_scope(): List all documents in scope

2. **PostgresExecutionRepository**

- save(): Persist execution state
- get(): Retrieve execution
- list_by_scope(): Filter by scope
- list_active(): Get running/waiting executions

3. **Repository Factory**

- create_repositories(): Returns appropriate implementation
- Support both in-memory (testing) and PostgreSQL (production)

### Tests (10)
- Save and retrieve document
- Document versioning
- Get by scope and type
- Save and retrieve execution
- List executions by scope
- List active executions
- Transaction handling
- Concurrent access

---

## Day 4: Workflow Management API

### Deliverables

1. **Workflow Router** (app/api/v1/workflows.py)

- GET /workflows/ - List available workflows
- GET /workflows/{id} - Get workflow definition
- GET /workflows/{id}/schema/{step} - Get step output schema

2. **Document Router** (app/api/v1/documents.py)

- GET /documents/ - List with filters (scope, type)
- GET /documents/{id} - Get document content
- GET /documents/{id}/versions - Get version history

3. **Response Models**

- WorkflowSummary: id, name, description, step_count
- DocumentSummary: id, type, title, version, status

### Tests (12)
- List workflows
- Get workflow details
- Get step schema
- List documents with filters
- Get document content
- Get document versions
- Workflow not found
- Document not found

---

## Day 5: Cost/Telemetry API & Integration

### Deliverables

1. **Telemetry Router** (app/api/v1/telemetry.py)

- GET /telemetry/summary - Summary with date range
- GET /telemetry/executions/{id}/costs - Execution cost breakdown
- GET /telemetry/workflows/{id}/stats - Workflow statistics

2. **Response Models**

- TelemetrySummary: totals, averages, by_workflow
- ExecutionCosts: total, per-step breakdown
- StepCost: model, tokens, cost

3. **Integration Tests**

- Full execution from API start to SSE completion
- Document persistence verification
- Cost tracking accuracy

### Tests (10)
- Get telemetry summary
- Get execution costs
- Get workflow stats
- Date range filtering
- Full execution flow integration

---

## API Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /executions/ | Start execution |
| GET | /executions/{id} | Get execution details |
| GET | /executions/{id}/steps | Get step statuses |
| GET | /executions/{id}/stream | SSE progress stream |
| POST | /executions/{id}/steps/{step}/clarification | Submit answers |
| POST | /executions/{id}/cancel | Cancel execution |
| GET | /workflows/ | List workflows |
| GET | /workflows/{id} | Get workflow details |
| GET | /documents/ | List documents |
| GET | /documents/{id} | Get document |
| GET | /telemetry/summary | Get telemetry summary |
| GET | /telemetry/executions/{id}/costs | Get execution costs |

---

## File Structure

app/api/v1/
  executions.py, workflows.py, documents.py, telemetry.py

app/api/models/
  execution.py

app/execution/
  progress.py

app/persistence/
  pg_repositories.py

tests/api/
  test_executions_api.py, test_workflows_api.py
  test_documents_api.py, test_telemetry_api.py

tests/integration/
  test_full_flow.py

---

## Success Criteria

1. Can start execution via POST /executions/
2. SSE stream delivers real-time progress updates
3. Documents persist to PostgreSQL
4. Clarification flow works end-to-end via API
5. Cost tracking accessible via API
6. 793+ tests passing

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SSE connection drops | Reconnection with last-event-id |
| Long-running executions | Background task with status polling |
| Database connection exhaustion | Connection pooling, health checks |
| Concurrent execution conflicts | Optimistic locking on documents |

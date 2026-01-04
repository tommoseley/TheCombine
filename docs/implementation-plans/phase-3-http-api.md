# Phase 3: HTTP API Layer

**Goal:** Expose workflow execution via FastAPI endpoints with proper error handling, authentication hooks, and real-time status updates.

**Prerequisites:** Phase 2 complete (207 tests passing)

**Estimated Tests:** ~50 new → ~257 total

---

## Exit Criteria

1. Can start workflow via POST /workflows/{id}/start
2. Can check status via GET /workflows/{id}/executions/{exec_id}
3. Can submit acceptance decision via POST
4. Can submit clarification answers via POST
5. WebSocket delivers real-time step progress
6. Proper HTTP error responses (400/404/500)
7. Authentication hooks in place (not full implementation)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  Routers                                                 │
│  ├── /workflows           - List, get definitions        │
│  ├── /workflows/{id}/start - Start execution            │
│  ├── /executions/{id}     - Status, acceptance, clarify │
│  └── /ws/executions/{id}  - WebSocket status stream     │
├─────────────────────────────────────────────────────────┤
│  Dependencies                                            │
│  ├── get_workflow_registry() - Workflow definitions     │
│  ├── get_persistence()       - State storage            │
│  ├── get_llm_service()       - LLM provider             │
│  └── get_current_user()      - Auth (stub for now)      │
├─────────────────────────────────────────────────────────┤
│  Services (from Phase 1-2)                              │
│  ├── WorkflowExecutor                                   │
│  ├── StepExecutor                                       │
│  └── StatePersistence                                   │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Workflow Definitions

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/workflows | List available workflows |
| GET | /api/v1/workflows/{workflow_id} | Get workflow definition |

### Execution Management

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/workflows/{workflow_id}/start | Start new execution |
| GET | /api/v1/executions | List executions (with filters) |
| GET | /api/v1/executions/{execution_id} | Get execution status |
| POST | /api/v1/executions/{execution_id}/resume | Resume paused execution |
| POST | /api/v1/executions/{execution_id}/cancel | Cancel execution |

### Human Interaction

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/executions/{execution_id}/acceptance | Submit acceptance decision |
| POST | /api/v1/executions/{execution_id}/clarification | Submit clarification answers |

### Real-time Updates

| Method | Path | Description |
|--------|------|-------------|
| WS | /api/v1/ws/executions/{execution_id} | Stream execution events |

---

## Request/Response Models

### StartWorkflowRequest
```python
class StartWorkflowRequest(BaseModel):
    project_id: str
    initial_context: Optional[Dict[str, Any]] = None
```

### ExecutionResponse
```python
class ExecutionResponse(BaseModel):
    execution_id: str
    workflow_id: str
    project_id: str
    status: str  # pending, running, waiting_acceptance, completed, failed
    current_step_id: Optional[str]
    completed_steps: List[str]
    pending_acceptance: Optional[AcceptancePending]
    pending_clarification: Optional[ClarificationPending]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
```

### AcceptanceRequest
```python
class AcceptanceRequest(BaseModel):
    accepted: bool
    comment: Optional[str] = None
```

### ClarificationRequest
```python
class ClarificationRequest(BaseModel):
    answers: Dict[str, str]  # question_id -> answer
```

### WebSocket Events
```python
class ExecutionEvent(BaseModel):
    event_type: str  # step_started, step_completed, waiting_acceptance, etc.
    step_id: Optional[str]
    timestamp: datetime
    data: Dict[str, Any]
```

---

## Day-by-Day Plan

### Day 1: Core Router & Models (6 tests)

**Files:**
- `app/api/v1/schemas/workflow.py` - Request/response models
- `app/api/v1/schemas/execution.py` - Execution models
- `app/api/v1/dependencies.py` - Dependency injection
- `app/api/v1/routers/workflows.py` - Workflow definition endpoints

**Endpoints:**
- GET /workflows - List workflows
- GET /workflows/{id} - Get workflow

**Tests:**
- test_list_workflows
- test_get_workflow_found
- test_get_workflow_not_found
- test_workflow_response_schema

### Day 2: Execution Endpoints (12 tests)

**Files:**
- `app/api/v1/routers/executions.py` - Execution management
- `app/api/v1/services/execution_service.py` - Business logic layer

**Endpoints:**
- POST /workflows/{id}/start
- GET /executions
- GET /executions/{id}
- POST /executions/{id}/cancel

**Tests:**
- test_start_workflow_success
- test_start_workflow_not_found
- test_start_workflow_invalid_request
- test_get_execution_found
- test_get_execution_not_found
- test_list_executions_empty
- test_list_executions_with_results
- test_list_executions_filter_by_status
- test_cancel_execution
- test_cancel_already_complete

### Day 3: Human Interaction Endpoints (10 tests)

**Files:**
- Update `app/api/v1/routers/executions.py`

**Endpoints:**
- POST /executions/{id}/acceptance
- POST /executions/{id}/clarification
- POST /executions/{id}/resume

**Tests:**
- test_submit_acceptance_approved
- test_submit_acceptance_rejected
- test_submit_acceptance_wrong_state
- test_submit_acceptance_not_found
- test_submit_clarification_success
- test_submit_clarification_wrong_state
- test_submit_clarification_missing_answers
- test_resume_after_acceptance
- test_resume_wrong_state

### Day 4: WebSocket & Events (10 tests)

**Files:**
- `app/api/v1/routers/websocket.py` - WebSocket endpoint
- `app/api/v1/services/event_broadcaster.py` - Event distribution

**Functionality:**
- Connect to execution stream
- Receive step_started events
- Receive step_completed events
- Receive waiting_acceptance events
- Handle disconnection gracefully

**Tests:**
- test_websocket_connect
- test_websocket_receives_step_started
- test_websocket_receives_step_completed
- test_websocket_receives_waiting_acceptance
- test_websocket_invalid_execution_id
- test_websocket_execution_not_found
- test_websocket_disconnect_cleanup
- test_multiple_websocket_clients

### Day 5: Error Handling & Integration (12 tests)

**Files:**
- `app/api/v1/exceptions.py` - Custom exceptions
- `app/api/v1/error_handlers.py` - Exception handlers
- `tests/api/v1/test_integration.py` - End-to-end tests

**Functionality:**
- Consistent error response format
- Validation error handling
- Not found handling
- Internal error handling

**Tests:**
- test_validation_error_response
- test_not_found_response
- test_internal_error_response
- test_full_workflow_execution_flow
- test_workflow_with_acceptance_pause
- test_workflow_with_clarification_pause
- test_concurrent_executions

---

## Error Response Format

```python
class ErrorResponse(BaseModel):
    error_code: str      # e.g., "WORKFLOW_NOT_FOUND"
    message: str         # Human-readable message
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

# HTTP Status Mapping
# 400 - Validation errors, invalid state transitions
# 404 - Workflow/execution not found
# 409 - Conflict (e.g., execution already running)
# 500 - Internal errors
# 503 - LLM service unavailable
```

---

## Dependencies Structure

```python
# app/api/v1/dependencies.py

async def get_workflow_registry() -> WorkflowRegistry:
    """Load workflow definitions from seed directory."""
    ...

async def get_persistence() -> StatePersistence:
    """Get state persistence (file-based for MVP)."""
    ...

async def get_llm_service() -> LLMService:
    """Get configured LLM service."""
    ...

async def get_current_user() -> User:
    """Get authenticated user (stub for Phase 3)."""
    # Returns stub user for now
    # Full auth in Phase 4
    ...

async def get_execution_service(
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    persistence: StatePersistence = Depends(get_persistence),
    llm: LLMService = Depends(get_llm_service),
) -> ExecutionService:
    """Build execution service with dependencies."""
    ...
```

---

## File Structure

```
app/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── dependencies.py
    ├── exceptions.py
    ├── error_handlers.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── workflow.py
    │   ├── execution.py
    │   └── common.py
    ├── routers/
    │   ├── __init__.py
    │   ├── workflows.py
    │   ├── executions.py
    │   └── websocket.py
    └── services/
        ├── __init__.py
        ├── execution_service.py
        └── event_broadcaster.py

tests/api/
└── v1/
    ├── __init__.py
    ├── conftest.py
    ├── test_workflows.py
    ├── test_executions.py
    ├── test_acceptance.py
    ├── test_clarification.py
    ├── test_websocket.py
    └── test_integration.py
```

---

## Testing Strategy

### Unit Tests
- Mock LLM service (no API calls)
- Mock persistence (in-memory)
- Test each endpoint in isolation

### Integration Tests
- Use TestClient with real workflow definitions
- Test full execution flows
- Test state persistence across requests

### Fixtures
```python
@pytest.fixture
def test_client():
    """FastAPI test client with mocked dependencies."""
    ...

@pytest.fixture
def mock_llm():
    """LLM that returns valid JSON responses."""
    ...

@pytest.fixture
def sample_workflow():
    """Load test workflow from fixtures."""
    ...
```

---

## Key Decisions

1. **Async everywhere** - All endpoints and services are async
2. **Execution IDs** - UUID4, generated at start
3. **Background execution** - Workflows run in background tasks
4. **State snapshots** - Persist after each step completion
5. **WebSocket scope** - One connection per execution
6. **Auth stub** - Returns mock user, full auth in Phase 4

---

## Definition of Done

- [ ] All endpoints return correct status codes
- [ ] Request validation produces 400 with details
- [ ] Not found produces 404
- [ ] WebSocket streams events in real-time
- [ ] State persists across server restarts
- [ ] ~50 new tests passing
- [ ] API documentation auto-generated (OpenAPI)
- [ ] No hard-coded configuration

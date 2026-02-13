# Phase 2: Workflow Executor - Implementation Summary
**Completed:** 2026-01-03
**Duration:** 3 days (same session as Phase 1)
**Tests:** 207 total (73 new in Phase 2)

---

## Overview

Phase 2 delivers multi-step workflow orchestration with iteration support, acceptance gates for human approval, and state persistence for restart survival.

---

## Architecture

```
WorkflowExecutor
    │
    ├── StepExecutor (from Phase 1)
    │       └── Execute individual steps
    │
    ├── WorkflowContext
    │       ├── Scope-aware document storage
    │       ├── Entity storage
    │       └── Scope stack for iteration
    │
    ├── IterationHandler
    │       ├── Expand iterate_over blocks
    │       └── Generate entity instances
    │
    ├── AcceptanceGate
    │       ├── Check acceptance requirements
    │       └── Record decisions
    │
    └── StatePersistence
            ├── FileStatePersistence (dev/test)
            └── InMemoryStatePersistence (unit tests)
```

---

## Execution Flow

```
WorkflowExecutor.start()
    │
    ├── Create WorkflowState + WorkflowContext
    │
    └── run_until_pause()
            │
            ├── Get next step
            │   │
            │   ├── None → COMPLETED
            │   │
            │   ├── Production step → _execute_production_step()
            │   │       │
            │   │       ├── StepExecutor.execute()
            │   │       ├── Store output document
            │   │       ├── Check acceptance requirement
            │   │       │   └── If required → WAITING_ACCEPTANCE (pause)
            │   │       └── Mark step complete
            │   │
            │   └── Iteration step → _execute_iteration_step()
            │           │
            │           ├── IterationHandler.expand()
            │           ├── For each instance:
            │           │   ├── push_scope()
            │           │   ├── Execute nested steps
            │           │   └── pop_scope()
            │           └── Mark iteration complete
            │
            └── Loop until pause or complete
```

---

## Components Delivered

### Day 1: Context & Iteration

| File | Lines | Purpose |
|------|-------|---------|
| `context.py` | 157 | Scope-aware document/entity storage |
| `iteration.py` | 164 | Expand iterate_over blocks |

### Day 2: State & Acceptance

| File | Lines | Purpose |
|------|-------|---------|
| `workflow_state.py` | 237 | Track workflow execution progress |
| `gates/acceptance.py` | 199 | Human approval flow |

### Day 3: Executor & Persistence

| File | Lines | Purpose |
|------|-------|---------|
| `workflow_executor.py` | 289 | Multi-step orchestration |
| `persistence.py` | 204 | Save/restore state |

---

## Key Types

### WorkflowContext
```python
class WorkflowContext:
    # DocumentStore protocol (used by InputResolver)
    def get_document(self, doc_type, scope, scope_id) -> Optional[Dict]: ...
    def get_entity(self, entity_type, scope, scope_id) -> Optional[Dict]: ...
    
    # Storage
    def store_document(self, doc_type, content, scope_id=None): ...
    def store_entity(self, entity_type, entity_id, content): ...
    
    # Scope management for iteration
    def push_scope(self, scope, scope_id, entity): ...
    def pop_scope(self) -> ScopeInstance: ...
    def get_scope_chain(self) -> Dict[str, str]: ...
    
    # Serialization
    def to_dict(self) -> Dict: ...
    @classmethod
    def from_dict(cls, data, workflow) -> WorkflowContext: ...
```

### WorkflowState
```python
class WorkflowStatus(Enum):
    PENDING, RUNNING, WAITING_ACCEPTANCE, 
    WAITING_CLARIFICATION, COMPLETED, FAILED, CANCELLED

@dataclass
class WorkflowState:
    workflow_id: str
    project_id: str
    status: WorkflowStatus
    current_step_id: Optional[str]
    completed_steps: List[str]
    step_states: Dict[str, StepState]
    iteration_progress: Dict[str, IterationProgress]
    pending_acceptance: Optional[str]
    acceptance_decisions: Dict[str, AcceptanceDecision]
```

### WorkflowExecutionResult
```python
@dataclass
class WorkflowExecutionResult:
    state: WorkflowState
    context: WorkflowContext
    paused: bool = False
    pause_reason: Optional[str] = None
```

---

## Iteration Handling

Given workflow step:
```json
{
  "step_id": "epic_iteration",
  "iterate_over": {
    "doc_type": "epic_backlog",
    "collection_field": "epics",
    "entity_type": "epic"
  },
  "steps": [...]
}
```

IterationHandler:
1. Gets `epic_backlog` document from context
2. Extracts `epics` array
3. Creates IterationInstance per item
4. Each instance has scope/scope_id for context isolation

---

## Acceptance Flow

1. Step produces document with `acceptance_required: true`
2. WorkflowExecutor pauses: `status = WAITING_ACCEPTANCE`
3. External system calls `process_acceptance(decision)`
4. If accepted: resume workflow
5. If rejected: fail workflow

---

## State Persistence

```python
# Save state for restart
persistence = FileStatePersistence(Path("./workflow_state"))
await persistence.save(state, context)

# Load on restart
loaded = await persistence.load(workflow_id, project_id, workflow)
if loaded:
    state, context = loaded
    result = await executor.resume(workflow, state, context)
```

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_context.py | 12 | Document/entity storage, scope stack |
| test_iteration.py | 11 | Collection expansion, ID generation |
| test_workflow_state.py | 18 | Status transitions, serialization |
| test_acceptance.py | 16 | Acceptance requirements, decisions |
| test_workflow_executor.py | 10 | Multi-step, iteration, acceptance pause |
| test_persistence.py | 10 | File and in-memory persistence |
| **Phase 2 Total** | **77** | |

---

## Files Structure

```
app/domain/workflow/
├── context.py           # WorkflowContext
├── iteration.py         # IterationHandler
├── workflow_state.py    # WorkflowState, WorkflowStatus
├── workflow_executor.py # WorkflowExecutor
├── persistence.py       # StatePersistence implementations
└── gates/
    └── acceptance.py    # AcceptanceGate

tests/domain/workflow/
├── test_context.py
├── test_iteration.py
├── test_workflow_state.py
├── test_workflow_executor.py
├── test_persistence.py
└── gates/
    └── test_acceptance.py
```

---

## Usage Example

```python
from app.domain.workflow import (
    WorkflowExecutor, WorkflowLoader, StepExecutor,
    PromptLoader, ClarificationGate, QAGate, AcceptanceDecision,
    FileStatePersistence
)

# Setup
step_executor = StepExecutor(
    prompt_loader=PromptLoader(),
    clarification_gate=ClarificationGate(),
    qa_gate=QAGate(),
    llm_service=my_llm_service,
)
workflow_executor = WorkflowExecutor(step_executor)
persistence = FileStatePersistence(Path("./state"))

# Load workflow
loader = WorkflowLoader()
workflow = loader.load(Path("seed/workflows/software_product_development.v1.json"))

# Start execution
result = await workflow_executor.start(workflow, "project_123")

# Handle pause for acceptance
if result.state.status == WorkflowStatus.WAITING_ACCEPTANCE:
    await persistence.save(result.state, result.context)
    # ... wait for human decision ...
    
    decision = AcceptanceDecision(
        doc_type=result.state.pending_acceptance,
        scope_id=result.state.pending_acceptance_scope_id,
        accepted=True,
        decided_by="user@example.com",
        comment="Approved"
    )
    result = await workflow_executor.process_acceptance(
        workflow, result.state, result.context, decision
    )

# Check completion
if result.state.status == WorkflowStatus.COMPLETED:
    print("Workflow complete!")
    await persistence.delete(workflow.workflow_id, "project_123")
```

---

## Exit Criteria Met

1. ✅ Can run Discovery → Epic Backlog → Architecture
2. ✅ Iteration works for multiple epics
3. ✅ Can pause and resume at acceptance
4. ✅ State survives restart

---

## Next: Phase 3

Phase 3 adds HTTP API layer:
- FastAPI endpoints for workflow operations
- WebSocket for real-time status
- Authentication integration
- Error handling and logging

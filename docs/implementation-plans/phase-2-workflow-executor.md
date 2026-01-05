# Phase 2: Workflow Executor - Implementation Plan
**Status:** Ready to Start
**Duration:** 3-4 days
**Depends on:** Phase 1 Complete (134 tests passing)

---

## Goal

Execute multi-step workflows with iteration, state persistence, and acceptance gates.

## Exit Criteria (from MVP-Roadmap.md)

1. Can run Discovery → Epic Backlog → Architecture
2. Iteration works for multiple epics
3. Can pause and resume at acceptance
4. State survives restart

---

## Architecture Overview

```
WorkflowExecutor
    │
    ├── WorkflowRegistry (from Phase 1)
    │       └── Get workflow definition
    │
    ├── StepExecutor (from Phase 1)
    │       └── Execute individual steps
    │
    ├── WorkflowContext (NEW)
    │       ├── Scope-aware document storage
    │       └── Implements DocumentStore protocol
    │
    ├── IterationHandler (NEW)
    │       └── Expand iterate_over blocks
    │
    ├── AcceptanceGate (NEW)
    │       └── Human approval flow
    │
    └── StatePersistence (NEW)
            └── Save/restore execution state
```

---

## Integration with Phase 1

Phase 2 builds directly on Phase 1 components:

| Phase 1 Component | Phase 2 Usage |
|-------------------|---------------|
| `StepExecutor` | Called for each production step |
| `InputResolver` | Used internally by StepExecutor |
| `DocumentStore` protocol | Implemented by WorkflowContext |
| `StepState` | Embedded in WorkflowState |
| `WorkflowRegistry` | Load workflow definitions |
| `Workflow`, `WorkflowStep` | Navigate step graph |

---

## Day 1: Context & Iteration

### Task 2.1: WorkflowContext
**File:** `app/domain/workflow/context.py`

Scope-aware document storage implementing the `DocumentStore` protocol.

```python
@dataclass
class ScopeInstance:
    scope: str
    scope_id: str
    entity: Dict[str, Any]

class WorkflowContext:
    def __init__(self, workflow: Workflow, project_id: str): ...
    
    # DocumentStore protocol
    def get_document(self, doc_type, scope, scope_id) -> Optional[Dict]: ...
    def get_entity(self, entity_type, scope, scope_id) -> Optional[Dict]: ...
    
    # Storage
    def store_document(self, doc_type, content, scope_id=None): ...
    def store_entity(self, entity_type, entity_id, content): ...
    
    # Scope management
    def push_scope(self, scope, scope_id, entity): ...
    def pop_scope(self) -> ScopeInstance: ...
    def get_scope_chain(self) -> Dict[str, str]: ...
    
    # Serialization
    def to_dict(self) -> Dict: ...
    @classmethod
    def from_dict(cls, data, workflow) -> "WorkflowContext": ...
```

### Task 2.2: IterationHandler
**File:** `app/domain/workflow/iteration.py`

```python
@dataclass
class IterationInstance:
    entity_type: str
    entity_id: str
    entity_data: Dict[str, Any]
    scope: str
    scope_id: str
    steps: List[WorkflowStep]

class IterationHandler:
    def __init__(self, workflow: Workflow): ...
    def expand(self, step, context) -> List[IterationInstance]: ...
    def get_collection(self, doc_type, collection_field, context) -> List[Dict]: ...
```

---

## Day 2: State & Acceptance

### Task 2.3: WorkflowState
**File:** `app/domain/workflow/workflow_state.py`

```python
class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_ACCEPTANCE = "waiting_acceptance"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

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
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

### Task 2.4: AcceptanceGate
**File:** `app/domain/workflow/gates/acceptance.py`

```python
@dataclass
class AcceptanceDecision:
    doc_type: str
    scope_id: Optional[str]
    accepted: bool
    comment: Optional[str]
    decided_by: str
    decided_at: datetime

class AcceptanceGate:
    def requires_acceptance(self, doc_type) -> bool: ...
    def get_acceptors(self, doc_type) -> List[str]: ...
    def record_decision(self, doc_type, scope_id, accepted, decided_by, comment=None): ...
    def can_proceed(self, doc_type, scope_id, decisions) -> bool: ...
```

---

## Day 3: Executor & Persistence

### Task 2.5: WorkflowExecutor
**File:** `app/domain/workflow/workflow_executor.py`

```python
class WorkflowExecutor:
    def __init__(self, step_executor, iteration_handler, acceptance_gate): ...
    
    async def start(self, workflow, project_id) -> Tuple[WorkflowState, WorkflowContext]: ...
    async def resume(self, workflow, state, context) -> Tuple[WorkflowState, WorkflowContext]: ...
    async def run_until_pause(self, workflow, state, context) -> Tuple[WorkflowState, WorkflowContext]: ...
    async def process_acceptance(self, workflow, state, context, decision): ...
    def get_next_step(self, workflow, state) -> Optional[WorkflowStep]: ...
```

### Task 2.6: StatePersistence
**File:** `app/domain/workflow/persistence.py`

```python
class StatePersistence(Protocol):
    async def save(self, state, context) -> None: ...
    async def load(self, workflow_id, project_id, workflow) -> Optional[Tuple]: ...
    async def delete(self, workflow_id, project_id) -> None: ...

class FileStatePersistence:
    def __init__(self, base_dir: Path): ...
    # Implements StatePersistence protocol
```

---

## Day 4: Integration Testing

**File:** `tests/integration/test_workflow_execution.py`

```python
@pytest.mark.asyncio
async def test_discovery_to_epic_backlog(): ...

@pytest.mark.asyncio
async def test_full_workflow_with_iteration(): ...

@pytest.mark.asyncio
async def test_pause_and_resume_at_acceptance(): ...

@pytest.mark.asyncio
async def test_state_survives_restart(): ...
```

---

## Test Count Estimate

| Test File | Tests |
|-----------|-------|
| test_context.py | 10 |
| test_iteration.py | 8 |
| test_workflow_state.py | 8 |
| test_acceptance.py | 8 |
| test_workflow_executor.py | 12 |
| test_persistence.py | 8 |
| test_workflow_execution.py | 6 |
| **Total New** | **~60** |
| **Phase 1** | **134** |
| **Grand Total** | **~194** |

---

## Definition of Done

1. WorkflowContext implements DocumentStore protocol
2. IterationHandler expands collections to instances
3. WorkflowState tracks progress through steps
4. AcceptanceGate pauses for human decision
5. WorkflowExecutor orchestrates full flow
6. State persists and survives restart
7. Integration test: Discovery → Epic Backlog → Architecture
8. All unit tests passing

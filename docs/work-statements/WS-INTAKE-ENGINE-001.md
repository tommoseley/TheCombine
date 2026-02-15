# WS-INTAKE-ENGINE-001: Document Interaction Workflow Engine

**Status:** **COMPLETE**
**Date:** 2026-01-16
**Scope:** Multi-phase implementation
**Depends On:** WS-INTAKE-WORKFLOW-001 (complete)
**Related ADRs:** ADR-025, ADR-035, ADR-036, ADR-037, ADR-038, ADR-039

---

## Objective

Implement the execution engine for Document Interaction Workflow Plans (ADR-039), enabling graph-based workflow execution with node-type handlers, conditional edge routing, and thread ownership integration.

The reference implementation target is `concierge_intake.v1.json` - the Concierge Intake Document Workflow created in WS-INTAKE-WORKFLOW-001.

---

## Current State Analysis

### Existing Infrastructure (Reusable)

| Component | Location | Reuse Strategy |
|-----------|----------|----------------|
| `WorkflowContext` | `app/domain/workflow/context.py` | Extend for node state |
| `StepExecutor` | `app/domain/workflow/step_executor.py` | Adapt for task nodes |
| `AcceptanceGate` | `app/domain/workflow/gates/acceptance.py` | Reuse for gate nodes |
| `QAGate` | `app/domain/workflow/gates/qa.py` | Reuse for QA nodes |
| `ClarificationGate` | `app/domain/workflow/gates/clarification.py` | Reuse for concierge nodes |
| `ThreadExecutionService` | `app/domain/services/thread_execution_service.py` | Integrate for thread ownership |
| `LLMThread`, `LLMWorkItem` | `app/persistence/models.py` | Use for durable execution |

### Missing Infrastructure (To Build)

| Component | Purpose |
|-----------|---------|
| `PlanLoader` | Load and parse workflow-plan.v1.json files |
| `PlanValidator` | Validate plan schema and graph semantics |
| `PlanExecutor` | Graph traversal orchestrator |
| `NodeExecutor` (base) | Abstract node execution interface |
| `TaskNodeExecutor` | Execute task nodes (LLM generation) |
| `GateNodeExecutor` | Execute gate nodes (decision points) |
| `ConciergeNodeExecutor` | Execute concierge nodes (thread-based conversation) |
| `QANodeExecutor` | Execute QA nodes (validation + remediation) |
| `EndNodeExecutor` | Handle terminal outcomes |
| `EdgeRouter` | Evaluate conditions and route to next node |
| `OutcomeMapper` | Map gate outcomes to terminal outcomes |
| `DocumentWorkflowState` | Track node-based execution state |

---

## Architectural Constraints

### 1. Graph-Based Execution Model

The engine MUST support:
- Directed graph traversal (nodes + edges)
- Multiple entry points (entry_node_ids)
- Conditional edge evaluation (outcome + conditions)
- Cyclic paths (remediation loops)
- Multiple terminal nodes

The engine MUST NOT:
- Assume linear execution order
- Hard-code node sequences
- Conflate graph structure with execution order

### 2. Node Type Contract

Each node type has a defined execution contract:

| Node Type | Input | Output | Side Effects |
|-----------|-------|--------|--------------|
| `concierge` | Thread context | Conversation state | Appends to thread |
| `task` | Input documents | Produced document | Stores document |
| `gate` | Execution state | Gate outcome | Records decision |
| `qa` | Document to validate | Pass/fail + feedback | May trigger remediation |
| `end` | Execution state | Terminal outcome | Closes workflow |

### 3. Thread Ownership (ADR-035)

Document workflows with `owns_thread: true` MUST:
- Create a thread on workflow start
- Link all LLM executions to work items
- Record outcomes to ledger entries
- Close thread on workflow completion

Thread creation is idempotent per document instance.

### 4. Edge Routing Logic

Edge evaluation follows this precedence:
1. Match `from_node_id` to current node
2. Match `outcome` to node execution result
3. Evaluate `conditions` (all must pass)
4. Select first matching edge
5. If no match and node is non-terminal, fail execution

Condition types supported:
- `retry_count`: Compare against execution retry counter
- `state_value`: Compare against workflow state field

### 5. Circuit Breaker Enforcement (ADR-037)

The engine MUST enforce `governance.circuit_breaker.max_retries`:
- Track retry count per retriable node
- Evaluate retry conditions on edges
- Route to escalation when breaker trips
- Surface escalation options to caller

### 6. Outcome Mapping (ADR-025 / ADR-039)

Terminal outcome is derived from gate outcome via `outcome_mapping`:
- Gate outcome is authoritative (governance vocabulary)
- Terminal outcome is computed (execution vocabulary)
- Both are recorded and auditable
- Mapping is deterministic and enforced by engine

### 7. Staleness Handling (ADR-036)

The engine MUST NOT auto-re-enter completed workflows.

If staleness is detected:
- Block downstream operations
- Surface explicit refresh option
- Require user action to restart

---

## Invariants

### A. Execution Invariants

- Workflow execution is **deterministic** given: plan version + initial inputs + user responses
- Node execution is **idempotent** where possible
- Execution state is **persisted after every node completion**
- Replay of persisted state produces identical routing decisions

### B. Separation Invariants

- **Executors perform work, not control** — they produce outcomes, not routing decisions
- **Router performs control, not work** — it selects edges, not generates content
- **Plans define legality, not behavior** — they constrain what is possible, not what happens

This separation is non-negotiable. Violations are architectural defects.

### C. Audit Invariants

Every workflow execution MUST produce:
- Ordered execution log (node_id, timestamp, outcome)
- Node outcomes (per execution)
- Retry counts (per retriable node)
- Escalation events (if circuit breaker tripped)
- Final terminal outcome + gate outcome

All audit data is immutable once written.

---

## Implementation Phases

### Phase 1: Plan Loading & Validation

**Deliverables:**
- `app/domain/workflow/plan_loader.py` - Load workflow-plan.v1.json
- `app/domain/workflow/plan_validator.py` - Schema + semantic validation
- `app/domain/workflow/plan_registry.py` - Cache loaded plans
- Unit tests for loader and validator

**Validation Rules:**
- All edge targets exist as nodes (or null for non-advancing)
- All edge sources exist as nodes
- Entry nodes exist
- Non-end nodes have outbound edges
- Outcome mapping covers all gate outcomes
- No orphan nodes (unreachable from entry)

**Acceptance Criteria:**
- [ ] `concierge_intake.v1.json` loads without error
- [ ] Invalid plans produce clear error messages
- [ ] Plan registry caches loaded plans
- [ ] 100% test coverage on loader/validator

---

### Phase 2: Node Executors

**Deliverables:**
- `app/domain/workflow/nodes/__init__.py`
- `app/domain/workflow/nodes/base.py` - `NodeExecutor` ABC
- `app/domain/workflow/nodes/task.py` - `TaskNodeExecutor`
- `app/domain/workflow/nodes/gate.py` - `GateNodeExecutor`
- `app/domain/workflow/nodes/concierge.py` - `ConciergeNodeExecutor`
- `app/domain/workflow/nodes/qa.py` - `QANodeExecutor`
- `app/domain/workflow/nodes/end.py` - `EndNodeExecutor`
- Unit tests for each executor

**NodeExecutor Interface:**
```python
class NodeExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        node: Node,
        context: DocumentWorkflowContext,
        state: DocumentWorkflowState,
    ) -> NodeResult:
        """Execute node and return result with outcome."""
        pass
```

**NodeResult:**
```python
@dataclass
class NodeResult:
    outcome: str  # e.g., "success", "failed", "qualified"
    produced_document: Optional[dict] = None
    requires_user_input: bool = False
    user_prompt: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

**Node Executor Boundary Constraints:**

All Node Executors MUST NOT:
- Inspect or select outgoing edges
- Mutate workflow control state (current_node_id, retry_counts)
- Infer routing decisions
- Access other nodes in the plan

All routing decisions are performed **exclusively** by the EdgeRouter.

**ConciergeNodeExecutor Specific Constraints:**

ConciergeNodeExecutor MAY:
- Ask clarification questions
- Accept user responses
- Update workflow-local context (conversation state)
- Append messages to the owned thread

ConciergeNodeExecutor MUST NOT:
- Choose workflow routing options
- Infer next steps or suggest paths
- Bypass EdgeRouter constraints
- Make autonomous decisions about workflow progression

The Concierge asks questions; it does not decide what happens next.

**Acceptance Criteria:**
- [ ] Each node type has executor with tests
- [ ] Task executor integrates with existing StepExecutor
- [ ] QA executor integrates with existing QAGate
- [ ] Gate executor supports outcome selection
- [ ] Concierge executor supports thread-based conversation
- [ ] End executor records terminal outcome

---

### Phase 3: Edge Router & State Management

**Deliverables:**
- `app/domain/workflow/edge_router.py` - Edge evaluation and routing
- `app/domain/workflow/document_workflow_state.py` - Node-based state
- `app/domain/workflow/outcome_mapper.py` - Gate → terminal mapping
- Unit tests for routing logic

**EdgeRouter Logic:**
```python
class EdgeRouter:
    def get_next_node(
        self,
        current_node_id: str,
        outcome: str,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
    ) -> Optional[str]:
        """Return next node_id or None if terminal/non-advancing."""
        pass

    def evaluate_conditions(
        self,
        conditions: List[EdgeCondition],
        state: DocumentWorkflowState,
    ) -> bool:
        """Return True if all conditions pass."""
        pass
```

**DocumentWorkflowState:**
```python
@dataclass
class DocumentWorkflowState:
    workflow_id: str
    document_id: str
    current_node_id: str
    status: DocumentWorkflowStatus  # running, paused, completed, failed
    node_history: List[NodeExecution]
    retry_counts: Dict[str, int]
    gate_outcome: Optional[str] = None
    terminal_outcome: Optional[str] = None
    thread_id: Optional[str] = None
```

**OutcomeMapper Purity Constraints:**

OutcomeMapper is a **pure function**:
- Given `(gate_outcome)` → returns fixed `terminal_outcome`
- No LLM calls
- No heuristics
- No "best guess" inference
- No external state consultation

The mapping table is defined in the plan and is the single source of truth.

**Circuit Breaker Scope:**

Retry counter is scoped to `(document_id, generating_node_id)`:
- QA failures increment the retry counter for the upstream generating node
- Concierge clarification requests do NOT increment retry counters
- Gate decisions do NOT increment retry counters
- Only production failures (task, qa remediation) count toward circuit breaker

This prevents false trips from user interaction patterns.

**Acceptance Criteria:**
- [ ] Edge router correctly evaluates conditions
- [ ] Retry count conditions work for circuit breaker
- [ ] State tracks node execution history
- [ ] Outcome mapper enforces deterministic mapping
- [ ] Non-advancing edges (to_node_id: null) handled
- [ ] Circuit breaker only trips on production failures

---

### Phase 4: Plan Executor (Orchestrator)

**Deliverables:**
- `app/domain/workflow/plan_executor.py` - Main orchestrator
- Integration with ThreadExecutionService
- Persistence layer for DocumentWorkflowState
- Unit and integration tests

**PlanExecutor Interface:**
```python
class PlanExecutor:
    async def start(
        self,
        plan_id: str,
        document_id: str,
        initial_context: dict,
    ) -> DocumentWorkflowState:
        """Start new document workflow execution."""
        pass

    async def run_until_pause(
        self,
        state: DocumentWorkflowState,
    ) -> DocumentWorkflowState:
        """Execute until pause point or completion."""
        pass

    async def submit_user_input(
        self,
        state: DocumentWorkflowState,
        input_data: dict,
    ) -> DocumentWorkflowState:
        """Resume execution with user input."""
        pass

    async def get_escalation_options(
        self,
        state: DocumentWorkflowState,
    ) -> List[str]:
        """Return available escalation options if circuit breaker tripped."""
        pass
```

**Execution Loop:**
```
start()
  â”œâ”€â”€ Load plan from registry
  â”œâ”€â”€ Create thread if owns_thread
  â”œâ”€â”€ Initialize state at entry node
  â””â”€â”€ Call run_until_pause()

run_until_pause()
  â”œâ”€â”€ Loop:
  â”‚   â”œâ”€â”€ Get current node from plan
  â”‚   â”œâ”€â”€ Get executor for node type
  â”‚   â”œâ”€â”€ Execute node
  â”‚   â”œâ”€â”€ If requires_user_input: pause and return
  â”‚   â”œâ”€â”€ Route to next node via EdgeRouter
  â”‚   â”œâ”€â”€ If no next node (terminal): complete and return
  â”‚   â””â”€â”€ Update state with new current_node_id
  â””â”€â”€ Return updated state
```

**Headless Execution Requirement:**

PlanExecutor MUST be fully functional without HTTP/SSE:
- Execute a workflow from start to completion
- Emit events via injectable event sink (not hard-coded SSE)
- Persist state via injectable repository
- Support CLI invocation, background jobs, and recovery scenarios

Phase 5 (API) wraps PlanExecutor; it does not define it.

**Acceptance Criteria:**
- [ ] Executor runs concierge_intake workflow end-to-end
- [ ] Thread created and linked to execution
- [ ] Pauses correctly at consent gate
- [ ] QA loop executes with retry tracking
- [ ] Circuit breaker trips at max_retries
- [ ] Terminal outcome correctly derived from gate outcome
- [ ] State persisted and recoverable
- [ ] Executor works without HTTP context (headless mode)

---

### Phase 5: API Integration

**Deliverables:**
- `app/api/v1/routers/document_workflows.py` - REST endpoints
- `app/api/v1/schemas/document_workflow.py` - Request/response schemas
- SSE endpoint for execution progress
- Integration tests

**Endpoints:**
```
GET  /api/v1/workflow-plans                     → List available plans
GET  /api/v1/workflow-plans/{plan_id}           → Get plan definition

POST /api/v1/document-workflows                 → Start document workflow
GET  /api/v1/document-workflows/{id}            → Get execution state
POST /api/v1/document-workflows/{id}/submit     → Submit user input
POST /api/v1/document-workflows/{id}/escalate   → Choose escalation option
GET  /api/v1/document-workflows/{id}/progress   → SSE stream
```

**Acceptance Criteria:**
- [ ] All endpoints implemented with validation
- [ ] SSE streaming works for progress updates
- [ ] Escalation options surfaced via API
- [ ] Error responses follow existing patterns

---

## Testing Strategy

### Unit Tests
- Plan loader/validator edge cases
- Each node executor in isolation
- Edge router condition evaluation
- Outcome mapper determinism
- State serialization round-trip

### Integration Tests
- Full concierge_intake workflow execution
- Thread lifecycle (create → work items → close)
- Circuit breaker trip and escalation
- Pause/resume at consent gate
- QA remediation loop

### Contract Tests
- API request/response validation
- SSE event format verification
- State persistence compatibility

---

## Out of Scope

This work statement does NOT include:
- UI/UX for document workflow interaction
- Concierge conversation UI (chat interface)
- Downstream document workflow plans (Project Discovery, etc.)
- Migration of existing workflow.v1 executions
- Multi-document workflow orchestration (project-level)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Thread infrastructure untested at scale | Add load tests in Phase 4 |
| Edge routing complexity | Comprehensive unit tests, visual graph validation |
| State recovery after crash | Persistence tests with simulated failures |
| Concierge node conversation UX | Defer UI; API-first approach |

### Architectural Drift Risks

**Risk 1: Node Executors becoming mini-engines**

Failure mode: Developers put routing logic, retry logic, or plan interpretation inside executors.

Mitigation: Explicit boundary constraints (see Phase 2). Code review checklist item: "Does this executor touch edges or routing state?"

**Risk 2: ConciergeNodeExecutor becoming "smart routing"**

Failure mode: Concierge infers workflow paths or makes autonomous decisions.

Mitigation: Explicit MAY/MUST NOT constraints (see Phase 2). The Concierge asks; EdgeRouter decides.

**Risk 3: OutcomeMapper introducing vibes**

Failure mode: OutcomeMapper uses LLMs, heuristics, or "best guess" logic.

Mitigation: OutcomeMapper is a pure lookup function. Unit tests verify determinism. No dependencies beyond the plan's mapping table.

**Risk 4: Circuit breaker false trips**

Failure mode: Concierge clarification or gate decisions increment retry counter.

Mitigation: Explicit scope: `(document_id, generating_node_id)`. Only QA failures increment. Tests verify clarification does not trip breaker.

**Risk 5: Phase 4 coupled to HTTP**

Failure mode: PlanExecutor requires HTTP context to function.

Mitigation: Headless execution requirement. Injectable event sink and repository. CLI test harness validates headless mode.

---

## Success Criteria

1. `concierge_intake.v1.json` executes end-to-end via API
2. All governance constraints (ADR-025, 036, 037, 039) enforced
3. Thread ownership works per ADR-035
4. Circuit breaker trips and surfaces escalation options
5. Terminal outcome deterministically mapped from gate outcome
6. 100% test coverage on new code
7. Existing test suite remains green

---

## Summary

WS-INTAKE-ENGINE-001 delivers the Document Interaction Workflow Engine, enabling execution of graph-based workflow plans.

This is the execution counterpart to WS-INTAKE-WORKFLOW-001 (plan definition) and completes the ADR-039 reference implementation.

The phased approach allows incremental delivery and testing, with Phase 4 (Plan Executor) being the integration point that proves the architecture.

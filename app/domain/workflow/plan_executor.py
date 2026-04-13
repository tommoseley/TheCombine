"""Plan Executor for Document Interaction Workflow Plans (ADR-039).

The PlanExecutor is the main orchestrator that executes document workflows.
It coordinates node executors, edge routing, and state persistence.

INVARIANTS (WS-INTAKE-ENGINE-001):

Execution Invariants:
- Every node execution MUST produce exactly ONE outcome
- Outcome vocabulary per node type is fixed (executors enforce this)
- State is persisted after EVERY node completion

Separation Invariants:
- Executors perform work, Router performs control
- PlanExecutor orchestrates but does not make routing decisions
- Node executors MUST NOT access edges or mutate control state

Audit Invariants:
- Every node execution is logged with timestamp
- State transitions are recorded in node_history
- Retry counts are tracked per (project_id, generating_node_id)

Thread Ownership (WS-ADR-025 Phase 3):
- Workflows that declare thread_ownership.owns_thread create durable threads
- Conversation history is persisted to thread ledger
- Threads can be resumed when workflow is interrupted
"""

import logging
import uuid

from typing import Any, Dict, List, Optional, Protocol

from app.domain.workflow.plan_models import Node, NodeType, WorkflowPlan
from app.domain.workflow.plan_registry import PlanRegistry, get_plan_registry
from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
)
from app.domain.workflow.edge_router import EdgeRouter
from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)
from app.domain.workflow.thread_manager import ThreadManager
from app.domain.workflow.outcome_recorder import OutcomeRecorder
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Extracted sub-modules
from app.domain.workflow import qa_retry_handler
from app.domain.workflow import invariant_processor
from app.domain.workflow import child_document_manager
from app.domain.workflow import execution_event_emitter
from app.domain.workflow import execution_recorder
from app.domain.workflow import pgc_processor
from app.domain.workflow import document_persistence
from app.domain.workflow import execution_context_builder
from app.domain.workflow import execution_queries

# Domain-level protocols for mechanical operations (WS-CLEANUP-003)
from app.domain.workflow.operations import (
    OperationProvider,
    OperationExecutor,
    ExclusionFilter,
)

logger = logging.getLogger(__name__)


class StatePersistence(Protocol):
    """Protocol for state persistence backends."""

    async def save(self, state: DocumentWorkflowState) -> None:
        """Save workflow state."""
        ...

    async def load(self, execution_id: str) -> Optional[DocumentWorkflowState]:
        """Load workflow state by execution ID."""
        ...

    async def load_by_document(
        self, project_id: str, workflow_id: str
    ) -> Optional[DocumentWorkflowState]:
        """Load workflow state by document and workflow ID."""
        ...

    async def list_executions(
        self,
        status_filter: Optional[List[DocumentWorkflowStatus]] = None,
        limit: int = 100,
    ) -> List[DocumentWorkflowState]:
        """List executions, optionally filtered by status."""
        ...


class InMemoryStatePersistence:
    """In-memory state persistence for testing."""

    def __init__(self):
        self._states: Dict[str, DocumentWorkflowState] = {}

    async def save(self, state: DocumentWorkflowState) -> None:
        """Save state to memory."""
        self._states[state.execution_id] = state

    async def load(self, execution_id: str) -> Optional[DocumentWorkflowState]:
        """Load state from memory."""
        return self._states.get(execution_id)

    async def load_by_document(
        self, project_id: str, workflow_id: str
    ) -> Optional[DocumentWorkflowState]:
        """Load state by document and workflow."""
        for state in self._states.values():
            if state.project_id == project_id and state.workflow_id == workflow_id:
                return state
        return None

    async def list_executions(
        self,
        status_filter: Optional[List[DocumentWorkflowStatus]] = None,
        limit: int = 100,
    ) -> List[DocumentWorkflowState]:
        """List executions, optionally filtered by status."""
        states = list(self._states.values())

        # Filter by status if specified
        if status_filter:
            states = [s for s in states if s.status in status_filter]

        # Sort by updated_at descending (most recent first)
        states.sort(key=lambda s: s.updated_at, reverse=True)

        # Apply limit
        return states[:limit]


class PlanExecutorError(Exception):
    """Error during plan execution."""
    pass


class PlanExecutor:
    """Executes Document Interaction Workflow Plans.

    The PlanExecutor is responsible for:
    1. Loading workflow plans from the registry
    2. Managing execution state (create, load, persist)
    3. Dispatching to node executors based on node type
    4. Using EdgeRouter to determine next node after each execution
    5. Handling pause/resume for human-in-the-loop interactions
    6. Recording execution history for audit

    INVARIANT: PlanExecutor orchestrates but does NOT make routing decisions.
    All routing decisions are made by EdgeRouter based on outcomes and state.
    """

    def __init__(
        self,
        persistence: StatePersistence,
        plan_registry: Optional[PlanRegistry] = None,
        executors: Optional[Dict[NodeType, NodeExecutor]] = None,
        thread_manager: Optional[ThreadManager] = None,
        outcome_recorder: Optional[OutcomeRecorder] = None,
        db_session: Optional[AsyncSession] = None,
        ops_service: Optional["OperationProvider"] = None,
        operation_provider: Optional[OperationProvider] = None,
        operation_executor: Optional[OperationExecutor] = None,
        exclusion_filter: Optional[ExclusionFilter] = None,
    ):
        """Initialize the executor.

        Args:
            persistence: State persistence backend
            plan_registry: Optional plan registry (uses global if not provided)
            executors: Optional dict mapping NodeType to NodeExecutor instances.
                       If not provided, uses minimal stub executors for testing.
            thread_manager: Optional thread manager for conversation persistence.
                           If provided, enables thread ownership for workflows.
            outcome_recorder: Optional outcome recorder for governance audit.
                             If provided, records dual outcomes on completion.
            ops_service: Deprecated alias for operation_provider (backward compat).
            operation_provider: Protocol for fetching operation definitions.
            operation_executor: Protocol for executing mechanical operations.
            exclusion_filter: Protocol for filtering excluded topics.
        """
        self._persistence = persistence
        self._plan_registry = plan_registry or get_plan_registry()
        self._thread_manager = thread_manager
        self._outcome_recorder = outcome_recorder
        self._db_session = db_session

        # Domain-level protocols (WS-CLEANUP-003)
        self._ops_service = operation_provider or ops_service
        self._operation_executor = operation_executor
        self._exclusion_filter = exclusion_filter

        # Lazy-create default adapters if not injected
        if self._ops_service is None or self._operation_executor is None or self._exclusion_filter is None:
            self._ensure_default_operations()

        # Node executors by type - injectable for testing
        if executors:
            self._executors = executors
        else:
            # Default to minimal stub executors
            # In production, inject properly configured executors
            self._executors: Dict[NodeType, NodeExecutor] = {}

    def _ensure_default_operations(self):
        """Populate unset operation protocols from the default factory registry."""
        from app.domain.workflow.operations import (
            get_default_provider,
            get_default_executor,
            get_default_filter,
        )
        if self._ops_service is None:
            self._ops_service = get_default_provider()
        if self._operation_executor is None:
            self._operation_executor = get_default_executor()
        if self._exclusion_filter is None:
            self._exclusion_filter = get_default_filter()

    async def start_execution(
        self,
        project_id: str,
        document_type: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> DocumentWorkflowState:
        """Start a new workflow execution for a document.

        Args:
            project_id: The document being processed
            document_type: Type of document (determines which plan to use)
            initial_context: Optional initial context data

        Returns:
            The created execution state

        Raises:
            PlanExecutorError: If plan not found or execution fails
        """
        # Load plan for document type
        plan = self._plan_registry.get_by_document_type(document_type)
        if not plan:
            raise PlanExecutorError(
                f"No workflow plan found for document type: {document_type}"
            )

        # Check for existing execution
        existing = await self._persistence.load_by_document(
            project_id, plan.workflow_id
        )
        if existing and existing.status not in (
            DocumentWorkflowStatus.COMPLETED,
            DocumentWorkflowStatus.FAILED,
        ):
            logger.info(
                f"Resuming existing execution {existing.execution_id} "
                f"for document {project_id}"
            )
            return existing

        # Create new execution state
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        entry_node = plan.get_entry_node()
        if not entry_node:
            raise PlanExecutorError(f"Plan {plan.workflow_id} has no entry node")

        # Check if plan declares thread ownership
        thread_id = None
        if self._thread_manager and plan.thread_ownership.owns_thread:
            thread_id = await self._thread_manager.create_workflow_thread(
                workflow_id=plan.workflow_id,
                project_id=project_id,
                document_type=document_type,
                execution_id=execution_id,
                thread_purpose=plan.thread_ownership.thread_purpose,
            )
            logger.info(
                f"Created thread {thread_id} for execution {execution_id}"
            )

        state = DocumentWorkflowState(
            execution_id=execution_id,
            workflow_id=plan.workflow_id,
            project_id=project_id,
            document_type=document_type,
            current_node_id=entry_node.node_id,
            status=DocumentWorkflowStatus.PENDING,
            thread_id=thread_id,
            context_state=initial_context or {},
        )

        # Save initial state
        await self._persistence.save(state)

        # WS-STATION-DATA-001 Phase 2: Emit stations_declared event
        await self._emit_stations_declared(plan, state)

        # WS-STATION-DATA-001 Phase 2: Emit initial station_changed for entry node
        await self._emit_station_changed(plan, state, entry_node.node_id, "active")

        # Emit initial internal_step if entry node has internals
        if entry_node.internals:
            first_phase = list(entry_node.internals.keys())[0]
            await self._emit_internal_step(plan, state, entry_node, first_phase)

        logger.info(
            f"Started execution {execution_id} for document {project_id} "
            f"at node {entry_node.node_id}"
        )

        return state

    async def execute_step(
        self,
        execution_id: str,
        user_input: Optional[Any] = None,
        user_choice: Optional[str] = None,
    ) -> DocumentWorkflowState:
        """Execute the next step in the workflow.

        This method executes the current node and advances to the next
        based on the outcome. If the node requires user input, execution
        pauses and the state reflects the pending input.

        Args:
            execution_id: The execution to advance
            user_input: Optional user input (for paused executions)
            user_choice: Optional user choice (for gate nodes)

        Returns:
            Updated execution state

        Raises:
            PlanExecutorError: If execution fails
        """
        # Load state
        state = await self._persistence.load(execution_id)
        if not state:
            raise PlanExecutorError(f"Execution not found: {execution_id}")

        # Check if already terminal
        if state.status in (
            DocumentWorkflowStatus.COMPLETED,
            DocumentWorkflowStatus.FAILED,
        ):
            logger.info(f"Execution {execution_id} already terminal: {state.status}")
            return state

        # Load plan
        plan = self._plan_registry.get(state.workflow_id)
        if not plan:
            raise PlanExecutorError(f"Plan not found: {state.workflow_id}")

        # Get current node
        current_node = plan.get_node(state.current_node_id)
        if not current_node:
            raise PlanExecutorError(
                f"Node not found: {state.current_node_id} in plan {plan.workflow_id}"
            )

        # Build execution context
        context = await self._build_context(state, plan, user_input, user_choice)

        # Clear pause state if we have user input
        if state.pending_user_input and (user_input or user_choice):
            state.clear_pause()

            # Special handling for PGC nodes: store answers and advance to generation
            if current_node.type == NodeType.PGC and user_input:
                return await self._handle_pgc_user_answers(
                    execution_id, current_node, state, plan, user_input
                )

        # Update status to running
        state.status = DocumentWorkflowStatus.RUNNING

        # Load PGC answers from database for QA nodes (WS-PGC-VALIDATION-001 Phase 2)
        if current_node.is_qa_gate() and self._db_session:
            await self._load_pgc_answers_for_qa(state, context)

        # Execute the node
        try:
            result = await self._execute_node(current_node, context, state)
        except Exception as e:
            logger.exception(f"Node execution failed: {e}")
            state.set_failed(str(e))
            await self._persistence.save(state)
            raise PlanExecutorError(f"Node execution failed: {e}") from e

        # Emit internal_step event based on result and phase transitions
        if current_node.internals:
            if result.requires_user_input and "entry" in current_node.internals:
                # Transitioning to UI entry phase (waiting for user input)
                await self._emit_internal_step(plan, state, current_node, "entry")
            elif result.metadata and result.metadata.get("phase"):
                # Emit the phase from result (e.g., "merge" after user submits)
                await self._emit_internal_step(
                    plan, state, current_node, result.metadata["phase"]
                )

        # Persist conversation turns to thread (if applicable)
        await self._persist_conversation(result, current_node, state, context)

        # Handle result
        await self._handle_result(result, current_node, state, plan)

        # Update thread status on workflow completion/failure
        await self._sync_thread_status(state)

        # Persist state (INVARIANT: persist after every node completion)
        await self._persistence.save(state)

        return state

    async def run_to_completion_or_pause(
        self,
        execution_id: str,
        max_steps: int = 100,
    ) -> DocumentWorkflowState:
        """Run execution until it completes or pauses for user input.

        This is a convenience method that repeatedly calls execute_step
        until the workflow reaches a terminal state or pauses.

        Args:
            execution_id: The execution to run
            max_steps: Maximum steps to prevent infinite loops

        Returns:
            Final execution state

        Raises:
            PlanExecutorError: If execution fails or max steps exceeded
        """
        for step in range(max_steps):
            state = await self._persistence.load(execution_id)
            if not state:
                raise PlanExecutorError(f"Execution not found: {execution_id}")

            # Check terminal conditions
            if state.status == DocumentWorkflowStatus.COMPLETED:
                logger.info(
                    f"Execution {execution_id} completed with outcome: "
                    f"{state.terminal_outcome}"
                )
                return state

            if state.status == DocumentWorkflowStatus.FAILED:
                logger.info(f"Execution {execution_id} failed")
                return state

            if state.status == DocumentWorkflowStatus.PAUSED:
                logger.info(
                    f"Execution {execution_id} paused for user input at "
                    f"{state.current_node_id}"
                )
                return state

            # Execute next step
            state = await self.execute_step(execution_id)

        raise PlanExecutorError(
            f"Execution {execution_id} exceeded max steps ({max_steps})"
        )

    async def submit_user_input(
        self,
        execution_id: str,
        user_input: Optional[Any] = None,
        user_choice: Optional[str] = None,
    ) -> DocumentWorkflowState:
        """Submit user input for a paused execution.

        Args:
            execution_id: The paused execution
            user_input: User's text input
            user_choice: User's choice selection

        Returns:
            Updated execution state after processing input

        Raises:
            PlanExecutorError: If execution not paused or input invalid
        """
        state = await self._persistence.load(execution_id)
        if not state:
            raise PlanExecutorError(f"Execution not found: {execution_id}")

        if state.status != DocumentWorkflowStatus.PAUSED:
            raise PlanExecutorError(
                f"Execution {execution_id} is not paused "
                f"(status: {state.status.value})"
            )

        # Execute with user input
        return await self.execute_step(
            execution_id,
            user_input=user_input,
            user_choice=user_choice,
        )

    async def handle_escalation_choice(
        self,
        execution_id: str,
        choice: str,
    ) -> DocumentWorkflowState:
        """Handle user's escalation choice (circuit breaker).

        Args:
            execution_id: The execution with active escalation
            choice: User's selected escalation option

        Returns:
            Updated execution state

        Raises:
            PlanExecutorError: If no escalation active or invalid choice
        """
        state = await self._persistence.load(execution_id)
        if not state:
            raise PlanExecutorError(f"Execution not found: {execution_id}")

        if not state.escalation_active:
            raise PlanExecutorError(
                f"Execution {execution_id} has no active escalation"
            )

        if choice not in state.escalation_options:
            raise PlanExecutorError(
                f"Invalid escalation choice: {choice}. "
                f"Valid options: {state.escalation_options}"
            )

        # Clear escalation and record choice
        state.clear_escalation()
        state.record_execution(
            node_id=state.current_node_id,
            outcome="escalation_resolved",
            metadata={"escalation_choice": choice},
        )

        # Handle based on choice
        if choice == "abandon":
            state.set_completed("abandoned", gate_outcome="escalation_abandon")
        elif choice == "retry":
            # Reset retry count for the GENERATING node (not current QA node).
            # Retry counts are keyed by generating_node_id per WS-INTAKE-ENGINE-001.
            retry_key = state.generating_node_id or state.current_node_id
            state.retry_counts[retry_key] = 0
            state.status = DocumentWorkflowStatus.RUNNING
        else:
            # Other choices may need custom handling
            state.status = DocumentWorkflowStatus.RUNNING

        await self._persistence.save(state)
        return state

    async def cancel_execution(
        self,
        execution_id: str,
    ) -> DocumentWorkflowState:
        """Cancel a running or paused workflow execution (WS-RING0-002).

        Args:
            execution_id: The execution to cancel

        Returns:
            Updated execution state with status=completed, terminal_outcome=cancelled

        Raises:
            PlanExecutorError: If execution not found or already in terminal state
        """
        state = await self._persistence.load(execution_id)
        if not state:
            raise PlanExecutorError(f"Execution not found: {execution_id}")

        # Only running or paused executions can be cancelled
        if state.status not in (
            DocumentWorkflowStatus.RUNNING,
            DocumentWorkflowStatus.PAUSED,
        ):
            raise PlanExecutorError(
                f"Cannot cancel execution in state '{state.status.value}'. "
                f"Only running or paused executions can be cancelled."
            )

        # Clear any active escalation or pause state
        if state.escalation_active:
            state.clear_escalation()
        if state.pending_user_input:
            state.clear_pause()

        # Set terminal state
        state.set_completed("cancelled", gate_outcome="operator_cancelled")
        state.record_execution(
            node_id=state.current_node_id,
            outcome="cancelled",
            metadata={"cancelled_by": "operator"},
        )

        await self._persistence.save(state)
        return state

    async def _build_context(self, state, plan, user_input, user_choice):
        return await execution_context_builder.build_context(
            state, plan, user_input, user_choice, self._db_session, self._thread_manager,
        )

    async def _execute_node(
        self,
        node: Node,
        context: DocumentWorkflowContext,
        state: DocumentWorkflowState,
    ) -> NodeResult:
        """Execute a node using the appropriate executor."""
        executor = self._executors.get(node.type)
        if not executor:
            raise PlanExecutorError(f"No executor for node type: {node.type}")

        # Build node config from Node dataclass
        node_config = {
            "node_id": node.node_id,
            "type": node.type.value,
            "description": node.description,
            "task_ref": node.task_ref,
            "produces": node.produces,
            "requires_consent": node.requires_consent,
            "requires_qa": node.requires_qa,
            "gate_outcomes": node.gate_outcomes,
            "terminal_outcome": node.terminal_outcome,
            "gate_outcome": node.gate_outcome,
            "includes": node.includes,  # ADR-041 template includes
            "internals": node.internals,  # ADR-047 Gate Profile internals
        }

        # Build state snapshot
        state_snapshot = state.to_dict()

        logger.debug(f"Executing node {node.node_id} (type: {node.type.value})")

        result = await executor.execute(
            node_id=node.node_id,
            node_config=node_config,
            context=context,
            state_snapshot=state_snapshot,
        )

        logger.debug(f"Node {node.node_id} returned outcome: {result.outcome}")

        return result

    async def _handle_result(
        self,
        result: NodeResult,
        current_node: Node,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
    ) -> None:
        """Handle the result of a node execution.

        Orchestrates 5 concerns via sub-methods (WS-CRAP-008):
        1. Records the execution in history
        2. Handles pause/user input requirements
        3. Stores produced documents in context
        4. Handles intake gate pause-for-review
        5. Routes to next node (terminal, non-advancing, or advance)
        6. Manages QA retry feedback
        """
        # 1. Record execution in history
        execution_metadata = dict(result.metadata) if result.metadata else {}
        if result.user_prompt:
            execution_metadata["user_prompt"] = result.user_prompt
        state.record_execution(
            node_id=current_node.node_id,
            outcome=result.outcome,
            metadata=execution_metadata,
        )

        # 2. User input pause
        if await self._handle_user_input_pause(result, state):
            return

        # 3. Produced document storage
        await self._store_produced_document(result, state)

        # 4. Intake gate handling
        if await self._handle_intake_gate_result(result, current_node, state, plan):
            return

        # 5. Pre-routing: Set generating_node_id for QA failures
        self._prepare_qa_retry_tracking(result, current_node, state, plan)

        # 6. Route via EdgeRouter
        router = EdgeRouter(plan)
        next_node_id, matched_edge = router.get_next_node(
            current_node_id=current_node.node_id,
            outcome=result.outcome,
            state=state,
        )

        # 7. Non-advancing edge (circuit breaker)
        if matched_edge and matched_edge.to_node_id is None:
            if matched_edge.escalation_options:
                state.set_escalation(matched_edge.escalation_options)
            else:
                logger.warning(
                    f"Non-advancing edge without escalation options at "
                    f"{current_node.node_id}"
                )
            return

        # 8. No matching edge -> error
        if next_node_id is None:
            logger.error(
                f"No matching edge from {current_node.node_id} "
                f"with outcome '{result.outcome}'"
            )
            await self._emit_station_changed(plan, state, current_node.node_id, "blocked")
            state.set_failed(
                f"No routing edge for outcome '{result.outcome}' "
                f"from node {current_node.node_id}"
            )
            return

        # 9. Terminal node
        if router.is_terminal_node(next_node_id):
            await self._handle_terminal_node(
                router, next_node_id, current_node, result, state, plan,
            )
            return

        # 10. Station transitions + advance
        await self._advance_to_next_node(
            current_node, next_node_id, state, plan,
        )

        # 11. QA retry/feedback
        self._handle_qa_retry_feedback(result, current_node, state)

    # =========================================================================
    # Sub-methods extracted from _handle_result (WS-CRAP-008)
    # =========================================================================

    async def _handle_user_input_pause(
        self,
        result: NodeResult,
        state: DocumentWorkflowState,
    ) -> bool:
        """Handle user input requirement. Returns True if execution paused."""
        if not result.requires_user_input:
            return False

        logger.info(
            f"Setting paused state with payload={result.user_input_payload is not None}, "
            f"schema_ref={result.user_input_schema_ref}"
        )

        # Store Gate Profile metadata in context_state for resumption (ADR-047)
        from app.domain.workflow.result_handling import extract_metadata_by_keys, GATE_PROFILE_KEYS

        gate_metadata = extract_metadata_by_keys(result.metadata, GATE_PROFILE_KEYS)
        if gate_metadata:
            state.update_context_state(gate_metadata)
            logger.info(f"Stored Gate Profile metadata: {list(gate_metadata.keys())}")

        state.set_paused(
            prompt=result.user_prompt,
            choices=result.user_choices,
            payload=result.user_input_payload,
            schema_ref=result.user_input_schema_ref,
        )
        return True

    async def _store_produced_document(self, result, state):
        await document_persistence.store_produced_document(
            result.produced_document, result.metadata, state,
            self._pin_invariants_via_operation, self._filter_excluded_via_operation,
        )

    async def _handle_intake_gate_result(self, result, current_node, state, plan):
        return await document_persistence.handle_intake_gate_result(
            result.outcome, result.metadata, current_node, state, plan, self._persistence,
        )

    async def _handle_terminal_node(
        self,
        router: EdgeRouter,
        next_node_id: str,
        current_node: Node,
        result: NodeResult,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
    ) -> None:
        """Handle terminal node: set completed, record governance, persist documents."""
        terminal_outcome = router.get_terminal_outcome(next_node_id)

        # Get gate outcome: prefer end node definition, fallback to result metadata
        gate_outcome = router.get_gate_outcome(next_node_id)
        if not gate_outcome:
            gate_outcome = result.metadata.get("gate_outcome")

        # Detect circuit breaker trigger
        if (
            current_node.is_qa_gate()
            and result.outcome == "failed"
            and terminal_outcome == "blocked"
        ):
            retry_count = (
                state.get_retry_count(state.generating_node_id)
                if state.generating_node_id else 0
            )
            logger.warning(
                f"CIRCUIT BREAKER TRIPPED: QA failed {retry_count} times for "
                f"{state.generating_node_id}, routing to {next_node_id}"
            )

        state.current_node_id = next_node_id

        # WS-STATION-DATA-001 Phase 2: Station events
        current_station = plan.get_node_station(current_node.node_id)
        if current_station:
            await self._emit_station_changed(plan, state, current_node.node_id, "complete")
        await self._emit_station_changed(plan, state, next_node_id, "complete")

        state.set_completed(
            terminal_outcome=terminal_outcome,
            gate_outcome=gate_outcome,
        )

        # Record governance outcome (ADR-037)
        await self._record_governance_outcome(state, plan, result)

        # Persist produced documents on successful completion
        if terminal_outcome == "stabilized":
            await self._persist_produced_documents(state, plan)

        logger.info(
            f"Execution {state.execution_id} reached terminal: "
            f"{terminal_outcome} (gate: {gate_outcome})"
        )

    async def _advance_to_next_node(
        self,
        current_node: Node,
        next_node_id: str,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
    ) -> None:
        """Advance state to next node, emitting station change events."""
        current_station = plan.get_node_station(current_node.node_id)
        next_station = plan.get_node_station(next_node_id)

        if current_station and (not next_station or current_station.id != next_station.id):
            await self._emit_station_changed(plan, state, current_node.node_id, "complete")

        state.current_node_id = next_node_id

        if next_station and (not current_station or next_station.id != current_station.id):
            await self._emit_station_changed(plan, state, next_node_id, "active")

    # =========================================================================
    # Delegation to extracted sub-modules
    # =========================================================================

    # -- QA retry handler --
    def _prepare_qa_retry_tracking(self, result, current_node, state, plan):
        qa_retry_handler.prepare_qa_retry_tracking(result, current_node, state, plan)

    def _handle_qa_retry_feedback(self, result, current_node, state):
        qa_retry_handler.handle_qa_retry_feedback(result, current_node, state)

    def _extract_qa_feedback(self, result):
        return qa_retry_handler.extract_qa_feedback(result)

    def _find_generating_node(self, state, plan):
        return qa_retry_handler.find_generating_node(state, plan)

    # -- Invariant processor --
    async def _pin_invariants_via_operation(self, document, state):
        return await invariant_processor.pin_invariants_via_operation(
            document, state, self._ops_service, self._operation_executor
        )

    async def _filter_excluded_via_operation(self, document, state):
        return await invariant_processor.filter_excluded_via_operation(
            document, state, self._ops_service, self._operation_executor
        )

    def _pin_invariants_to_known_constraints(self, document, state):
        return invariant_processor.pin_invariants_to_known_constraints(document, state)

    def _filter_excluded_topics(self, document, state):
        return invariant_processor.filter_excluded_topics(document, state, self._exclusion_filter)

    def _promote_pgc_invariants_to_document(self, doc_content, state):
        invariant_processor.promote_pgc_invariants_to_document(
            doc_content, state, self._derive_constraint_domain, self._build_invariant_statement
        )

    def _embed_pgc_clarifications(self, doc_content, state):
        invariant_processor.embed_pgc_clarifications(doc_content, state)

    def _derive_constraint_domain(self, constraint_id):
        return invariant_processor.derive_constraint_domain(constraint_id)

    def _build_invariant_statement(self, constraint_id, question_text, answer_label, binding_source):
        return invariant_processor.build_invariant_statement(
            constraint_id, question_text, answer_label, binding_source
        )

    # -- Child document manager --
    async def _spawn_child_documents(self, state, doc_content, parent_id, parent_title, execution_id=None):
        await child_document_manager.spawn_child_documents(
            state, doc_content, parent_id, parent_title, self._db_session, execution_id
        )

    async def _upsert_child_document(self, spec, existing_children, state, parent_id):
        return await child_document_manager.upsert_child_document(
            spec, existing_children, state, parent_id, self._db_session
        )

    def _mark_stale_children(self, existing_children, spawned_ids):
        return child_document_manager.mark_stale_children(existing_children, spawned_ids)

    async def _load_existing_children(self, parent_id, child_specs, Document):
        return await child_document_manager.load_existing_children(
            parent_id, child_specs, Document, self._db_session
        )

    async def _run_upsert_loop(self, child_specs, existing_children, state, parent_id):
        return await child_document_manager.run_upsert_loop(
            child_specs, existing_children, state, parent_id, self._db_session
        )

    async def _commit_and_notify_children(self, created_count, updated_count, superseded_count,
                                           state, parent_id, child_specs, existing_children,
                                           spawned_ids, build_children_event_payload):
        await child_document_manager.commit_and_notify_children(
            created_count, updated_count, superseded_count,
            state, parent_id, child_specs, existing_children, spawned_ids,
            build_children_event_payload, self._db_session,
        )

    # -- Execution event emitter --
    async def _emit_stations_declared(self, plan, state):
        await execution_event_emitter.emit_stations_declared(plan, state)

    async def _emit_station_changed(self, plan, state, node_id, station_state, phase=None):
        await execution_event_emitter.emit_station_changed(plan, state, node_id, station_state, phase)

    async def _emit_internal_step(self, plan, state, node, phase_key):
        await execution_event_emitter.emit_internal_step(plan, state, node, phase_key)

    # -- Execution recorder --
    async def _persist_conversation(self, result, node, state, context):
        await execution_recorder.persist_conversation(result, node, state, context, self._thread_manager)

    async def _sync_thread_status(self, state):
        await execution_recorder.sync_thread_status(state, self._thread_manager)

    async def _record_governance_outcome(self, state, plan, result):
        await execution_recorder.record_governance_outcome(state, plan, result, self._outcome_recorder)

    # -- PGC processor --
    async def _handle_pgc_user_answers(self, execution_id, current_node, state, plan, user_input):
        return await pgc_processor.handle_pgc_user_answers(
            execution_id, current_node, state, plan, user_input,
            self._ops_service, self._operation_executor, self._persistence, self._db_session,
            self._emit_internal_step, self.execute_step,
        )

    async def _get_pgc_questions_for_merge(self, state):
        return await pgc_processor.get_pgc_questions_for_merge(state, self._db_session)

    async def _load_pgc_answers_for_qa(self, state, context):
        await pgc_processor.load_pgc_answers_for_qa(state, context, self._db_session, self._ops_service, self._operation_executor)

    # =========================================================================
    # Document persistence (kept in core - touches multiple DB concerns)
    # =========================================================================

    async def _persist_produced_documents(self, state, plan):
        if not self._db_session:
            logger.warning("No db_session - skipping document persistence")
            return
        await document_persistence.persist_produced_documents(
            state, plan, self._db_session, self._persistence,
            self._derive_constraint_domain, self._build_invariant_statement,
            self._spawn_child_documents,
        )

    # =========================================================================
    # Query methods
    # =========================================================================

    async def get_execution_status(self, execution_id):
        return await execution_queries.get_execution_status(self._persistence, execution_id)

    async def list_executions(self, status_filter=None, limit=100):
        return await execution_queries.list_executions(self._persistence, status_filter, limit)

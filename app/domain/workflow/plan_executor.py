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
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol

from app.domain.workflow.plan_models import Node, NodeType, WorkflowPlan
from app.domain.workflow.plan_registry import PlanRegistry, get_plan_registry
from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
)
from app.domain.workflow.edge_router import EdgeRouter
from app.domain.workflow.outcome_mapper import OutcomeMapper
from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    NodeExecutor,
    NodeResult,
)
from app.domain.workflow.thread_manager import ThreadManager
from app.domain.workflow.outcome_recorder import OutcomeRecorder
from sqlalchemy.ext.asyncio import AsyncSession

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
        """
        self._persistence = persistence
        self._plan_registry = plan_registry or get_plan_registry()
        self._thread_manager = thread_manager
        self._outcome_recorder = outcome_recorder
        self._db_session = db_session

        # Node executors by type - injectable for testing
        if executors:
            self._executors = executors
        else:
            # Default to minimal stub executors
            # In production, inject properly configured executors
            self._executors: Dict[NodeType, NodeExecutor] = {}

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
            # Don't re-execute PGC - that would generate new questions
            if current_node.type == NodeType.PGC and user_input:
                logger.info(f"PGC node {current_node.node_id} received user answers - advancing to generation")
                state.update_context_state({"pgc_answers": user_input})
                
                # Route to next node using "success" outcome (user answered, proceed)
                router = EdgeRouter(plan)
                next_node_id, edge = router.get_next_node(
                    current_node_id=current_node.node_id,
                    outcome="success",
                    state=state,
                )
                if next_node_id:
                    state.current_node_id = next_node_id
                    state.status = DocumentWorkflowStatus.RUNNING
                    await self._persistence.save(state)
                    # Continue execution at the new node
                    return await self.execute_step(execution_id)
                else:
                    raise PlanExecutorError(f"No edge from PGC node {current_node.node_id} with outcome 'success'")

        # Update status to running
        state.status = DocumentWorkflowStatus.RUNNING

        # Execute the node
        try:
            result = await self._execute_node(current_node, context, state)
        except Exception as e:
            logger.exception(f"Node execution failed: {e}")
            state.set_failed(str(e))
            await self._persistence.save(state)
            raise PlanExecutorError(f"Node execution failed: {e}") from e

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
            # Reset retry count and continue
            state.retry_counts[state.current_node_id] = 0
            state.status = DocumentWorkflowStatus.RUNNING
        else:
            # Other choices may need custom handling
            state.status = DocumentWorkflowStatus.RUNNING

        await self._persistence.save(state)
        return state

    async def _build_context(
        self,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
        user_input: Optional[Any],
        user_choice: Optional[str],
    ) -> DocumentWorkflowContext:
        """Build execution context for a node.

        Args:
            state: Current execution state
            plan: Workflow plan
            user_input: Optional user input
            user_choice: Optional user choice

        Returns:
            DocumentWorkflowContext for node execution
        """
        # Build extra context with execution metadata
        extra = {
            "execution_id": state.execution_id,
            "workflow_id": state.workflow_id,
            "retry_count": state.get_retry_count(state.current_node_id),
        }
        if user_input:
            extra["user_input"] = user_input
        if user_choice:
            extra["user_choice"] = user_choice

        # Load conversation history from thread if available
        conversation_history = []
        if state.thread_id and self._thread_manager:
            try:
                conversation_history = await self._thread_manager.load_conversation_history(
                    state.thread_id
                )
                logger.debug(
                    f"Loaded {len(conversation_history)} messages from thread {state.thread_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to load conversation history: {e}")

        # Load produced documents from context_state
        document_content = {}
        for key, value in state.context_state.items():
            if key.startswith("document_") and isinstance(value, dict):
                # Extract document type from key (e.g., "document_discovery" -> "discovery")
                doc_type = key[len("document_"):]
                document_content[doc_type] = value

        # Also include last_produced_document for easy access
        if state.context_state.get("last_produced_document"):
            document_content["_last"] = state.context_state["last_produced_document"]

        logger.debug(f"Loaded {len(document_content)} documents from context_state")

        return DocumentWorkflowContext(
            project_id=state.project_id,
            document_type=state.document_type,
            thread_id=state.thread_id,
            document_content=document_content,
            conversation_history=conversation_history,
            input_documents=state.context_state.get("input_documents", {}),
            user_responses={},
            extra=extra,
            context_state=state.context_state,
        )

    async def _execute_node(
        self,
        node: Node,
        context: DocumentWorkflowContext,
        state: DocumentWorkflowState,
    ) -> NodeResult:
        """Execute a node using the appropriate executor.

        Args:
            node: The node to execute
            context: Execution context
            state: Current state (for snapshot)

        Returns:
            NodeResult from executor
        """
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

        This method:
        1. Records the execution in history
        2. Handles pause/user input requirements
        3. Uses EdgeRouter to determine next node
        4. Updates state with next node or terminal outcome

        Args:
            result: The node execution result
            current_node: The node that was executed
            state: Current execution state
            plan: Workflow plan
        """
        # Record execution in history (include user_prompt for clarification questions)
        execution_metadata = dict(result.metadata) if result.metadata else {}
        if result.user_prompt:
            execution_metadata["user_prompt"] = result.user_prompt
        state.record_execution(
            node_id=current_node.node_id,
            outcome=result.outcome,
            metadata=execution_metadata,
        )

        # Handle user input requirement
        if result.requires_user_input:
            logger.info(f"Setting paused state with payload={result.user_input_payload is not None}, schema_ref={result.user_input_schema_ref}")
            state.set_paused(
                prompt=result.user_prompt,
                choices=result.user_choices,
                payload=result.user_input_payload,
                schema_ref=result.user_input_schema_ref,
            )
            return

        # Store produced document in context_state for subsequent nodes (e.g., QA)
        # Note: produced_document is a direct field on NodeResult, not in metadata
        if result.produced_document:
            produces_key = result.metadata.get("produces", "last_produced")
            state.update_context_state({
                f"document_{produces_key}": result.produced_document,
                "last_produced_document": result.produced_document,
            })
            logger.info(f"Stored produced document as document_{produces_key}")

        # Store intake gate metadata in context_state for downstream nodes
        # This includes: intake_summary, project_type, user_input, interpretation, phase
        if current_node.type == NodeType.INTAKE_GATE and result.outcome == "qualified":
            intake_metadata = {}
            for key in ["intake_summary", "project_type", "user_input", "intent_canon", "extracted_data", "interpretation", "phase"]:
                if key in result.metadata:
                    intake_metadata[key] = result.metadata[key]
            if intake_metadata:
                state.update_context_state(intake_metadata)
                logger.info(f"Stored intake gate metadata: {list(intake_metadata.keys())}")
            
            # Pause for user review if phase is "review" (WS-INTAKE-001)
            # But don't pause again if we're already past review (phase == "generating")
            current_phase = state.context_state.get("phase")
            if result.metadata.get("phase") == "review" and current_phase != "generating":
                # Advance to next node BEFORE pausing (so resume starts at generation, not intake)
                router = EdgeRouter(plan)
                next_node_id, _ = router.get_next_node(
                    current_node_id=current_node.node_id,
                    outcome=result.outcome,
                    state=state,
                )
                if next_node_id:
                    state.current_node_id = next_node_id
                    logger.info(f"Advanced to {next_node_id} before pausing for review")
                
                state.set_paused(prompt=None, choices=None)
                await self._persistence.save(state)
                logger.info("Intake qualified - pausing for user review")
                return  # Don't execute next node until user clicks Initialize

        # Pre-routing: Set generating_node_id for QA failures (needed by edge router)
        if current_node.type == NodeType.QA and result.outcome == "failed":
            generating_node_id = self._find_generating_node(state, plan)
            if generating_node_id:
                state.generating_node_id = generating_node_id

        # Use EdgeRouter to determine next node
        router = EdgeRouter(plan)
        next_node_id, matched_edge = router.get_next_node(
            current_node_id=current_node.node_id,
            outcome=result.outcome,
            state=state,
        )

        # Handle non-advancing edge (circuit breaker)
        if matched_edge and matched_edge.to_node_id is None:
            if matched_edge.escalation_options:
                state.set_escalation(matched_edge.escalation_options)
                return
            else:
                # Non-advancing without escalation - stay at current node
                logger.warning(
                    f"Non-advancing edge without escalation options at "
                    f"{current_node.node_id}"
                )
                return

        # No matching edge - error state
        if next_node_id is None:
            logger.error(
                f"No matching edge from {current_node.node_id} "
                f"with outcome '{result.outcome}'"
            )
            state.set_failed(
                f"No routing edge for outcome '{result.outcome}' "
                f"from node {current_node.node_id}"
            )
            return

        # Check if next node is terminal
        if router.is_terminal_node(next_node_id):
            terminal_outcome = router.get_terminal_outcome(next_node_id)

            # Get gate outcome: prefer end node definition, fallback to result metadata
            gate_outcome = router.get_gate_outcome(next_node_id)
            if not gate_outcome:
                gate_outcome = result.metadata.get("gate_outcome")

            state.current_node_id = next_node_id
            state.set_completed(
                terminal_outcome=terminal_outcome,
                gate_outcome=gate_outcome,
            )

            # Record governance outcome (ADR-037)
            await self._record_governance_outcome(state, plan, result)

            # Persist produced documents to database on successful completion
            if terminal_outcome == "stabilized":
                await self._persist_produced_documents(state, plan)

            logger.info(
                f"Execution {state.execution_id} reached terminal: "
                f"{terminal_outcome} (gate: {gate_outcome})"
            )
            return

        # Advance to next node
        state.current_node_id = next_node_id

        # Handle QA failure -> increment retry for generating node
        # Note: generating_node_id was already set on state before routing
        if (
            current_node.type == NodeType.QA
            and result.outcome == "failed"
            and state.generating_node_id
        ):
            retry_count = state.increment_retry(state.generating_node_id)
            logger.info(
                f"QA failed, incremented retry for {state.generating_node_id} "
                f"to {retry_count}"
            )

    def _find_generating_node(
        self,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
    ) -> Optional[str]:
        """Find the generating node for QA retry tracking.

        Looks back in execution history to find the last task node
        that generated content being QA'd.

        Args:
            state: Current execution state
            plan: Workflow plan

        Returns:
            Node ID of generating node or None
        """
        # Look back through history for the last task node
        for execution in reversed(state.node_history):
            node = plan.get_node(execution.node_id)
            if node and node.type == NodeType.TASK:
                return execution.node_id
        return None

    async def _persist_conversation(
        self,
        result: NodeResult,
        node: Node,
        state: DocumentWorkflowState,
        context: DocumentWorkflowContext,
    ) -> None:
        """Persist conversation turns to thread.

        Records user input and assistant responses to the thread ledger
        for conversation continuity.

        Args:
            result: The node execution result
            node: The executed node
            state: Current execution state
            context: Execution context with user input
        """
        if not state.thread_id or not self._thread_manager:
            return

        try:
            # Record user input if present
            user_input = context.extra.get("user_input")
            if user_input:
                # Convert dict to JSON string for thread recording
                import json
                content = json.dumps(user_input, indent=2) if isinstance(user_input, dict) else user_input
                await self._thread_manager.record_conversation_turn(
                    thread_id=state.thread_id,
                    role="user",
                    content=content,
                    node_id=node.node_id,
                )

            # Record assistant response if produced
            if result.produced_document:
                # For concierge nodes, the response might be in the document
                response_content = result.produced_document.get("response")
                if response_content:
                    await self._thread_manager.record_conversation_turn(
                        thread_id=state.thread_id,
                        role="assistant",
                        content=response_content,
                        node_id=node.node_id,
                    )

            # Record user prompt for paused states
            if result.requires_user_input and result.user_prompt:
                await self._thread_manager.record_conversation_turn(
                    thread_id=state.thread_id,
                    role="assistant",
                    content=result.user_prompt,
                    node_id=node.node_id,
                )

        except Exception as e:
            logger.warning(f"Failed to persist conversation to thread: {e}")

    async def _sync_thread_status(
        self,
        state: DocumentWorkflowState,
    ) -> None:
        """Sync thread status with workflow status.

        Updates thread status to match workflow completion/failure.

        Args:
            state: Current execution state
        """
        if not state.thread_id or not self._thread_manager:
            return

        try:
            if state.status == DocumentWorkflowStatus.RUNNING:
                await self._thread_manager.start_thread(state.thread_id)
            elif state.status == DocumentWorkflowStatus.COMPLETED:
                await self._thread_manager.complete_thread(state.thread_id)
            elif state.status == DocumentWorkflowStatus.FAILED:
                await self._thread_manager.fail_thread(state.thread_id)
        except Exception as e:
            logger.warning(f"Failed to sync thread status: {e}")

    async def _record_governance_outcome(
        self,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
        result: NodeResult,
    ) -> None:
        """Record governance outcome for audit (ADR-037).

        Records both gate outcome (governance vocabulary) and terminal outcome
        (execution vocabulary) to the governance_outcomes table.

        Args:
            state: The completed workflow state
            plan: The workflow plan
            result: The final node result
        """
        if not self._outcome_recorder:
            return

        if not state.gate_outcome or not state.terminal_outcome:
            logger.debug("Skipping outcome recording: no outcomes set")
            return

        try:
            # Extract options offered from result metadata if available
            options_offered = result.metadata.get("options_offered")
            option_selected = result.metadata.get("option_selected")
            selection_method = result.metadata.get("selection_method")

            await self._outcome_recorder.record_outcome(
                state=state,
                plan=plan,
                gate_type="intake_gate",  # Default for concierge intake
                options_offered=options_offered,
                option_selected=option_selected,
                selection_method=selection_method,
                recorded_by="workflow_engine",
            )
        except Exception as e:
            logger.warning(f"Failed to record governance outcome: {e}")

    async def _persist_produced_documents(
        self,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
    ) -> None:
        """Persist produced documents to the documents table.

        Called on successful workflow completion (stabilized).
        Saves the primary output document to the database.
        
        System-owned fields (meta.created_at, meta.artifact_id) are
        overwritten with system values - LLM must not mint these.

        Args:
            state: The completed workflow state
            plan: The workflow plan
        """
        if not self._db_session:
            logger.warning("No db_session - skipping document persistence")
            return

        # Import here to avoid circular dependencies
        from app.api.models.document import Document
        from uuid import UUID
        import copy

        # Find the primary produced document (e.g., document_project_discovery)
        doc_key = f"document_{state.document_type}"
        produced_doc = state.context_state.get(doc_key)
        
        if not produced_doc:
            logger.warning(f"No produced document found at {doc_key}")
            return

        try:
            # Deep copy to avoid mutating context_state
            doc_content = copy.deepcopy(produced_doc)
            
            # Enforce system-owned meta fields
            if "meta" not in doc_content:
                doc_content["meta"] = {}
            
            meta = doc_content["meta"]
            
            # Log if LLM minted values that differ from system values
            llm_created_at = meta.get("created_at")
            llm_artifact_id = meta.get("artifact_id")
            
            # System-owned: created_at = now
            system_created_at = datetime.utcnow().isoformat() + "Z"
            if llm_created_at and llm_created_at != system_created_at:
                logger.warning(
                    f"LLM minted meta.created_at={llm_created_at}, "
                    f"overwriting with system value"
                )
            meta["created_at"] = system_created_at
            
            # System-owned: artifact_id = execution_id based
            system_artifact_id = f"{state.document_type.upper()}-{state.execution_id}"
            if llm_artifact_id and llm_artifact_id != system_artifact_id:
                logger.warning(
                    f"LLM minted meta.artifact_id={llm_artifact_id}, "
                    f"overwriting with system value"
                )
            meta["artifact_id"] = system_artifact_id
            
            # Add provenance: correlation_id links to execution
            meta["correlation_id"] = state.execution_id
            meta["workflow_id"] = state.workflow_id

            # Create the document record
            document = Document(
                space_type="project",
                space_id=UUID(state.project_id),
                doc_type_id=state.document_type,
                title=doc_content.get("project_name", f"{state.document_type} Document"),
                content=doc_content,
                version=1,
                is_latest=True,
                status="draft",
                created_by=None,  # System-generated
            )
            document.update_revision_hash()

            self._db_session.add(document)
            await self._db_session.commit()
            
            # Update context_state with system-corrected document
            # so API responses show corrected values
            doc_key = f"document_{state.document_type}"
            state.context_state[doc_key] = doc_content
            await self._persistence.save(state)
            
            logger.info(
                f"Persisted {state.document_type} document to database "
                f"(id={document.id}, artifact_id={system_artifact_id}, project={state.project_id})"
            )

        except Exception as e:
            logger.error(f"Failed to persist document: {e}")
            # Don't fail the workflow - document is still in context_state
            await self._db_session.rollback()
    async def get_execution_status(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get current execution status.

        Args:
            execution_id: The execution ID

        Returns:
            Status dict or None if not found
        """
        state = await self._persistence.load(execution_id)
        if not state:
            return None

        return {
            "execution_id": state.execution_id,
            "project_id": state.project_id,
            "document_type": state.document_type,
            "workflow_id": state.workflow_id,
            "status": state.status.value,
            "current_node_id": state.current_node_id,
            "terminal_outcome": state.terminal_outcome,
            "gate_outcome": state.gate_outcome,
            "pending_user_input": state.pending_user_input,
            "pending_user_input_rendered": state.pending_user_input_rendered,
            "pending_choices": state.pending_choices,
            "pending_user_input_payload": state.pending_user_input_payload,
            "pending_user_input_schema_ref": state.pending_user_input_schema_ref,
            "escalation_active": state.escalation_active,
            "escalation_options": state.escalation_options,
            "step_count": len(state.node_history),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "produced_documents": {k: v for k, v in state.context_state.items() if k.startswith("document_")},
        }

    async def list_executions(
        self,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List workflow executions.

        Args:
            status_filter: Optional list of status values to filter by
                          (e.g., ["running", "paused"])
            limit: Maximum number of executions to return

        Returns:
            List of execution status dicts, sorted by most recent first
        """
        # Convert string statuses to enum if provided
        enum_filter = None
        if status_filter:
            enum_filter = [DocumentWorkflowStatus(s) for s in status_filter]

        states = await self._persistence.list_executions(
            status_filter=enum_filter,
            limit=limit,
        )

        return [
            {
                "execution_id": state.execution_id,
                "project_id": state.project_id,
                "document_type": state.document_type,
                "workflow_id": state.workflow_id,
                "status": state.status.value,
                "current_node_id": state.current_node_id,
                "terminal_outcome": state.terminal_outcome,
                "pending_user_input": state.pending_user_input,
                "step_count": len(state.node_history),
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat(),
            }
            for state in states
        ]

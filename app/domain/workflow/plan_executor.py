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
- Retry counts are tracked per (document_id, generating_node_id)
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
        self, document_id: str, workflow_id: str
    ) -> Optional[DocumentWorkflowState]:
        """Load workflow state by document and workflow ID."""
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
        self, document_id: str, workflow_id: str
    ) -> Optional[DocumentWorkflowState]:
        """Load state by document and workflow."""
        for state in self._states.values():
            if state.document_id == document_id and state.workflow_id == workflow_id:
                return state
        return None


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
    ):
        """Initialize the executor.

        Args:
            persistence: State persistence backend
            plan_registry: Optional plan registry (uses global if not provided)
            executors: Optional dict mapping NodeType to NodeExecutor instances.
                       If not provided, uses minimal stub executors for testing.
        """
        self._persistence = persistence
        self._plan_registry = plan_registry or get_plan_registry()

        # Node executors by type - injectable for testing
        if executors:
            self._executors = executors
        else:
            # Default to minimal stub executors
            # In production, inject properly configured executors
            self._executors: Dict[NodeType, NodeExecutor] = {}

    async def start_execution(
        self,
        document_id: str,
        document_type: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> DocumentWorkflowState:
        """Start a new workflow execution for a document.

        Args:
            document_id: The document being processed
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
            document_id, plan.workflow_id
        )
        if existing and existing.status not in (
            DocumentWorkflowStatus.COMPLETED,
            DocumentWorkflowStatus.FAILED,
        ):
            logger.info(
                f"Resuming existing execution {existing.execution_id} "
                f"for document {document_id}"
            )
            return existing

        # Create new execution state
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        entry_node = plan.get_entry_node()
        if not entry_node:
            raise PlanExecutorError(f"Plan {plan.workflow_id} has no entry node")

        state = DocumentWorkflowState(
            execution_id=execution_id,
            workflow_id=plan.workflow_id,
            document_id=document_id,
            document_type=document_type,
            current_node_id=entry_node.node_id,
            status=DocumentWorkflowStatus.PENDING,
        )

        # Save initial state
        await self._persistence.save(state)

        logger.info(
            f"Started execution {execution_id} for document {document_id} "
            f"at node {entry_node.node_id}"
        )

        return state

    async def execute_step(
        self,
        execution_id: str,
        user_input: Optional[str] = None,
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
        context = self._build_context(state, plan, user_input, user_choice)

        # Clear pause state if we have user input
        if state.pending_user_input and (user_input or user_choice):
            state.clear_pause()

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

        # Handle result
        await self._handle_result(result, current_node, state, plan)

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
        user_input: Optional[str] = None,
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

    def _build_context(
        self,
        state: DocumentWorkflowState,
        plan: WorkflowPlan,
        user_input: Optional[str],
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

        return DocumentWorkflowContext(
            document_id=state.document_id,
            document_type=state.document_type,
            thread_id=state.thread_id,
            document_content={},  # TODO: Load current document
            conversation_history=[],  # TODO: Load from thread
            input_documents={},
            user_responses={},
            extra=extra,
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
        # Record execution in history
        state.record_execution(
            node_id=current_node.node_id,
            outcome=result.outcome,
            metadata=result.metadata,
        )

        # Handle user input requirement
        if result.requires_user_input:
            state.set_paused(
                prompt=result.user_prompt,
                choices=result.user_choices,
            )
            return

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

            # Get gate outcome from result metadata if present
            gate_outcome = result.metadata.get("gate_outcome")

            state.current_node_id = next_node_id
            state.set_completed(
                terminal_outcome=terminal_outcome,
                gate_outcome=gate_outcome,
            )

            logger.info(
                f"Execution {state.execution_id} reached terminal: "
                f"{terminal_outcome} (gate: {gate_outcome})"
            )
            return

        # Advance to next node
        state.current_node_id = next_node_id

        # Handle QA failure -> increment retry for generating node
        if (
            current_node.type == NodeType.QA
            and result.outcome == "failed"
        ):
            # Find the generating node (previous task node)
            generating_node_id = self._find_generating_node(state, plan)
            if generating_node_id:
                retry_count = state.increment_retry(generating_node_id)
                logger.info(
                    f"QA failed, incremented retry for {generating_node_id} "
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
            "document_id": state.document_id,
            "document_type": state.document_type,
            "workflow_id": state.workflow_id,
            "status": state.status.value,
            "current_node_id": state.current_node_id,
            "terminal_outcome": state.terminal_outcome,
            "gate_outcome": state.gate_outcome,
            "pending_user_input": state.pending_user_input,
            "pending_prompt": state.pending_prompt,
            "pending_choices": state.pending_choices,
            "escalation_active": state.escalation_active,
            "escalation_options": state.escalation_options,
            "step_count": len(state.node_history),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

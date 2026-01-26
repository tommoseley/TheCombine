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
                logger.info(f"PGC node {current_node.node_id} received user answers - merging clarifications (ADR-042)")

                # ADR-042: Get questions (with DB fallback for restart scenarios)
                questions = await self._get_pgc_questions_for_merge(state)

                # ADR-042: Merge questions with answers and derive binding
                from app.domain.workflow.clarification_merger import merge_clarifications, extract_invariants

                clarifications = merge_clarifications(questions, user_input)
                invariants = extract_invariants(clarifications)

                state.update_context_state({
                    "pgc_answers": user_input,  # backward compat
                    "pgc_clarifications": clarifications,  # ADR-042: Full merged structure
                    "pgc_invariants": invariants,  # ADR-042: Binding constraints only
                })

                logger.info(
                    f"ADR-042: Merged {len(clarifications)} clarifications, "
                    f"{len(invariants)} binding invariants"
                )
                
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

        # Load PGC answers from database for QA nodes (WS-PGC-VALIDATION-001 Phase 2)
        if current_node.type == NodeType.QA and self._db_session:
            await self._load_pgc_answers_for_qa(state, context)

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

    async def _get_pgc_questions_for_merge(
        self,
        state: DocumentWorkflowState,
    ) -> list:
        """Get PGC questions for merging with answers (ADR-042).

        Questions come from state.pending_user_input_payload first,
        with DB fallback for restart scenarios.

        Args:
            state: Current execution state

        Returns:
            List of PGC question objects
        """
        # Try in-memory first (normal case)
        if state.pending_user_input_payload:
            questions = state.pending_user_input_payload.get("questions", [])
            if questions:
                logger.debug(f"ADR-042: Got {len(questions)} questions from pending payload")
                return questions

        # Fallback: load from DB (handles restart scenario)
        if self._db_session:
            try:
                from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository

                repo = PGCAnswerRepository(self._db_session)
                pgc_record = await repo.get_by_execution(state.execution_id)
                if pgc_record and pgc_record.questions:
                    logger.info(
                        f"ADR-042: Loaded {len(pgc_record.questions)} questions from DB fallback"
                    )
                    return pgc_record.questions
            except Exception as e:
                logger.warning(f"ADR-042: Failed to load questions from DB: {e}")

        logger.warning("ADR-042: No questions available for merge")
        return []

    async def _load_pgc_answers_for_qa(
        self,
        state: DocumentWorkflowState,
        context: DocumentWorkflowContext,
    ) -> None:
        """Load PGC answers from database for QA validation.

        Per WS-PGC-VALIDATION-001 Phase 2: When executing a QA node,
        load persisted PGC answers to enable code-based validation.

        Per ADR-042: Also loads merged clarifications if not already in context.

        Args:
            state: Current execution state
            context: Execution context to update
        """
        if not self._db_session:
            return

        # Check if clarifications already in context (normal flow)
        if context.context_state.get("pgc_clarifications"):
            logger.debug("ADR-042: Clarifications already in context, skipping DB load")
            return

        try:
            from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository

            repo = PGCAnswerRepository(self._db_session)
            pgc_answer = await repo.get_by_execution(state.execution_id)

            if pgc_answer:
                # Add to context_state for validation
                context.context_state["pgc_questions"] = pgc_answer.questions
                context.context_state["pgc_answers"] = pgc_answer.answers

                # ADR-042: Also merge clarifications if not present
                if not context.context_state.get("pgc_clarifications"):
                    from app.domain.workflow.clarification_merger import merge_clarifications, extract_invariants

                    clarifications = merge_clarifications(
                        pgc_answer.questions,
                        pgc_answer.answers,
                    )
                    invariants = extract_invariants(clarifications)

                    context.context_state["pgc_clarifications"] = clarifications
                    context.context_state["pgc_invariants"] = invariants

                    logger.info(
                        f"ADR-042: Merged {len(clarifications)} clarifications "
                        f"({len(invariants)} binding) from DB for QA"
                    )

                logger.info(
                    f"Loaded PGC answers for QA validation: "
                    f"{len(pgc_answer.questions)} questions"
                )
            else:
                logger.debug(
                    f"No PGC answers found for execution {state.execution_id}"
                )
        except Exception as e:
            logger.warning(f"Failed to load PGC answers for QA: {e}")

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
            
            # ADR-042: Pin invariants into known_constraints BEFORE storing
            # This runs after generation, before QA, making constraints mechanical
            pinned_document = self._pin_invariants_to_known_constraints(
                result.produced_document, state
            )
            
            # ADR-042: Filter excluded topics from recommendations
            # Prevents boilerplate recs from violating exclusion constraints
            filtered_document = self._filter_excluded_topics(pinned_document, state)
            
            state.update_context_state({
                f"document_{produces_key}": filtered_document,
                "last_produced_document": pinned_document,
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
            
            # Store QA feedback in context_state for remediation node
            # This enables the LLM to learn from the failure
            qa_feedback = self._extract_qa_feedback(result)
            if qa_feedback:
                state.update_context_state({"qa_feedback": qa_feedback})
                logger.info(f"Stored QA feedback for remediation: {len(qa_feedback.get('issues', []))} issues")
        
        # Clear QA feedback on success (to prevent stale feedback on subsequent runs)
        elif current_node.type == NodeType.QA and result.outcome == "success":
            if state.context_state.get("qa_feedback"):
                state.context_state.pop("qa_feedback", None)
                logger.debug("Cleared QA feedback after successful validation")

    def _extract_qa_feedback(self, result: NodeResult) -> Optional[Dict[str, Any]]:
        """Extract actionable QA feedback from failed result.
        
        Builds a structured feedback object that can be included in the
        remediation context to help the LLM understand what went wrong.
        
        Args:
            result: The failed QA NodeResult
            
        Returns:
            Dict with issues, summary, and remediation hints, or None
        """
        if not result.metadata:
            return None
            
        feedback = {
            "issues": [],
            "summary": "",
            "source": result.metadata.get("validation_source", "qa"),
        }
        
        # Extract drift validation errors (ADR-042)
        drift_errors = result.metadata.get("drift_errors", [])
        for err in drift_errors:
            feedback["issues"].append({
                "type": "constraint_drift",
                "check_id": err.get("check_id"),
                "message": err.get("message"),
                "remediation": err.get("remediation"),
            })
        
        # Extract code-based validation errors
        validation_errors = result.metadata.get("validation_errors", [])
        for err in validation_errors:
            feedback["issues"].append({
                "type": "validation",
                "check_id": err.get("check_id"),
                "message": err.get("message"),
            })
        
        # Extract LLM QA errors (list of strings or dicts)
        qa_errors = result.metadata.get("errors", [])
        for err in qa_errors:
            if isinstance(err, dict):
                feedback["issues"].append({
                    "type": "semantic_qa",
                    "severity": err.get("severity", "error"),
                    "section": err.get("section"),
                    "message": err.get("message"),
                })
            elif isinstance(err, str):
                feedback["issues"].append({
                    "type": "semantic_qa",
                    "message": err,
                })
        
        # Extract feedback summary
        qa_feedback = result.metadata.get("feedback", {})
        if isinstance(qa_feedback, dict):
            feedback["summary"] = qa_feedback.get("llm_feedback", "")
        elif isinstance(qa_feedback, str):
            feedback["summary"] = qa_feedback
        
        if not feedback["issues"]:
            return None
            
        return feedback

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

    def _pin_invariants_to_known_constraints(
        self,
        document: Dict[str, Any],
        state: DocumentWorkflowState,
    ) -> Dict[str, Any]:
        """Pin binding invariants into document's known_constraints[].
        
        ADR-042 Fix #2: This runs AFTER generation, BEFORE QA.
        
        Strategy: Build canonical pinned constraints from invariants, then
        REMOVE any LLM-generated constraints that duplicate them. This ensures
        consistent schema and no duplicates.
        
        Args:
            document: The produced document (will be copied, not mutated)
            state: Workflow state containing pgc_invariants
            
        Returns:
            Document with clean known_constraints (pinned + non-duplicate LLM)
        """
        import copy
        
        invariants = state.context_state.get("pgc_invariants", [])
        if not invariants:
            return document
        
        # Work on a copy to avoid mutating the original
        pinned = copy.deepcopy(document)
        
        # Get existing LLM-generated constraints
        llm_constraints = pinned.get("known_constraints", [])
        if not isinstance(llm_constraints, list):
            llm_constraints = []
        
        # Build canonical pinned constraints from invariants
        pinned_constraints = []
        pinned_keywords = set()  # Keywords to check for duplicates
        
        for inv in invariants:
            constraint_id = inv.get("id", "UNKNOWN")
            answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))
            
            if not answer_label:
                continue
            
            # Use normalized_text if available, otherwise clean format
            normalized = inv.get("normalized_text")
            constraint_text = normalized if normalized else answer_label
            
            # Add as structured constraint with clean text
            pinned_constraints.append({
                "text": constraint_text,
                "source": "user_clarification",
                "constraint_id": constraint_id,
                "binding": True,
            })
            
            # Build keywords for duplicate detection
            # Include answer label words, normalized text words, and constraint ID
            for word in answer_label.lower().split():
                if len(word) > 3:  # Skip short words
                    pinned_keywords.add(word)
            if normalized:
                for word in normalized.lower().split():
                    if len(word) > 3:
                        pinned_keywords.add(word)
            # Add constraint ID parts (e.g., PLATFORM -> platform, TARGET -> target)
            for part in constraint_id.split("_"):
                if len(part) > 2:
                    pinned_keywords.add(part.lower())
        
        def _is_duplicate_of_pinned(constraint: Any) -> bool:
            """Check if LLM constraint duplicates a pinned constraint."""
            # Extract text from constraint
            if isinstance(constraint, str):
                text = constraint.lower()
            elif isinstance(constraint, dict):
                # Check multiple fields where the constraint might be
                text = " ".join([
                    str(constraint.get("text", "")),
                    str(constraint.get("constraint", "")),
                    str(constraint.get("description", "")),
                ]).lower()
            else:
                return False
            
            # Count how many pinned keywords appear in this constraint
            matches = sum(1 for kw in pinned_keywords if kw in text)
            
            # If 2+ keyword matches, likely a duplicate
            return matches >= 2
        
        # Filter out LLM constraints that duplicate pinned ones
        filtered_llm = []
        removed_count = 0
        for kc in llm_constraints:
            if _is_duplicate_of_pinned(kc):
                removed_count += 1
                logger.debug(f"ADR-042: Removed duplicate LLM constraint: {kc}")
            else:
                filtered_llm.append(kc)
        
        # Final list: pinned constraints first, then filtered LLM constraints
        final_constraints = pinned_constraints + filtered_llm
        pinned["known_constraints"] = final_constraints
        
        logger.info(
            f"ADR-042: Pinned {len(pinned_constraints)} binding invariants, "
            f"removed {removed_count} duplicates, kept {len(filtered_llm)} LLM constraints "
            f"(total: {len(final_constraints)})"
        )
        
        return pinned

    def _filter_excluded_topics(
        self,
        document: Dict[str, Any],
        state: DocumentWorkflowState,
    ) -> Dict[str, Any]:
        """Filter recommendations and decision points mentioning excluded topics.
        
        ADR-042: Mechanical post-processing to remove boilerplate content
        that violates exclusion constraints. Runs after generation, before QA.
        
        Args:
            document: The produced document (will be copied, not mutated)
            state: Workflow state containing pgc_invariants
            
        Returns:
            Document with excluded topics filtered out
        """
        import copy
        import json
        
        invariants = state.context_state.get("pgc_invariants", [])
        
        # Get exclusion invariants with their canonical tags
        exclusions = []
        for inv in invariants:
            if inv.get("invariant_kind") == "exclusion":
                tags = inv.get("canonical_tags", [])
                if tags:
                    exclusions.append({
                        "id": inv.get("id", "UNKNOWN"),
                        "tags": [t.lower() for t in tags],
                    })
        
        if not exclusions:
            return document
        
        # Work on a copy
        filtered = copy.deepcopy(document)
        removed_count = 0
        
        # Filter recommendations_for_pm
        recommendations = filtered.get("recommendations_for_pm", [])
        if recommendations:
            original_count = len(recommendations)
            filtered_recs = []
            for rec in recommendations:
                rec_text = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)
                rec_lower = rec_text.lower()
                
                # Check if any exclusion tag is mentioned
                should_remove = False
                for excl in exclusions:
                    for tag in excl["tags"]:
                        if tag in rec_lower:
                            logger.debug(f"ADR-042: Removing recommendation mentioning excluded '{tag}'")
                            should_remove = True
                            break
                    if should_remove:
                        break
                
                if not should_remove:
                    filtered_recs.append(rec)
            
            filtered["recommendations_for_pm"] = filtered_recs
            removed_count += original_count - len(filtered_recs)
        
        # Filter early_decision_points that overlap ANY binding invariant
        # Decision points are for unresolved items - bound constraints are resolved
        all_bindings = []
        for inv in invariants:
            tags = inv.get("canonical_tags", [])
            if tags:
                all_bindings.append({
                    "id": inv.get("id", "UNKNOWN"),
                    "tags": [t.lower() for t in tags],
                    "kind": inv.get("invariant_kind", "requirement"),
                })
        
        decision_points = filtered.get("early_decision_points", [])
        if decision_points and all_bindings:
            original_count = len(decision_points)
            filtered_dps = []
            for dp in decision_points:
                dp_text = json.dumps(dp).lower() if isinstance(dp, dict) else str(dp).lower()
                
                should_remove = False
                for binding in all_bindings:
                    for tag in binding["tags"]:
                        if tag in dp_text:
                            logger.debug(
                                f"ADR-042: Removing decision point overlapping bound "
                                f"'{binding['id']}' ({binding['kind']})"
                            )
                            should_remove = True
                            break
                    if should_remove:
                        break
                
                if not should_remove:
                    filtered_dps.append(dp)
            
            filtered["early_decision_points"] = filtered_dps
            removed_count += original_count - len(filtered_dps)
        
        if removed_count > 0:
            logger.info(f"ADR-042: Filtered {removed_count} items mentioning excluded topics")
        
        return filtered

    def _promote_pgc_invariants_to_document(
        self,
        doc_content: Dict[str, Any],
        state: DocumentWorkflowState,
    ) -> None:
        """Promote PGC invariants into document structure.

        Per ADR-042: At document completion, mechanically transform binding
        constraints from context_state into a structured pgc_invariants[]
        section in the output document.

        This makes binding constraints explicit and traceable in the artifact,
        separate from known_constraints (which may include non-PGC items).

        Args:
            doc_content: The document content dict (mutated in place)
            state: The workflow state containing pgc_invariants
        """
        context_invariants = state.context_state.get("pgc_invariants", [])
        if not context_invariants:
            return

        # Get existing known_constraints for cross-referencing
        known_constraints = doc_content.get("known_constraints", [])

        # Build structured invariants
        pgc_invariants = []
        for idx, inv in enumerate(context_invariants, start=1):
            constraint_id = inv.get("id", f"UNKNOWN-{idx}")
            answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))
            binding_source = inv.get("binding_source", "priority")

            # Generate invariant ID
            invariant_id = f"INV-{constraint_id}"

            # Find matching constraint ID in known_constraints (if present)
            source_constraint_id = None
            for i, kc in enumerate(known_constraints):
                kc_text = kc if isinstance(kc, str) else kc.get("text", "")
                if answer_label.lower() in kc_text.lower():
                    source_constraint_id = f"CNS-{i + 1}"
                    break

            # Derive domain from constraint ID (heuristic)
            domain = self._derive_constraint_domain(constraint_id)

            # Build statement from question context
            question_text = inv.get("text", "")
            statement = self._build_invariant_statement(
                constraint_id, question_text, answer_label, binding_source
            )

            pgc_invariants.append({
                "invariant_id": invariant_id,
                "source_constraint_id": source_constraint_id,
                "statement": statement,
                "domain": domain,
                "binding": True,
                "origin": "pgc",
                "change_policy": "explicit_renegotiation_only",
                "pgc_question_id": constraint_id,
                "user_answer": inv.get("user_answer"),
                "user_answer_label": answer_label,
            })

        doc_content["pgc_invariants"] = pgc_invariants
        logger.info(
            f"ADR-042: Promoted {len(pgc_invariants)} PGC invariants to document structure"
        )

    def _derive_constraint_domain(self, constraint_id: str) -> str:
        """Derive semantic domain from constraint ID.

        Args:
            constraint_id: The PGC question ID (e.g., TARGET_PLATFORM)

        Returns:
            Domain string (e.g., "platform", "user", "scope")
        """
        # Map common patterns to domains
        domain_patterns = {
            "PLATFORM": "platform",
            "TARGET": "platform",
            "USER": "user",
            "PRIMARY": "user",
            "DEPLOYMENT": "deployment",
            "CONTEXT": "deployment",
            "SCOPE": "scope",
            "MATH": "scope",
            "FEATURE": "feature",
            "TRACKING": "feature",
            "STANDARD": "compliance",
            "EDUCATIONAL": "compliance",
            "SYSTEM": "integration",
            "EXISTING": "integration",
        }

        constraint_upper = constraint_id.upper()
        for pattern, domain in domain_patterns.items():
            if pattern in constraint_upper:
                return domain

        return "general"

    def _build_invariant_statement(
        self,
        constraint_id: str,
        question_text: str,
        answer_label: str,
        binding_source: str,
    ) -> str:
        """Build human-readable invariant statement.

        Args:
            constraint_id: The PGC question ID
            question_text: The original question text
            answer_label: The user's answer label
            binding_source: How binding was derived (priority, exclusion, etc.)

        Returns:
            Statement string describing the invariant
        """
        # Handle exclusions specially
        if binding_source == "exclusion":
            return f"{answer_label} is explicitly excluded"

        # Build statement based on constraint type
        if "PLATFORM" in constraint_id.upper():
            return f"Application must be deployed as {answer_label}"
        elif "USER" in constraint_id.upper():
            return f"Primary users are {answer_label}"
        elif "DEPLOYMENT" in constraint_id.upper() or "CONTEXT" in constraint_id.upper():
            return f"Deployment context is {answer_label}"
        elif "SCOPE" in constraint_id.upper():
            return f"Scope includes {answer_label}"
        elif "TRACKING" in constraint_id.upper():
            return f"System will provide {answer_label}"
        elif "STANDARD" in constraint_id.upper():
            return f"Educational standards: {answer_label}"
        else:
            # Generic statement
            return f"{constraint_id}: {answer_label}"

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

            # ADR-042: Promote PGC invariants into document structure
            self._promote_pgc_invariants_to_document(doc_content, state)

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

"""Tests for PlanExecutor (ADR-039)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.workflow.plan_executor import (
    PlanExecutor,
    PlanExecutorError,
    InMemoryStatePersistence,
)
from app.domain.workflow.plan_models import (
    Edge,
    EdgeKind,
    Governance,
    Node,
    NodeType,
    OutcomeMapping,
    ThreadOwnership,
    WorkflowPlan,
)
from app.domain.workflow.plan_registry import PlanRegistry
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.domain.workflow.nodes.base import NodeResult


def make_simple_plan() -> WorkflowPlan:
    """Create a simple test workflow plan."""
    return WorkflowPlan(
        workflow_id="test_workflow",
        version="1.0.0",
        name="Test Workflow",
        description="Simple test workflow",
        scope_type="document",
        document_type="test_doc",
        requires_inputs=[],
        entry_node_ids=["start"],
        nodes=[
            Node(
                node_id="start",
                type=NodeType.TASK,
                description="Start task",
                task_ref="task1",
            ),
            Node(
                node_id="end_success",
                type=NodeType.END,
                description="Success end",
                terminal_outcome="stabilized",
            ),
            Node(
                node_id="end_failed",
                type=NodeType.END,
                description="Failed end",
                terminal_outcome="blocked",
            ),
        ],
        edges=[
            Edge(
                edge_id="e1",
                from_node_id="start",
                to_node_id="end_success",
                outcome="success",
                label="Success",
                kind=EdgeKind.AUTO,
            ),
            Edge(
                edge_id="e2",
                from_node_id="start",
                to_node_id="end_failed",
                outcome="failed",
                label="Failed",
                kind=EdgeKind.AUTO,
            ),
        ],
        outcome_mapping=[
            OutcomeMapping(gate_outcome="qualified", terminal_outcome="stabilized"),
        ],
        thread_ownership=ThreadOwnership(owns_thread=False),
        governance=Governance(),
    )


def make_plan_with_gate() -> WorkflowPlan:
    """Create a workflow plan with a gate node."""
    return WorkflowPlan(
        workflow_id="gate_workflow",
        version="1.0.0",
        name="Gate Workflow",
        description="Workflow with gate",
        scope_type="document",
        document_type="gate_doc",
        requires_inputs=[],
        entry_node_ids=["start"],
        nodes=[
            Node(
                node_id="start",
                type=NodeType.TASK,
                description="Start task",
                task_ref="task1",
            ),
            Node(
                node_id="consent_gate",
                type=NodeType.GATE,
                description="Consent gate",
                requires_consent=True,
            ),
            Node(
                node_id="end_success",
                type=NodeType.END,
                description="Success end",
                terminal_outcome="stabilized",
            ),
            Node(
                node_id="end_blocked",
                type=NodeType.END,
                description="Blocked end",
                terminal_outcome="blocked",
            ),
        ],
        edges=[
            Edge(
                edge_id="e1",
                from_node_id="start",
                to_node_id="consent_gate",
                outcome="success",
                label="To gate",
                kind=EdgeKind.AUTO,
            ),
            Edge(
                edge_id="e2",
                from_node_id="consent_gate",
                to_node_id="end_success",
                outcome="success",
                label="Consent given",
                kind=EdgeKind.USER_CHOICE,
            ),
            Edge(
                edge_id="e3",
                from_node_id="consent_gate",
                to_node_id="end_blocked",
                outcome="blocked",
                label="Consent denied",
                kind=EdgeKind.USER_CHOICE,
            ),
        ],
        outcome_mapping=[],
        thread_ownership=ThreadOwnership(owns_thread=False),
        governance=Governance(),
    )


class TestPlanExecutorStartExecution:
    """Tests for starting workflow execution."""

    @pytest.fixture
    def registry(self):
        """Create a registry with test plan."""
        registry = PlanRegistry()
        registry.register(make_simple_plan())
        return registry

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryStatePersistence()

    @pytest.fixture
    def mock_executors(self):
        """Create mock executors for all node types."""
        from app.domain.workflow.plan_models import NodeType

        mock_task = AsyncMock()
        mock_task.execute.return_value = NodeResult.success()

        mock_gate = AsyncMock()
        mock_gate.execute.return_value = NodeResult.success()

        mock_end = AsyncMock()
        mock_end.execute.return_value = NodeResult(outcome="stabilized")

        return {
            NodeType.TASK: mock_task,
            NodeType.GATE: mock_gate,
            NodeType.END: mock_end,
        }

    @pytest.fixture
    def executor(self, persistence, registry, mock_executors):
        """Create executor with mocked services."""
        return PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
            executors=mock_executors,
        )

    @pytest.mark.asyncio
    async def test_start_execution_creates_state(self, executor, persistence):
        """Starting execution creates new state."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        assert state is not None
        assert state.project_id == "proj-123"
        assert state.document_type == "test_doc"
        assert state.workflow_id == "test_workflow"
        assert state.current_node_id == "start"
        assert state.status == DocumentWorkflowStatus.PENDING

    @pytest.mark.asyncio
    async def test_start_execution_persists_state(self, executor, persistence):
        """Starting execution persists the state."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        loaded = await persistence.load(state.execution_id)
        assert loaded is not None
        assert loaded.execution_id == state.execution_id

    @pytest.mark.asyncio
    async def test_start_execution_resumes_existing(self, executor, persistence):
        """Starting execution resumes existing non-terminal execution."""
        # Start first execution
        state1 = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        # Try to start again - should return existing
        state2 = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        assert state2.execution_id == state1.execution_id

    @pytest.mark.asyncio
    async def test_start_execution_unknown_document_type(self, executor):
        """Starting execution with unknown document type raises error."""
        with pytest.raises(PlanExecutorError) as exc_info:
            await executor.start_execution(
                project_id="proj-123",
                document_type="unknown_type",
            )

        assert "No workflow plan found" in str(exc_info.value)


class TestPlanExecutorExecuteStep:
    """Tests for executing workflow steps."""

    @pytest.fixture
    def registry(self):
        """Create a registry with test plan."""
        registry = PlanRegistry()
        registry.register(make_simple_plan())
        return registry

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryStatePersistence()

    @pytest.fixture
    def mock_executors(self):
        """Create mock executors for all node types."""
        from app.domain.workflow.plan_models import NodeType

        mock_task = AsyncMock()
        mock_task.execute.return_value = NodeResult.success()

        mock_end = AsyncMock()
        mock_end.execute.return_value = NodeResult(outcome="stabilized")

        return {
            NodeType.TASK: mock_task,
            NodeType.END: mock_end,
        }

    @pytest.fixture
    def executor(self, persistence, registry, mock_executors):
        """Create executor with mocked task executor."""
        return PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
            executors=mock_executors,
        )

    @pytest.mark.asyncio
    async def test_execute_step_advances_to_terminal(self, executor, persistence, mock_executors):
        """Execute step advances through workflow to terminal."""
        # Start execution
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        # Configure mock to return success with document
        from app.domain.workflow.plan_models import NodeType
        mock_executors[NodeType.TASK].execute.return_value = NodeResult.success(
            produced_document={"content": "test"}
        )

        # Execute step
        state = await executor.execute_step(state.execution_id)

        # Should have advanced to terminal
        assert state.status == DocumentWorkflowStatus.COMPLETED
        assert state.terminal_outcome == "stabilized"

    @pytest.mark.asyncio
    async def test_execute_step_records_history(self, executor, persistence, mock_executors):
        """Execute step records execution in history."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        state = await executor.execute_step(state.execution_id)

        assert len(state.node_history) == 1
        assert state.node_history[0].node_id == "start"
        assert state.node_history[0].outcome == "success"

    @pytest.mark.asyncio
    async def test_execute_step_handles_failure(self, executor, persistence, mock_executors):
        """Execute step handles failed outcome correctly."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        # Configure mock to return failure
        from app.domain.workflow.plan_models import NodeType
        mock_executors[NodeType.TASK].execute.return_value = NodeResult.failed(
            reason="Task failed"
        )

        state = await executor.execute_step(state.execution_id)

        assert state.status == DocumentWorkflowStatus.COMPLETED
        assert state.terminal_outcome == "blocked"

    @pytest.mark.asyncio
    async def test_execute_step_not_found(self, executor):
        """Execute step with unknown execution raises error."""
        with pytest.raises(PlanExecutorError) as exc_info:
            await executor.execute_step("nonexistent")

        assert "Execution not found" in str(exc_info.value)


class TestPlanExecutorPauseResume:
    """Tests for pause/resume functionality."""

    @pytest.fixture
    def registry(self):
        """Create registry with gate workflow."""
        registry = PlanRegistry()
        registry.register(make_plan_with_gate())
        return registry

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryStatePersistence()

    @pytest.fixture
    def mock_executors(self):
        """Create mock executors for gate workflow."""
        from app.domain.workflow.plan_models import NodeType

        mock_task = AsyncMock()
        mock_task.execute.return_value = NodeResult.success()

        mock_gate = AsyncMock()
        mock_gate.execute.return_value = NodeResult(
            outcome="needs_user_input",
            requires_user_input=True,
            user_prompt="Do you consent?",
            user_choices=["Yes", "No"],
        )

        mock_end = AsyncMock()
        mock_end.execute.return_value = NodeResult(outcome="stabilized")

        return {
            NodeType.TASK: mock_task,
            NodeType.GATE: mock_gate,
            NodeType.END: mock_end,
        }

    @pytest.fixture
    def executor(self, persistence, registry, mock_executors):
        """Create executor."""
        return PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
            executors=mock_executors,
        )

    @pytest.mark.asyncio
    async def test_pauses_at_gate(self, executor, persistence, mock_executors):
        """Execution pauses when gate requires user input."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="gate_doc",
        )

        # Execute first step (task)
        state = await executor.execute_step(state.execution_id)
        assert state.current_node_id == "consent_gate"

        # Execute gate step - should pause
        state = await executor.execute_step(state.execution_id)

        assert state.status == DocumentWorkflowStatus.PAUSED
        assert state.pending_user_input is True
        assert state.pending_user_input_rendered == "Do you consent?"
        assert state.pending_choices == ["Yes", "No"]

    @pytest.mark.asyncio
    async def test_resume_with_user_input(self, executor, persistence, mock_executors):
        """Execution resumes after user input."""
        from app.domain.workflow.plan_models import NodeType

        state = await executor.start_execution(
            project_id="proj-123",
            document_type="gate_doc",
        )

        # Gate requires input first, then accepts
        mock_executors[NodeType.GATE].execute.side_effect = [
            NodeResult(
                outcome="needs_user_input",
                requires_user_input=True,
                user_prompt="Consent?",
                user_choices=["Yes", "No"],
            ),
            NodeResult.success(),  # After user input
        ]

        # Execute through to pause
        state = await executor.execute_step(state.execution_id)  # task
        state = await executor.execute_step(state.execution_id)  # gate pauses

        assert state.status == DocumentWorkflowStatus.PAUSED

        # Submit user input
        state = await executor.submit_user_input(
            state.execution_id,
            user_choice="Yes",
        )

        # Should complete
        assert state.status == DocumentWorkflowStatus.COMPLETED
        assert state.terminal_outcome == "stabilized"

    @pytest.mark.asyncio
    async def test_submit_input_not_paused_raises(self, executor, persistence):
        """Submitting input to non-paused execution raises error."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="gate_doc",
        )

        with pytest.raises(PlanExecutorError) as exc_info:
            await executor.submit_user_input(
                state.execution_id,
                user_input="test",
            )

        assert "is not paused" in str(exc_info.value)


class TestPlanExecutorRunToCompletion:
    """Tests for run_to_completion_or_pause."""

    @pytest.fixture
    def registry(self):
        """Create registry with test plan."""
        registry = PlanRegistry()
        registry.register(make_simple_plan())
        registry.register(make_plan_with_gate())
        return registry

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryStatePersistence()

    @pytest.fixture
    def mock_executors(self):
        """Create mock executors."""
        from app.domain.workflow.plan_models import NodeType

        mock_task = AsyncMock()
        mock_task.execute.return_value = NodeResult.success()

        mock_gate = AsyncMock()
        mock_gate.execute.return_value = NodeResult(
            outcome="needs_user_input",
            requires_user_input=True,
            user_prompt="Consent?",
        )

        mock_end = AsyncMock()
        mock_end.execute.return_value = NodeResult(outcome="stabilized")

        return {
            NodeType.TASK: mock_task,
            NodeType.GATE: mock_gate,
            NodeType.END: mock_end,
        }

    @pytest.fixture
    def executor(self, persistence, registry, mock_executors):
        """Create executor."""
        return PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
            executors=mock_executors,
        )

    @pytest.mark.asyncio
    async def test_runs_to_completion(self, executor, persistence):
        """Run to completion executes all steps."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        state = await executor.run_to_completion_or_pause(state.execution_id)

        assert state.status == DocumentWorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_stops_at_pause(self, executor, persistence):
        """Run stops when execution pauses."""
        state = await executor.start_execution(
            project_id="proj-456",
            document_type="gate_doc",
        )

        state = await executor.run_to_completion_or_pause(state.execution_id)

        assert state.status == DocumentWorkflowStatus.PAUSED


class TestPlanExecutorEscalation:
    """Tests for escalation handling."""

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryStatePersistence()

    @pytest.mark.asyncio
    async def test_handle_escalation_abandon(self, persistence):
        """Handle abandon escalation choice."""
        # Create plan with circuit breaker
        plan = WorkflowPlan(
            workflow_id="escalation_workflow",
            version="1.0.0",
            name="Escalation Workflow",
            description="Workflow with escalation",
            scope_type="document",
            document_type="escalation_doc",
            requires_inputs=[],
            entry_node_ids=["start"],
            nodes=[
                Node(
                    node_id="start",
                    type=NodeType.TASK,
                    description="Start",
                    task_ref="t1",
                ),
            ],
            edges=[],
            outcome_mapping=[],
            thread_ownership=ThreadOwnership(owns_thread=False),
            governance=Governance(),
        )

        registry = PlanRegistry()
        registry.register(plan)

        executor = PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
        )

        state = await executor.start_execution(
            project_id="proj-123",
            document_type="escalation_doc",
        )

        # Manually set escalation state
        state.set_escalation(["retry", "narrow_scope", "abandon"])
        await persistence.save(state)

        # Handle abandon choice
        state = await executor.handle_escalation_choice(
            state.execution_id,
            choice="abandon",
        )

        assert state.escalation_active is False
        assert state.status == DocumentWorkflowStatus.COMPLETED
        assert state.terminal_outcome == "abandoned"

    @pytest.mark.asyncio
    async def test_handle_escalation_retry(self, persistence):
        """Handle retry escalation choice."""
        plan = WorkflowPlan(
            workflow_id="escalation_workflow",
            version="1.0.0",
            name="Escalation Workflow",
            description="Workflow with escalation",
            scope_type="document",
            document_type="escalation_doc",
            requires_inputs=[],
            entry_node_ids=["start"],
            nodes=[
                Node(
                    node_id="start",
                    type=NodeType.TASK,
                    description="Start",
                    task_ref="t1",
                ),
            ],
            edges=[],
            outcome_mapping=[],
            thread_ownership=ThreadOwnership(owns_thread=False),
            governance=Governance(),
        )

        registry = PlanRegistry()
        registry.register(plan)

        executor = PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
        )

        state = await executor.start_execution(
            project_id="proj-123",
            document_type="escalation_doc",
        )

        # Set escalation with prior retries
        state.increment_retry("start")
        state.increment_retry("start")
        state.set_escalation(["retry", "abandon"])
        await persistence.save(state)

        # Handle retry choice
        state = await executor.handle_escalation_choice(
            state.execution_id,
            choice="retry",
        )

        assert state.escalation_active is False
        assert state.status == DocumentWorkflowStatus.RUNNING
        assert state.get_retry_count("start") == 0  # Reset

    @pytest.mark.asyncio
    async def test_handle_escalation_invalid_choice(self, persistence):
        """Handle invalid escalation choice raises error."""
        plan = WorkflowPlan(
            workflow_id="escalation_workflow",
            version="1.0.0",
            name="Escalation Workflow",
            description="Workflow with escalation",
            scope_type="document",
            document_type="escalation_doc",
            requires_inputs=[],
            entry_node_ids=["start"],
            nodes=[
                Node(
                    node_id="start",
                    type=NodeType.TASK,
                    description="Start",
                    task_ref="t1",
                ),
            ],
            edges=[],
            outcome_mapping=[],
            thread_ownership=ThreadOwnership(owns_thread=False),
            governance=Governance(),
        )

        registry = PlanRegistry()
        registry.register(plan)

        executor = PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
        )

        state = await executor.start_execution(
            project_id="proj-123",
            document_type="escalation_doc",
        )

        state.set_escalation(["retry", "abandon"])
        await persistence.save(state)

        with pytest.raises(PlanExecutorError) as exc_info:
            await executor.handle_escalation_choice(
                state.execution_id,
                choice="invalid",
            )

        assert "Invalid escalation choice" in str(exc_info.value)


class TestPlanExecutorStatus:
    """Tests for execution status retrieval."""

    @pytest.fixture
    def registry(self):
        """Create registry with test plan."""
        registry = PlanRegistry()
        registry.register(make_simple_plan())
        return registry

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryStatePersistence()

    @pytest.fixture
    def mock_executors(self):
        """Create mock executors."""
        from app.domain.workflow.plan_models import NodeType

        mock_task = AsyncMock()
        mock_task.execute.return_value = NodeResult.success()

        return {
            NodeType.TASK: mock_task,
        }

    @pytest.fixture
    def executor(self, persistence, registry, mock_executors):
        """Create executor."""
        return PlanExecutor(
            persistence=persistence,
            plan_registry=registry,
            executors=mock_executors,
        )

    @pytest.mark.asyncio
    async def test_get_execution_status(self, executor, persistence):
        """Get execution status returns correct data."""
        state = await executor.start_execution(
            project_id="proj-123",
            document_type="test_doc",
        )

        status = await executor.get_execution_status(state.execution_id)

        assert status is not None
        assert status["execution_id"] == state.execution_id
        assert status["project_id"] == "proj-123"
        assert status["status"] == "pending"
        assert status["current_node_id"] == "start"

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, executor):
        """Get status for unknown execution returns None."""
        status = await executor.get_execution_status("nonexistent")

        assert status is None


class TestInMemoryStatePersistence:
    """Tests for in-memory persistence."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Save and load state."""
        persistence = InMemoryStatePersistence()

        from app.domain.workflow.document_workflow_state import (
            DocumentWorkflowState,
            DocumentWorkflowStatus,
        )

        state = DocumentWorkflowState(
            execution_id="exec-123",
            workflow_id="wf-1",
            project_id="proj-456",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )

        await persistence.save(state)
        loaded = await persistence.load("exec-123")

        assert loaded is not None
        assert loaded.execution_id == "exec-123"

    @pytest.mark.asyncio
    async def test_load_by_document(self):
        """Load state by document and workflow."""
        persistence = InMemoryStatePersistence()

        from app.domain.workflow.document_workflow_state import (
            DocumentWorkflowState,
            DocumentWorkflowStatus,
        )

        state = DocumentWorkflowState(
            execution_id="exec-123",
            workflow_id="wf-1",
            project_id="proj-456",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )

        await persistence.save(state)
        loaded = await persistence.load_by_document("proj-456", "wf-1")

        assert loaded is not None
        assert loaded.project_id == "proj-456"

    @pytest.mark.asyncio
    async def test_load_not_found(self):
        """Load returns None for unknown execution."""
        persistence = InMemoryStatePersistence()

        loaded = await persistence.load("nonexistent")
        assert loaded is None


class TestPinInvariantsToKnownConstraints:
    """Tests for _pin_invariants_to_known_constraints transformation.

    Per WS-ADR-047-004 Phase 1: Test coverage for refactoring target.
    """

    @pytest.fixture
    def executor(self):
        """Create executor for testing transformation methods."""
        persistence = InMemoryStatePersistence()
        return PlanExecutor(persistence=persistence)

    @pytest.fixture
    def mock_state(self):
        """Create mock state with context_state."""
        from app.domain.workflow.document_workflow_state import (
            DocumentWorkflowState,
            DocumentWorkflowStatus,
        )
        return DocumentWorkflowState(
            execution_id="exec-123",
            workflow_id="wf-1",
            project_id="proj-456",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )

    def test_no_invariants_returns_original(self, executor, mock_state):
        """No invariants returns document unchanged."""
        document = {"known_constraints": ["existing constraint"]}
        mock_state.context_state = {}  # No pgc_invariants

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        assert result == document
        assert result["known_constraints"] == ["existing constraint"]

    def test_pins_invariants_to_known_constraints(self, executor, mock_state):
        """Invariants are pinned to known_constraints with proper structure."""
        document = {"known_constraints": []}
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "TARGET_PLATFORM",
                    "user_answer_label": "Web browser",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        assert len(result["known_constraints"]) == 1
        pinned = result["known_constraints"][0]
        assert pinned["text"] == "Web browser"
        assert pinned["source"] == "user_clarification"
        assert pinned["constraint_id"] == "TARGET_PLATFORM"
        assert pinned["binding"] is True

    def test_uses_normalized_text_when_available(self, executor, mock_state):
        """Uses normalized_text instead of answer_label when available."""
        document = {"known_constraints": []}
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "EXISTING_SYSTEMS",
                    "user_answer_label": "No",
                    "normalized_text": "No integrations with existing systems are in scope.",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        pinned = result["known_constraints"][0]
        assert pinned["text"] == "No integrations with existing systems are in scope."

    def test_removes_duplicate_llm_constraints(self, executor, mock_state):
        """LLM constraints duplicating pinned ones are removed."""
        document = {
            "known_constraints": [
                {"text": "Application must target web browser platform"},
                {"text": "Unrelated constraint about security"},
            ]
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "TARGET_PLATFORM",
                    "user_answer_label": "Web browser",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        # Should have pinned + one non-duplicate (2 total)
        assert len(result["known_constraints"]) == 2
        # First should be the pinned constraint
        assert result["known_constraints"][0]["source"] == "user_clarification"
        # Second should be the non-duplicate
        assert "security" in result["known_constraints"][1]["text"].lower()

    def test_keeps_non_duplicate_llm_constraints(self, executor, mock_state):
        """LLM constraints not duplicating pinned ones are kept."""
        document = {
            "known_constraints": [
                {"text": "Must support 1000 concurrent users"},
                {"text": "Database must be PostgreSQL"},
            ]
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "TARGET_PLATFORM",
                    "user_answer_label": "Mobile app",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        # Should have pinned + both LLM constraints (3 total)
        assert len(result["known_constraints"]) == 3

    def test_does_not_mutate_original_document(self, executor, mock_state):
        """Original document is not mutated."""
        original_constraints = [{"text": "Original constraint"}]
        document = {"known_constraints": original_constraints.copy()}
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "TEST",
                    "user_answer_label": "Test value",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        # Original document unchanged
        assert document["known_constraints"] == original_constraints
        # Result is different
        assert len(result["known_constraints"]) == 2

    def test_handles_string_constraints(self, executor, mock_state):
        """Handles LLM constraints as plain strings."""
        document = {
            "known_constraints": [
                "Web browser is the target platform",
                "Must support offline mode",
            ]
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "TARGET_PLATFORM",
                    "user_answer_label": "Web browser",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        # Should remove the duplicate string constraint
        assert len(result["known_constraints"]) == 2

    def test_skips_invariants_with_empty_answer_label(self, executor, mock_state):
        """Invariants with empty answer_label are skipped."""
        document = {"known_constraints": []}
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "EMPTY",
                    "user_answer_label": "",
                    "user_answer": "",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        # Empty answer_label and empty user_answer -> skipped
        assert len(result["known_constraints"]) == 0

    def test_uses_user_answer_as_fallback(self, executor, mock_state):
        """Uses str(user_answer) when user_answer_label is missing."""
        document = {"known_constraints": []}
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "WITH_ANSWER",
                    "user_answer": "some value",
                    "binding": True,
                },
            ]
        }

        result = executor._pin_invariants_to_known_constraints(document, mock_state)

        assert len(result["known_constraints"]) == 1
        assert result["known_constraints"][0]["text"] == "some value"


class TestFilterExcludedTopics:
    """Tests for _filter_excluded_topics transformation.

    Per WS-ADR-047-004 Phase 1: Test coverage for refactoring target.
    """

    @pytest.fixture
    def executor(self):
        """Create executor for testing transformation methods."""
        persistence = InMemoryStatePersistence()
        return PlanExecutor(persistence=persistence)

    @pytest.fixture
    def mock_state(self):
        """Create mock state with context_state."""
        from app.domain.workflow.document_workflow_state import (
            DocumentWorkflowState,
            DocumentWorkflowStatus,
        )
        return DocumentWorkflowState(
            execution_id="exec-123",
            workflow_id="wf-1",
            project_id="proj-456",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )

    def test_no_exclusions_returns_original(self, executor, mock_state):
        """No exclusion invariants returns document unchanged."""
        document = {
            "recommendations_for_pm": [{"recommendation": "Consider integrations"}],
            "early_decision_points": [{"area": "Platform choice"}],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "PLATFORM",
                    "invariant_kind": "requirement",  # Not exclusion
                    "canonical_tags": ["web"],
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        assert len(result["recommendations_for_pm"]) == 1
        assert len(result["early_decision_points"]) == 1

    def test_filters_recommendations_mentioning_excluded_tags(self, executor, mock_state):
        """Recommendations mentioning excluded tags are removed."""
        document = {
            "recommendations_for_pm": [
                {"recommendation": "Consider offline support for mobile users"},
                {"recommendation": "Add user authentication"},
            ],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE_MODE",
                    "invariant_kind": "exclusion",
                    "canonical_tags": ["offline"],
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        assert len(result["recommendations_for_pm"]) == 1
        assert "authentication" in result["recommendations_for_pm"][0]["recommendation"]

    def test_keeps_recommendations_not_mentioning_tags(self, executor, mock_state):
        """Recommendations not mentioning excluded tags are kept."""
        document = {
            "recommendations_for_pm": [
                {"recommendation": "Use React for frontend"},
                {"recommendation": "Implement caching layer"},
            ],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE_MODE",
                    "invariant_kind": "exclusion",
                    "canonical_tags": ["offline", "sync"],
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        assert len(result["recommendations_for_pm"]) == 2

    def test_filters_decision_points_overlapping_bindings(self, executor, mock_state):
        """Decision points overlapping any binding invariant are removed.

        Note: Decision point filtering only runs when exclusions are present.
        """
        document = {
            "recommendations_for_pm": [],  # Need for exclusion to trigger
            "early_decision_points": [
                {"decision_area": "Platform selection", "options": ["web", "mobile"]},
                {"decision_area": "Database choice", "options": ["postgres", "mysql"]},
            ],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE_MODE",
                    "invariant_kind": "exclusion",  # Need an exclusion to trigger filtering
                    "canonical_tags": ["offline"],
                },
                {
                    "id": "TARGET_PLATFORM",
                    "invariant_kind": "requirement",
                    "canonical_tags": ["platform", "web"],
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        # Platform decision should be removed (overlaps binding with "platform" or "web" tag)
        assert len(result["early_decision_points"]) == 1
        assert "database" in result["early_decision_points"][0]["decision_area"].lower()

    def test_does_not_mutate_original_document(self, executor, mock_state):
        """Original document is not mutated."""
        original_recs = [{"recommendation": "Add offline support"}]
        document = {
            "recommendations_for_pm": original_recs.copy(),
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE",
                    "invariant_kind": "exclusion",
                    "canonical_tags": ["offline"],
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        # Original unchanged
        assert document["recommendations_for_pm"] == original_recs
        # Result filtered
        assert len(result["recommendations_for_pm"]) == 0

    def test_handles_string_recommendations(self, executor, mock_state):
        """Handles recommendations as plain strings."""
        document = {
            "recommendations_for_pm": [
                "Consider offline functionality",
                "Use secure authentication",
            ],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE",
                    "invariant_kind": "exclusion",
                    "canonical_tags": ["offline"],
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        assert len(result["recommendations_for_pm"]) == 1
        assert "authentication" in result["recommendations_for_pm"][0]

    def test_exclusion_without_tags_is_ignored(self, executor, mock_state):
        """Exclusion invariants without canonical_tags are ignored."""
        document = {
            "recommendations_for_pm": [
                {"recommendation": "Consider offline support"},
            ],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE",
                    "invariant_kind": "exclusion",
                    "canonical_tags": [],  # Empty tags
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        # Nothing filtered because no tags to match
        assert len(result["recommendations_for_pm"]) == 1

    def test_case_insensitive_tag_matching(self, executor, mock_state):
        """Tag matching is case insensitive."""
        document = {
            "recommendations_for_pm": [
                {"recommendation": "Implement OFFLINE mode for better UX"},
            ],
        }
        mock_state.context_state = {
            "pgc_invariants": [
                {
                    "id": "OFFLINE",
                    "invariant_kind": "exclusion",
                    "canonical_tags": ["offline"],  # lowercase
                },
            ]
        }

        result = executor._filter_excluded_topics(document, mock_state)

        # Should still filter (case insensitive)
        assert len(result["recommendations_for_pm"]) == 0

"""CRAP score remediation tests for PlanExecutor methods.

Targets:
1. _emit_stations_declared (CC=11, 30% cov -> need ~55%)
2. execute_step (CC=18, 60.5% cov -> need ~73%)

Tests focus on UNCOVERED branches to push coverage above CRAP-30 threshold.
"""

import importlib
import importlib.util
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ---------------------------------------------------------------------------
# Stubs (avoid circular imports by not importing real classes)
# ---------------------------------------------------------------------------

class FakeStationMetadata:
    def __init__(self, station_id, label, order):
        self.id = station_id
        self.label = label
        self.order = order


class FakeNode:
    """Minimal Node stub matching plan_models.Node interface."""

    def __init__(
        self,
        node_id="task-1",
        node_type="task",
        description="test node",
        station=None,
        internals=None,
        gate_kind=None,
        produces=None,
        task_ref=None,
    ):
        self.node_id = node_id
        self.type = node_type
        self.description = description
        self.station = station
        self.internals = internals or {}
        self.gate_kind = gate_kind
        self.produces = produces
        self.task_ref = task_ref

    def is_qa_gate(self):
        return self.type == "qa" or (self.type == "gate" and self.gate_kind == "qa")


class FakeState:
    """Minimal DocumentWorkflowState stub."""

    def __init__(
        self,
        execution_id="exec-1",
        workflow_id="test_wf",
        current_node_id="task-1",
        status="running",
        project_id=None,
        document_type="test_doc",
        context_state=None,
        pending_user_input=False,
    ):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.current_node_id = current_node_id
        self.status = status
        self.project_id = project_id or str(uuid4())
        self.document_type = document_type
        self.context_state = context_state or {}
        self.pending_user_input = pending_user_input
        self.pending_choices = None
        self.pending_user_input_rendered = None
        self._recorded = []
        self._failed = False

    def record_execution(self, node_id, outcome, metadata=None):
        self._recorded.append({"node_id": node_id, "outcome": outcome, "metadata": metadata})

    def set_failed(self, reason):
        self._failed = True
        self.status = "failed"
        self._fail_reason = reason
        self.record_execution(self.current_node_id, "failed", {"failure_reason": reason})

    def clear_pause(self):
        self.pending_user_input = False
        self.pending_user_input_rendered = None
        self.pending_choices = None
        self.status = "running"

    def update_context_state(self, delta):
        self.context_state.update(delta)


class FakeNodeResult:
    """Minimal NodeResult stub."""

    def __init__(
        self,
        outcome="success",
        metadata=None,
        requires_user_input=False,
        user_prompt=None,
        produced_document=None,
    ):
        self.outcome = outcome
        self.metadata = metadata or {}
        self.requires_user_input = requires_user_input
        self.user_prompt = user_prompt
        self.produced_document = produced_document


class FakePlan:
    """Minimal WorkflowPlan stub."""

    def __init__(self, workflow_id="test_wf", nodes=None, stations=None):
        self.workflow_id = workflow_id
        self._nodes = {n.node_id: n for n in (nodes or [])}
        self._stations = stations
        self.nodes = nodes or []

    def get_node(self, node_id):
        return self._nodes.get(node_id)

    def get_stations(self):
        return self._stations or []


class FakePersistence:
    """Minimal state persistence stub."""

    def __init__(self):
        self._states = {}

    async def save(self, state):
        self._states[state.execution_id] = state

    async def load(self, execution_id):
        return self._states.get(execution_id)


# ---------------------------------------------------------------------------
# Fixture: PlanExecutor loaded via importlib to avoid circular imports
# ---------------------------------------------------------------------------

_mock_publish_event = AsyncMock()


@pytest.fixture
def pe_module():
    """Load plan_executor module avoiding circular imports."""
    global _mock_publish_event
    _mock_publish_event = AsyncMock()

    mock_production = MagicMock()
    mock_production.publish_event = _mock_publish_event
    sys.modules["app.api.v1.routers.production"] = mock_production

    spec = importlib.util.spec_from_file_location(
        "plan_executor_crap_test",
        "app/domain/workflow/plan_executor.py",
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Also patch publish_event on the loaded module to our controllable mock
    mod.publish_event = _mock_publish_event

    return mod


@pytest.fixture
def executor(pe_module):
    """Create PlanExecutor with minimal stubs."""
    PlanExecutor = pe_module.PlanExecutor
    pe = PlanExecutor.__new__(PlanExecutor)
    pe._persistence = FakePersistence()
    pe._db_session = None
    pe._ops_service = MagicMock()
    pe._outcome_recorder = None
    pe._thread_manager = None
    pe._executors = {}
    pe._plan_registry = MagicMock()
    return pe


# ====================================================================
# _emit_stations_declared tests
# ====================================================================


class TestEmitStationsDeclared:
    """Tests for PlanExecutor._emit_stations_declared uncovered branches."""

    @pytest.mark.asyncio
    async def test_no_stations_defined(self, executor):
        """Branch: plan.get_stations() returns empty -> early return."""
        plan = FakePlan(stations=[])
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        _mock_publish_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_stations_present_emits_event(self, executor):
        """Branch: stations present -> emits stations_declared."""
        s1 = FakeStationMetadata("draft", "DRAFT", 1)
        s2 = FakeStationMetadata("qa", "QA", 2)
        nodes = [
            FakeNode(node_id="task-1", station=s1),
            FakeNode(node_id="qa-1", station=s2),
        ]
        plan = FakePlan(
            nodes=nodes,
            stations=[
                {"id": "draft", "label": "DRAFT", "order": 1},
                {"id": "qa", "label": "QA", "order": 2},
            ],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        _mock_publish_event.assert_called_once()
        call_args = _mock_publish_event.call_args
        assert call_args[0][1] == "stations_declared"
        payload = call_args[0][2]
        assert "stations" in payload
        assert len(payload["stations"]) == 2

    @pytest.mark.asyncio
    async def test_stations_with_phases_from_internals(self, executor):
        """Branch: nodes have internals -> phases_by_station populated."""
        s1 = FakeStationMetadata("draft", "DRAFT", 1)
        nodes = [
            FakeNode(
                node_id="task-1",
                station=s1,
                internals={"pass_a": {"type": "llm"}, "entry": {"type": "ui"}},
            ),
        ]
        plan = FakePlan(
            nodes=nodes,
            stations=[{"id": "draft", "label": "DRAFT", "order": 1}],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        _mock_publish_event.assert_called_once()
        payload = _mock_publish_event.call_args[0][2]
        stations = payload["stations"]
        draft_station = next(s for s in stations if s["id"] == "draft")
        assert "phases" in draft_station
        assert "pass_a" in draft_station["phases"]
        assert "entry" in draft_station["phases"]

    @pytest.mark.asyncio
    async def test_publish_event_exception_swallowed(self, executor):
        """Branch: publish_event raises -> exception caught, not propagated."""
        plan = FakePlan(
            nodes=[FakeNode(station=FakeStationMetadata("draft", "DRAFT", 1))],
            stations=[{"id": "draft", "label": "DRAFT", "order": 1}],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        _mock_publish_event.side_effect = RuntimeError("SSE down")
        # Should not raise
        await executor._emit_stations_declared(plan, state)
        _mock_publish_event.side_effect = None  # Reset for other tests

    @pytest.mark.asyncio
    async def test_station_data_all_pending(self, executor):
        """Branch: all stations start as 'pending'."""
        plan = FakePlan(
            nodes=[
                FakeNode(station=FakeStationMetadata("draft", "DRAFT", 1)),
                FakeNode(node_id="qa-1", station=FakeStationMetadata("qa", "QA", 2)),
            ],
            stations=[
                {"id": "draft", "label": "DRAFT", "order": 1},
                {"id": "qa", "label": "QA", "order": 2},
            ],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        payload = _mock_publish_event.call_args[0][2]
        for station in payload["stations"]:
            assert station["state"] == "pending"

    @pytest.mark.asyncio
    async def test_stations_deduplicated(self, executor):
        """Branch: multiple nodes map to same station -> deduped."""
        station = FakeStationMetadata("draft", "DRAFT", 1)
        nodes = [
            FakeNode(node_id="task-1", station=station),
            FakeNode(node_id="task-2", station=station),
        ]
        plan = FakePlan(
            nodes=nodes,
            stations=[{"id": "draft", "label": "DRAFT", "order": 1}],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        payload = _mock_publish_event.call_args[0][2]
        assert len(payload["stations"]) == 1
        assert payload["stations"][0]["id"] == "draft"

    @pytest.mark.asyncio
    async def test_node_without_internals_empty_phases(self, executor):
        """Branch: node.station set but no internals -> empty phases list."""
        plan = FakePlan(
            nodes=[FakeNode(station=FakeStationMetadata("draft", "DRAFT", 1), internals={})],
            stations=[{"id": "draft", "label": "DRAFT", "order": 1}],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        payload = _mock_publish_event.call_args[0][2]
        assert payload["stations"][0]["phases"] == []

    @pytest.mark.asyncio
    async def test_duplicate_phase_keys_deduplicated(self, executor):
        """Branch: same phase key appears in multiple internals dicts -> deduped."""
        station = FakeStationMetadata("draft", "DRAFT", 1)
        nodes = [
            FakeNode(
                node_id="task-1",
                station=station,
                internals={"pass_a": {"type": "llm"}, "merge": {"type": "mech"}},
            ),
            FakeNode(
                node_id="task-2",
                station=station,
                internals={"pass_a": {"type": "llm"}, "entry": {"type": "ui"}},
            ),
        ]
        plan = FakePlan(
            nodes=nodes,
            stations=[{"id": "draft", "label": "DRAFT", "order": 1}],
        )
        state = FakeState()

        _mock_publish_event.reset_mock()
        await executor._emit_stations_declared(plan, state)
        payload = _mock_publish_event.call_args[0][2]
        phases = payload["stations"][0]["phases"]
        assert phases.count("pass_a") == 1
        assert "merge" in phases
        assert "entry" in phases


# ====================================================================
# execute_step tests
# ====================================================================


class TestExecuteStep:
    """Tests for PlanExecutor.execute_step uncovered branches."""

    @pytest.mark.asyncio
    async def test_execution_not_found(self, executor, pe_module):
        """Branch: persistence.load returns None -> PlanExecutorError."""
        with pytest.raises(pe_module.PlanExecutorError, match="Execution not found"):
            await executor.execute_step("nonexistent-exec")

    @pytest.mark.asyncio
    async def test_already_completed(self, executor, pe_module):
        """Branch: state.status == COMPLETED -> return state early."""
        state = FakeState(status=pe_module.DocumentWorkflowStatus.COMPLETED)
        await executor._persistence.save(state)

        result = await executor.execute_step(state.execution_id)
        assert result.status == pe_module.DocumentWorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_already_failed(self, executor, pe_module):
        """Branch: state.status == FAILED -> return state early."""
        state = FakeState(status=pe_module.DocumentWorkflowStatus.FAILED)
        await executor._persistence.save(state)

        result = await executor.execute_step(state.execution_id)
        assert result.status == pe_module.DocumentWorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_plan_not_found(self, executor, pe_module):
        """Branch: plan_registry.get returns None -> PlanExecutorError."""
        state = FakeState(status=pe_module.DocumentWorkflowStatus.RUNNING)
        await executor._persistence.save(state)
        executor._plan_registry.get.return_value = None

        with pytest.raises(pe_module.PlanExecutorError, match="Plan not found"):
            await executor.execute_step(state.execution_id)

    @pytest.mark.asyncio
    async def test_node_not_found_in_plan(self, executor, pe_module):
        """Branch: plan.get_node returns None -> PlanExecutorError."""
        state = FakeState(
            current_node_id="nonexistent-node",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[])
        executor._plan_registry.get.return_value = plan

        with pytest.raises(pe_module.PlanExecutorError, match="Node not found"):
            await executor.execute_step(state.execution_id)

    @pytest.mark.asyncio
    async def test_node_execution_exception(self, executor, pe_module):
        """Branch: _execute_node raises -> state set_failed, PlanExecutorError raised."""
        state = FakeState(
            current_node_id="task-1",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[FakeNode(node_id="task-1")])
        executor._plan_registry.get.return_value = plan

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(side_effect=RuntimeError("LLM failed"))

        with pytest.raises(pe_module.PlanExecutorError, match="Node execution failed"):
            await executor.execute_step(state.execution_id)

        saved_state = await executor._persistence.load(state.execution_id)
        assert saved_state._failed is True

    @pytest.mark.asyncio
    async def test_clear_pause_with_user_input(self, executor, pe_module):
        """Branch: pending_user_input and user_input provided -> clear_pause called."""
        state = FakeState(
            current_node_id="task-1",
            status=pe_module.DocumentWorkflowStatus.PAUSED,
            pending_user_input=True,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[FakeNode(node_id="task-1")])
        executor._plan_registry.get.return_value = plan

        node_result = FakeNodeResult(outcome="success")

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(return_value=node_result)
        executor._persist_conversation = AsyncMock()
        executor._handle_result = AsyncMock()
        executor._sync_thread_status = AsyncMock()

        result = await executor.execute_step(state.execution_id, user_input="answer")
        assert result.pending_user_input is False

    @pytest.mark.asyncio
    async def test_internal_step_emitted_for_user_input(self, executor, pe_module):
        """Branch: result.requires_user_input and 'entry' in internals."""
        node = FakeNode(
            node_id="task-1",
            internals={"pass_a": {"type": "llm"}, "entry": {"type": "ui"}},
        )
        state = FakeState(
            current_node_id="task-1",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[node])
        executor._plan_registry.get.return_value = plan

        node_result = FakeNodeResult(
            outcome="needs_user_input",
            requires_user_input=True,
        )

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(return_value=node_result)
        executor._persist_conversation = AsyncMock()
        executor._handle_result = AsyncMock()
        executor._sync_thread_status = AsyncMock()
        executor._emit_internal_step = AsyncMock()

        await executor.execute_step(state.execution_id)

        executor._emit_internal_step.assert_called_once()
        call_args = executor._emit_internal_step.call_args
        assert call_args[0][3] == "entry"

    @pytest.mark.asyncio
    async def test_internal_step_emitted_for_phase_metadata(self, executor, pe_module):
        """Branch: result.metadata has 'phase' key and node has internals."""
        node = FakeNode(
            node_id="task-1",
            internals={"merge": {"type": "mech"}},
        )
        state = FakeState(
            current_node_id="task-1",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[node])
        executor._plan_registry.get.return_value = plan

        node_result = FakeNodeResult(
            outcome="success",
            metadata={"phase": "merge"},
        )

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(return_value=node_result)
        executor._persist_conversation = AsyncMock()
        executor._handle_result = AsyncMock()
        executor._sync_thread_status = AsyncMock()
        executor._emit_internal_step = AsyncMock()

        await executor.execute_step(state.execution_id)

        executor._emit_internal_step.assert_called_once()
        call_args = executor._emit_internal_step.call_args
        assert call_args[0][3] == "merge"

    @pytest.mark.asyncio
    async def test_qa_node_loads_pgc_answers(self, executor, pe_module):
        """Branch: current_node.is_qa_gate() and db_session -> _load_pgc_answers_for_qa called."""
        qa_node = FakeNode(node_id="qa-1", node_type="qa")
        state = FakeState(
            current_node_id="qa-1",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[qa_node])
        executor._plan_registry.get.return_value = plan
        executor._db_session = AsyncMock()

        node_result = FakeNodeResult(outcome="success")

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(return_value=node_result)
        executor._persist_conversation = AsyncMock()
        executor._handle_result = AsyncMock()
        executor._sync_thread_status = AsyncMock()
        executor._load_pgc_answers_for_qa = AsyncMock()

        await executor.execute_step(state.execution_id)

        executor._load_pgc_answers_for_qa.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_internals_no_internal_step(self, executor, pe_module):
        """Branch: node has no internals -> no internal_step emitted."""
        node = FakeNode(node_id="task-1", internals={})
        state = FakeState(
            current_node_id="task-1",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[node])
        executor._plan_registry.get.return_value = plan

        node_result = FakeNodeResult(outcome="success")

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(return_value=node_result)
        executor._persist_conversation = AsyncMock()
        executor._handle_result = AsyncMock()
        executor._sync_thread_status = AsyncMock()
        executor._emit_internal_step = AsyncMock()

        await executor.execute_step(state.execution_id)

        executor._emit_internal_step.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_qa_node_no_pgc_load(self, executor, pe_module):
        """Branch: node is not QA -> _load_pgc_answers_for_qa NOT called."""
        task_node = FakeNode(node_id="task-1", node_type="task")
        state = FakeState(
            current_node_id="task-1",
            status=pe_module.DocumentWorkflowStatus.RUNNING,
        )
        await executor._persistence.save(state)

        plan = FakePlan(nodes=[task_node])
        executor._plan_registry.get.return_value = plan
        executor._db_session = AsyncMock()

        node_result = FakeNodeResult(outcome="success")

        executor._build_context = AsyncMock(return_value=MagicMock())
        executor._execute_node = AsyncMock(return_value=node_result)
        executor._persist_conversation = AsyncMock()
        executor._handle_result = AsyncMock()
        executor._sync_thread_status = AsyncMock()
        executor._load_pgc_answers_for_qa = AsyncMock()

        await executor.execute_step(state.execution_id)

        executor._load_pgc_answers_for_qa.assert_not_called()

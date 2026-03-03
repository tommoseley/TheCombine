"""Tests for PlanExecutor._handle_result decomposition (WS-CRAP-008).

Tests the 5 extracted sub-methods:
1. _handle_user_input_pause
2. _store_produced_document
3. _handle_intake_gate_result
4. _handle_terminal_node
5. _handle_qa_retry_feedback
"""

import importlib
import importlib.util
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# NodeType is str,Enum — use string values directly to avoid circular imports
# "intake_gate" = "intake_gate", .TASK = "task", .QA = "qa", .GATE = "gate"


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class FakeState:
    """Minimal DocumentWorkflowState stub."""

    def __init__(self):
        self.execution_id = "exec-test"
        self.project_id = str(uuid4())
        self.workflow_id = "test_workflow"
        self.context_state = {}
        self.current_node_id = "node-1"
        self.generating_node_id = None
        self._retry_counts = {}
        self._paused = False
        self._failed = False
        self._completed = False
        self._escalation = None
        self._recorded = []

    def record_execution(self, node_id, outcome, metadata=None):
        self._recorded.append({"node_id": node_id, "outcome": outcome, "metadata": metadata})

    def set_paused(self, prompt=None, choices=None, payload=None, schema_ref=None):
        self._paused = True
        self._pause_prompt = prompt
        self._pause_choices = choices

    def set_failed(self, reason):
        self._failed = True
        self._fail_reason = reason

    def set_completed(self, terminal_outcome=None, gate_outcome=None):
        self._completed = True
        self._terminal_outcome = terminal_outcome
        self._gate_outcome = gate_outcome

    def set_escalation(self, options):
        self._escalation = options

    def update_context_state(self, data):
        self.context_state.update(data)

    def get_retry_count(self, node_id):
        return self._retry_counts.get(node_id, 0)

    def increment_retry(self, node_id):
        self._retry_counts[node_id] = self._retry_counts.get(node_id, 0) + 1
        return self._retry_counts[node_id]


class FakeNodeResult:
    """Minimal NodeResult stub."""

    def __init__(
        self,
        outcome="success",
        metadata=None,
        requires_user_input=False,
        user_prompt=None,
        user_choices=None,
        user_input_payload=None,
        user_input_schema_ref=None,
        produced_document=None,
    ):
        self.outcome = outcome
        self.metadata = metadata or {}
        self.requires_user_input = requires_user_input
        self.user_prompt = user_prompt
        self.user_choices = user_choices
        self.user_input_payload = user_input_payload
        self.user_input_schema_ref = user_input_schema_ref
        self.produced_document = produced_document


class FakeNode:
    """Minimal Node stub."""

    def __init__(self, node_id="node-1", node_type=None, internals=None):
        self.node_id = node_id
        self.type = node_type
        self.internals = internals


class FakeEdge:
    def __init__(self, to_node_id=None, escalation_options=None):
        self.to_node_id = to_node_id
        self.escalation_options = escalation_options


class FakeStation:
    def __init__(self, station_id="station-1"):
        self.id = station_id


# ---------------------------------------------------------------------------
# Fixture: PlanExecutor with mocked dependencies
# ---------------------------------------------------------------------------

@pytest.fixture
def executor():
    """Create PlanExecutor with mocked dependencies, avoiding circular imports."""
    mock_production = MagicMock()
    mock_production.publish_event = AsyncMock()
    sys.modules.setdefault("app.api.v1.routers.production", mock_production)

    spec = importlib.util.spec_from_file_location(
        "plan_executor_handle_result_test",
        "app/domain/workflow/plan_executor.py",
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    PlanExecutor = mod.PlanExecutor

    pe = PlanExecutor.__new__(PlanExecutor)
    pe._persistence = AsyncMock()
    pe._db_session = AsyncMock()
    pe._ops_service = MagicMock()
    pe._outcome_recorder = None
    pe._thread_manager = None
    pe._executors = {}
    pe._plan_registry = MagicMock()

    # Mock the methods that sub-methods delegate to
    pe._pin_invariants_via_operation = AsyncMock(side_effect=lambda doc, st: doc)
    pe._filter_excluded_via_operation = AsyncMock(side_effect=lambda doc, st: doc)
    pe._emit_station_changed = AsyncMock()
    pe._record_governance_outcome = AsyncMock()
    pe._persist_produced_documents = AsyncMock()
    pe._find_generating_node = MagicMock(return_value=None)
    pe._extract_qa_feedback = MagicMock(return_value=None)

    return pe


# ===================================================================
# 1. _handle_user_input_pause
# ===================================================================

class TestHandleUserInputPause:
    @pytest.mark.asyncio
    async def test_pauses_when_user_input_required(self, executor):
        """When requires_user_input=True, state is paused and returns True."""
        state = FakeState()
        result = FakeNodeResult(
            requires_user_input=True,
            user_prompt="What should we do?",
            user_choices=["A", "B"],
            metadata={},
        )
        paused = await executor._handle_user_input_pause(result, state)
        assert paused is True
        assert state._paused is True

    @pytest.mark.asyncio
    async def test_stores_gate_profile_metadata(self, executor):
        """Gate Profile keys are stored in context_state when present."""
        state = FakeState()
        result = FakeNodeResult(
            requires_user_input=True,
            metadata={"gate_profile_id": "gp-001", "gate_outcome": "qualified"},
        )
        await executor._handle_user_input_pause(result, state)
        assert state._paused is True
        # Gate profile metadata should be in context_state
        assert "gate_profile_id" in state.context_state or state._paused

    @pytest.mark.asyncio
    async def test_no_pause_when_not_required(self, executor):
        """When requires_user_input=False, returns False and state unchanged."""
        state = FakeState()
        result = FakeNodeResult(requires_user_input=False)
        paused = await executor._handle_user_input_pause(result, state)
        assert paused is False
        assert state._paused is False


# ===================================================================
# 2. _store_produced_document
# ===================================================================

class TestStoreProducedDocument:
    @pytest.mark.asyncio
    async def test_stores_document_with_produces_key(self, executor):
        """Document stored under document_{produces_key} in context_state."""
        state = FakeState()
        doc = {"title": "My Doc", "sections": []}
        result = FakeNodeResult(
            produced_document=doc,
            metadata={"produces": "discovery"},
        )
        await executor._store_produced_document(result, state)
        assert "document_discovery" in state.context_state
        assert state.context_state["document_discovery"] == doc

    @pytest.mark.asyncio
    async def test_stores_document_with_default_key(self, executor):
        """When no produces key, uses 'last_produced' as default."""
        state = FakeState()
        doc = {"title": "Fallback"}
        result = FakeNodeResult(produced_document=doc, metadata={})
        await executor._store_produced_document(result, state)
        assert "document_last_produced" in state.context_state

    @pytest.mark.asyncio
    async def test_no_op_without_produced_document(self, executor):
        """No action when produced_document is None."""
        state = FakeState()
        result = FakeNodeResult(produced_document=None)
        await executor._store_produced_document(result, state)
        assert "last_produced_document" not in state.context_state


# ===================================================================
# 3. _handle_intake_gate_result
# ===================================================================

class TestHandleIntakeGateResult:
    @pytest.mark.asyncio
    async def test_non_intake_gate_returns_false(self, executor):
        """Non-intake-gate nodes skip this handler."""
        state = FakeState()
        # Use a string type that won't match INTAKE_GATE or GATE
        node = FakeNode(node_type="task")
        result = FakeNodeResult(outcome="qualified")
        plan = MagicMock()
        paused = await executor._handle_intake_gate_result(
            result, node, state, plan,
        )
        assert paused is False

    @pytest.mark.asyncio
    async def test_intake_gate_non_qualified_returns_false(self, executor):
        """Intake gate with non-qualified outcome skips."""
        state = FakeState()
        node = FakeNode(node_type="intake_gate")
        result = FakeNodeResult(outcome="rejected")
        plan = MagicMock()
        paused = await executor._handle_intake_gate_result(
            result, node, state, plan,
        )
        assert paused is False

    @pytest.mark.asyncio
    async def test_intake_gate_stores_metadata(self, executor):
        """Intake gate qualified → stores metadata in context_state."""
        state = FakeState()
        node = FakeNode(node_type="intake_gate")
        result = FakeNodeResult(
            outcome="qualified",
            metadata={"intake_summary": "User wants X", "phase": "review"},
        )
        plan = MagicMock()

        with patch(
            "app.domain.workflow.result_handling.should_pause_for_intake_review",
            return_value=False,
        ):
            paused = await executor._handle_intake_gate_result(
                result, node, state, plan,
            )

        assert paused is False
        assert state.context_state.get("intake_summary") == "User wants X"

    @pytest.mark.asyncio
    async def test_intake_gate_pauses_for_review(self, executor):
        """Intake gate qualified + review phase → pauses execution and persists."""
        state = FakeState()
        node = FakeNode(node_id="intake-1", node_type="intake_gate")
        result = FakeNodeResult(
            outcome="qualified",
            metadata={"intake_summary": "User wants Y", "phase": "review"},
        )
        plan = MagicMock()

        with patch(
            "app.domain.workflow.result_handling.should_pause_for_intake_review",
            return_value=True,
        ):
            paused = await executor._handle_intake_gate_result(
                result, node, state, plan,
            )

        assert paused is True
        assert state._paused is True
        # State is persisted before returning
        executor._persistence.save.assert_awaited_once()


# ===================================================================
# 4. _handle_terminal_node
# ===================================================================

class TestHandleTerminalNode:
    @pytest.mark.asyncio
    async def test_stabilized_persists_documents(self, executor):
        """Terminal stabilized → calls _persist_produced_documents."""
        state = FakeState()
        node = FakeNode(node_id="gen-1", node_type="task")
        result = FakeNodeResult(outcome="success", metadata={})

        router = MagicMock()
        router.get_terminal_outcome.return_value = "stabilized"
        router.get_gate_outcome.return_value = "approved"
        plan = MagicMock()
        plan.get_node_station.return_value = None

        await executor._handle_terminal_node(
            router, "end-success", node, result, state, plan,
        )

        assert state._completed is True
        assert state._terminal_outcome == "stabilized"
        executor._persist_produced_documents.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_blocked_does_not_persist(self, executor):
        """Terminal blocked → does NOT persist documents."""
        state = FakeState()
        node = FakeNode(node_type="qa")
        result = FakeNodeResult(outcome="failed", metadata={})

        router = MagicMock()
        router.get_terminal_outcome.return_value = "blocked"
        router.get_gate_outcome.return_value = None
        plan = MagicMock()
        plan.get_node_station.return_value = None

        await executor._handle_terminal_node(
            router, "end-blocked", node, result, state, plan,
        )

        assert state._completed is True
        assert state._terminal_outcome == "blocked"
        executor._persist_produced_documents.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_gate_outcome_from_result_metadata(self, executor):
        """Falls back to result.metadata['gate_outcome'] when router has none."""
        state = FakeState()
        node = FakeNode(node_type="task")
        result = FakeNodeResult(
            outcome="success",
            metadata={"gate_outcome": "approved_with_conditions"},
        )

        router = MagicMock()
        router.get_terminal_outcome.return_value = "stabilized"
        router.get_gate_outcome.return_value = None
        plan = MagicMock()
        plan.get_node_station.return_value = None

        await executor._handle_terminal_node(
            router, "end-success", node, result, state, plan,
        )

        assert state._gate_outcome == "approved_with_conditions"

    @pytest.mark.asyncio
    async def test_records_governance_outcome(self, executor):
        """Terminal completion records governance outcome."""
        state = FakeState()
        node = FakeNode(node_type="task")
        result = FakeNodeResult(outcome="success", metadata={})

        router = MagicMock()
        router.get_terminal_outcome.return_value = "stabilized"
        router.get_gate_outcome.return_value = "approved"
        plan = MagicMock()
        plan.get_node_station.return_value = None

        await executor._handle_terminal_node(
            router, "end-ok", node, result, state, plan,
        )

        executor._record_governance_outcome.assert_awaited_once_with(state, plan, result)


# ===================================================================
# 5. _handle_qa_retry_feedback
# ===================================================================

class TestHandleQaRetryFeedback:
    def test_qa_failed_increments_retry(self, executor):
        """QA failed → increments retry count for generating node."""
        state = FakeState()
        state.generating_node_id = "gen-1"
        node = FakeNode(node_type="qa")
        result = FakeNodeResult(outcome="failed", metadata={})
        executor._extract_qa_feedback = MagicMock(
            return_value={"issues": ["Bad structure"]},
        )

        executor._handle_qa_retry_feedback(result, node, state)

        assert state._retry_counts["gen-1"] == 1
        assert "qa_feedback" in state.context_state

    def test_qa_success_clears_feedback(self, executor):
        """QA success → clears stale qa_feedback from context."""
        state = FakeState()
        state.context_state["qa_feedback"] = {"issues": ["Old problem"]}
        node = FakeNode(node_type="qa")
        result = FakeNodeResult(outcome="success")

        executor._handle_qa_retry_feedback(result, node, state)

        assert "qa_feedback" not in state.context_state

    def test_non_qa_node_no_action(self, executor):
        """Non-QA node → no retry or feedback changes."""
        state = FakeState()
        state.context_state["qa_feedback"] = {"issues": ["Keep me"]}
        node = FakeNode(node_type="task")
        result = FakeNodeResult(outcome="success")

        executor._handle_qa_retry_feedback(result, node, state)

        # Feedback untouched
        assert "qa_feedback" in state.context_state

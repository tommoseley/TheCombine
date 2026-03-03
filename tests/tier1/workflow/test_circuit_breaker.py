"""Tests for QA gate circuit breaker with gate-type nodes (WS-RING0-001).

Reproduces the exact RCA scenario: a gate-type QA node (type=gate,
gate_kind=qa) must trigger retry tracking and circuit breaker logic
in plan_executor. Before the fix, NodeType.GATE != NodeType.QA caused
the retry counter to never increment, creating an infinite loop.

This is the money test. It must fail before the fix and pass after.

Uses importlib bypass to avoid circular import through workflow/__init__.py.
"""

import importlib.util
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# ---------------------------------------------------------------------------
# Load modules via importlib to bypass circular import chain
# ---------------------------------------------------------------------------

# 1. plan_models (no app imports)
_pm_spec = importlib.util.spec_from_file_location(
    "plan_models_cb_test",
    "app/domain/workflow/plan_models.py",
)
_pm_mod = importlib.util.module_from_spec(_pm_spec)
_pm_spec.loader.exec_module(_pm_mod)
# Register so edge_router can find it
sys.modules.setdefault("app.domain.workflow.plan_models", _pm_mod)

Node = _pm_mod.Node
NodeType = _pm_mod.NodeType
Edge = _pm_mod.Edge
EdgeCondition = _pm_mod.EdgeCondition
ConditionOperator = _pm_mod.ConditionOperator
WorkflowPlan = _pm_mod.WorkflowPlan
ThreadOwnership = _pm_mod.ThreadOwnership
Governance = _pm_mod.Governance

# 2. document_workflow_state (no app imports)
_dws_spec = importlib.util.spec_from_file_location(
    "document_workflow_state_cb_test",
    "app/domain/workflow/document_workflow_state.py",
)
_dws_mod = importlib.util.module_from_spec(_dws_spec)
_dws_spec.loader.exec_module(_dws_mod)
sys.modules.setdefault("app.domain.workflow.document_workflow_state", _dws_mod)

DocumentWorkflowState = _dws_mod.DocumentWorkflowState
DocumentWorkflowStatus = _dws_mod.DocumentWorkflowStatus
NodeExecution = _dws_mod.NodeExecution

# 3. edge_router (imports plan_models + document_workflow_state, now pre-registered)
_er_spec = importlib.util.spec_from_file_location(
    "edge_router_cb_test",
    "app/domain/workflow/edge_router.py",
)
_er_mod = importlib.util.module_from_spec(_er_spec)
_er_spec.loader.exec_module(_er_mod)

EdgeRouter = _er_mod.EdgeRouter

# 4. plan_executor (needs production mock)
_mock_production = MagicMock()
_mock_production.publish_event = AsyncMock()
sys.modules.setdefault("app.api.v1.routers.production", _mock_production)

_pe_spec = importlib.util.spec_from_file_location(
    "plan_executor_cb_test",
    "app/domain/workflow/plan_executor.py",
    submodule_search_locations=[],
)
_pe_mod = importlib.util.module_from_spec(_pe_spec)
_pe_spec.loader.exec_module(_pe_mod)

PlanExecutor = _pe_mod.PlanExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_qa_gate_node() -> Node:
    """Create a gate-type QA node matching real workflow definitions."""
    return Node(
        node_id="qa_gate",
        type=NodeType.GATE,
        description="QA gate",
        gate_kind="qa",
    )


def _make_generation_node() -> Node:
    """Create a generation task node (the upstream producer)."""
    return Node(
        node_id="generation",
        type=NodeType.TASK,
        description="Document generation",
        produces="project_discovery",
    )


def _make_remediation_node() -> Node:
    return Node(
        node_id="remediation",
        type=NodeType.TASK,
        description="Remediation",
        produces="project_discovery",
    )


def _make_end_blocked_node() -> Node:
    return Node(
        node_id="end_blocked",
        type=NodeType.END,
        description="Blocked",
        terminal_outcome="blocked",
    )


def _make_end_stabilized_node() -> Node:
    return Node(
        node_id="end_stabilized",
        type=NodeType.END,
        description="Stabilized",
        terminal_outcome="stabilized",
    )


def _make_workflow_plan() -> WorkflowPlan:
    """Build a minimal workflow plan with QA → remediation loop + circuit breaker."""
    return WorkflowPlan(
        workflow_id="test_pd",
        version="1.0.0",
        name="Test PD",
        description="Test",
        scope_type="document",
        document_type="project_discovery",
        requires_inputs=[],
        entry_node_ids=["generation"],
        nodes=[
            _make_generation_node(),
            _make_qa_gate_node(),
            _make_remediation_node(),
            _make_end_blocked_node(),
            _make_end_stabilized_node(),
        ],
        edges=[
            Edge(
                edge_id="gen_to_qa",
                from_node_id="generation",
                to_node_id="qa_gate",
                outcome="success",
                label="To QA",
                kind="auto",
            ),
            Edge(
                edge_id="qa_pass",
                from_node_id="qa_gate",
                to_node_id="end_stabilized",
                outcome="pass",
                label="QA passed",
                kind="auto",
            ),
            Edge(
                edge_id="qa_fail_remediate",
                from_node_id="qa_gate",
                to_node_id="remediation",
                outcome="fail",
                label="Remediate",
                kind="auto",
                conditions=[
                    EdgeCondition(
                        type="retry_count",
                        operator=ConditionOperator.LT,
                        value=2,
                    )
                ],
            ),
            Edge(
                edge_id="qa_circuit_breaker",
                from_node_id="qa_gate",
                to_node_id="end_blocked",
                outcome="fail",
                label="Circuit breaker",
                kind="auto",
                conditions=[
                    EdgeCondition(
                        type="retry_count",
                        operator=ConditionOperator.GTE,
                        value=2,
                    )
                ],
            ),
            Edge(
                edge_id="remediation_to_qa",
                from_node_id="remediation",
                to_node_id="qa_gate",
                outcome="success",
                label="Back to QA",
                kind="auto",
            ),
        ],
        outcome_mapping=[],
        thread_ownership=ThreadOwnership(owns_thread=False),
        governance=Governance(adr_references=[]),
    )


def _make_state_with_history() -> DocumentWorkflowState:
    """Create state with generation node in history (needed by _find_generating_node)."""
    state = DocumentWorkflowState(
        execution_id="exec-test",
        workflow_id="test_pd",
        project_id="proj-1",
        document_type="project_discovery",
        current_node_id="qa_gate",
        status=DocumentWorkflowStatus.RUNNING,
    )
    state.node_history.append(
        NodeExecution(
            node_id="generation",
            outcome="success",
            timestamp=datetime.utcnow(),
        )
    )
    return state


class FakeNodeResult:
    """Minimal NodeResult stub for circuit breaker tests."""

    def __init__(self, outcome="failed", metadata=None):
        self.outcome = outcome
        self.metadata = metadata or {}
        self.requires_user_input = False
        self.user_prompt = None
        self.user_choices = None
        self.user_input_payload = None
        self.user_input_schema_ref = None
        self.produced_document = None


# ---------------------------------------------------------------------------
# Fixture: PlanExecutor with mocked dependencies
# ---------------------------------------------------------------------------

@pytest.fixture
def executor():
    """Create PlanExecutor with mocked dependencies."""
    pe = PlanExecutor.__new__(PlanExecutor)
    pe._db_session = AsyncMock()
    pe._persistence = AsyncMock()
    pe._ops_service = MagicMock()
    pe._outcome_recorder = None
    pe._thread_manager = None
    pe._executors = {}
    pe._plan_registry = MagicMock()
    pe._emit_station_changed = AsyncMock()
    pe._record_governance_outcome = AsyncMock()
    pe._persist_produced_documents = AsyncMock()
    pe._extract_qa_feedback = MagicMock(
        return_value={"issues": ["constraint language"], "summary": "test"},
    )
    return pe


# ===================================================================
# Circuit breaker integration tests
# ===================================================================

class TestPrepareQaRetryTrackingSetsGeneratingNode:
    """_prepare_qa_retry_tracking must set generating_node_id for gate-type QA nodes.

    This is the exact bug from the RCA: gate-type nodes (type=gate, gate_kind=qa)
    were silently skipped because the code checked NodeType.QA.
    """

    def test_gate_type_qa_node_sets_generating_node_id(self, executor):
        """Gate-type QA node (type=gate, gate_kind=qa) must set generating_node_id."""
        state = _make_state_with_history()
        plan = _make_workflow_plan()
        qa_node = plan.get_node("qa_gate")
        result = FakeNodeResult(outcome="failed")

        executor._prepare_qa_retry_tracking(result, qa_node, state, plan)

        assert state.generating_node_id == "generation", (
            "generating_node_id must be set for gate-type QA nodes. "
            "If this fails, the NodeType identity drift bug is still present."
        )


class TestHandleQaRetryFeedbackIncrementsForGateType:
    """_handle_qa_retry_feedback must increment retry count for gate-type QA nodes."""

    def test_gate_type_qa_increments_retry(self, executor):
        """Gate-type QA node must increment retry count."""
        state = _make_state_with_history()
        state.generating_node_id = "generation"
        qa_node = _make_qa_gate_node()
        result = FakeNodeResult(outcome="failed")

        executor._handle_qa_retry_feedback(result, qa_node, state)

        assert state.get_retry_count("generation") == 1

    def test_gate_type_qa_clears_feedback_on_success(self, executor):
        """Gate-type QA success must clear stale feedback."""
        state = _make_state_with_history()
        state.context_state["qa_feedback"] = {"issues": ["old"]}
        qa_node = _make_qa_gate_node()
        result = FakeNodeResult(outcome="success")

        executor._handle_qa_retry_feedback(result, qa_node, state)

        assert "qa_feedback" not in state.context_state


class TestCircuitBreakerTripsAfterThreshold:
    """End-to-end: after N QA failures, EdgeRouter must select the circuit breaker edge."""

    def test_breaker_trips_at_threshold(self):
        """After 2 retries, EdgeRouter selects qa_circuit_breaker → end_blocked."""
        plan = _make_workflow_plan()
        state = _make_state_with_history()
        state.generating_node_id = "generation"
        state.retry_counts["generation"] = 2

        router = EdgeRouter(plan)
        next_node_id, edge = router.get_next_node("qa_gate", "fail", state)

        assert next_node_id == "end_blocked", (
            f"Expected circuit breaker to route to end_blocked, got {next_node_id}"
        )
        assert edge.edge_id == "qa_circuit_breaker"

    def test_remediation_selected_below_threshold(self):
        """Below threshold, EdgeRouter selects qa_fail_remediate → remediation."""
        plan = _make_workflow_plan()
        state = _make_state_with_history()
        state.generating_node_id = "generation"
        state.retry_counts["generation"] = 1

        router = EdgeRouter(plan)
        next_node_id, edge = router.get_next_node("qa_gate", "fail", state)

        assert next_node_id == "remediation"
        assert edge.edge_id == "qa_fail_remediate"

    def test_remediation_selected_at_zero(self):
        """At zero retries, remediation is selected."""
        plan = _make_workflow_plan()
        state = _make_state_with_history()
        state.generating_node_id = "generation"
        state.retry_counts["generation"] = 0

        router = EdgeRouter(plan)
        next_node_id, edge = router.get_next_node("qa_gate", "fail", state)

        assert next_node_id == "remediation"
        assert edge.edge_id == "qa_fail_remediate"


class TestFullRetrySequence:
    """Simulate the full QA failure → retry tracking → circuit breaker sequence.

    This is the exact scenario from the RCA incident: gate-type QA node fails
    repeatedly, retry count must increment, and circuit breaker must eventually trip.
    """

    def test_full_sequence_gate_type_qa(self, executor):
        """3 QA failures on a gate-type QA node: 2 remediations then breaker trips."""
        plan = _make_workflow_plan()
        state = _make_state_with_history()
        qa_node = plan.get_node("qa_gate")
        router = EdgeRouter(plan)

        # --- QA failure #1 (retry_count=0) ---
        result = FakeNodeResult(outcome="failed")
        executor._prepare_qa_retry_tracking(result, qa_node, state, plan)
        assert state.generating_node_id == "generation"

        next_id, edge = router.get_next_node("qa_gate", "fail", state)
        assert next_id == "remediation", "First failure should route to remediation"

        executor._handle_qa_retry_feedback(result, qa_node, state)
        assert state.get_retry_count("generation") == 1

        # --- QA failure #2 (retry_count=1) ---
        executor._prepare_qa_retry_tracking(result, qa_node, state, plan)

        next_id, edge = router.get_next_node("qa_gate", "fail", state)
        assert next_id == "remediation", "Second failure should route to remediation"

        executor._handle_qa_retry_feedback(result, qa_node, state)
        assert state.get_retry_count("generation") == 2

        # --- QA failure #3 (retry_count=2) → circuit breaker ---
        executor._prepare_qa_retry_tracking(result, qa_node, state, plan)

        next_id, edge = router.get_next_node("qa_gate", "fail", state)
        assert next_id == "end_blocked", (
            f"Third failure must trip circuit breaker → end_blocked, got {next_id}"
        )
        assert edge.edge_id == "qa_circuit_breaker"

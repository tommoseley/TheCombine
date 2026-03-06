"""Tests for escalation wiring to QA circuit breaker (WS-RING0-002).

When the QA circuit breaker trips (retry count >= threshold), the workflow
should pause with escalation options ["retry", "abandon"] instead of
terminating at end_blocked.

Resolving with "retry" should reset the generating node's retry count and
re-enter the QA gate. Resolving with "abandon" should terminate with
terminal_outcome = "abandoned".

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
    "plan_models_esc_test",
    "app/domain/workflow/plan_models.py",
)
_pm_mod = importlib.util.module_from_spec(_pm_spec)
_pm_spec.loader.exec_module(_pm_mod)
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
    "document_workflow_state_esc_test",
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
    "edge_router_esc_test",
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
    "plan_executor_esc_test",
    "app/domain/workflow/plan_executor.py",
    submodule_search_locations=[],
)
_pe_mod = importlib.util.module_from_spec(_pe_spec)
_pe_spec.loader.exec_module(_pe_mod)

PlanExecutor = _pe_mod.PlanExecutor
PlanExecutorError = _pe_mod.PlanExecutorError


# ---------------------------------------------------------------------------
# Helpers: Build a workflow plan with escalation-wired circuit breaker
# ---------------------------------------------------------------------------

def _make_escalation_workflow_plan() -> WorkflowPlan:
    """Build a workflow plan where qa_circuit_breaker uses escalation.

    This is the target state after WS-RING0-002: the circuit breaker edge
    has to_node_id=None, non_advancing=True, escalation_options=["retry", "abandon"].
    """
    return WorkflowPlan(
        workflow_id="test_esc",
        version="1.0.0",
        name="Test Escalation",
        description="Test",
        scope_type="document",
        document_type="project_discovery",
        requires_inputs=[],
        entry_node_ids=["generation"],
        nodes=[
            Node(
                node_id="generation",
                type=NodeType.TASK,
                description="Document generation",
                produces="project_discovery",
            ),
            Node(
                node_id="qa_gate",
                type=NodeType.GATE,
                description="QA gate",
                gate_kind="qa",
            ),
            Node(
                node_id="remediation",
                type=NodeType.TASK,
                description="Remediation",
                produces="project_discovery",
            ),
            Node(
                node_id="end_stabilized",
                type=NodeType.END,
                description="Stabilized",
                terminal_outcome="stabilized",
            ),
            Node(
                node_id="end_blocked",
                type=NodeType.END,
                description="Blocked",
                terminal_outcome="blocked",
            ),
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
            # Circuit breaker → escalation (WS-RING0-002 target)
            Edge(
                edge_id="qa_circuit_breaker",
                from_node_id="qa_gate",
                to_node_id=None,
                outcome="fail",
                label="Circuit breaker - escalate to operator",
                kind="auto",
                non_advancing=True,
                escalation_options=["retry", "abandon"],
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


def _make_state_at_qa_with_retries(retry_count: int) -> DocumentWorkflowState:
    """Create state as if QA gate has been reached after N retries."""
    state = DocumentWorkflowState(
        execution_id="exec-esc-test",
        workflow_id="test_esc",
        project_id="proj-1",
        document_type="project_discovery",
        current_node_id="qa_gate",
        status=DocumentWorkflowStatus.RUNNING,
    )
    # Record generation in history (needed by _find_generating_node)
    state.node_history.append(
        NodeExecution(
            node_id="generation",
            outcome="success",
            timestamp=datetime.utcnow(),
        )
    )
    # Set generating node and retry counts
    state.generating_node_id = "generation"
    state.retry_counts["generation"] = retry_count
    return state


class FakeNodeResult:
    """Minimal NodeResult stub."""

    def __init__(self, outcome="failed", metadata=None):
        self.outcome = outcome
        self.metadata = metadata or {}
        self.requires_user_input = False
        self.user_prompt = None
        self.user_choices = None
        self.user_input_payload = None
        self.user_input_schema_ref = None
        self.produced_document = None


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
# Test: Circuit breaker trips -> workflow pauses with escalation
# ===================================================================

class TestCircuitBreakerTripsToEscalation:
    """When the circuit breaker trips, the workflow must pause with escalation
    options instead of terminating at end_blocked."""

    def test_circuit_breaker_routes_to_escalation_edge(self):
        """EdgeRouter selects the non-advancing escalation edge at threshold."""
        plan = _make_escalation_workflow_plan()
        state = _make_state_at_qa_with_retries(2)

        router = EdgeRouter(plan)
        next_node_id, edge = router.get_next_node("qa_gate", "fail", state)

        # The circuit breaker edge has to_node_id=None (non-advancing)
        assert next_node_id is None, (
            f"Expected non-advancing edge (None), got {next_node_id}"
        )
        assert edge is not None
        assert edge.edge_id == "qa_circuit_breaker"
        assert edge.escalation_options == ["retry", "abandon"]

    def test_state_becomes_paused_with_escalation(self):
        """After circuit breaker trip, state must be paused with escalation options."""
        plan = _make_escalation_workflow_plan()
        state = _make_state_at_qa_with_retries(2)

        router = EdgeRouter(plan)
        _next_id, matched_edge = router.get_next_node("qa_gate", "fail", state)

        # Simulate what PlanExecutor does when it gets a non-advancing edge
        if matched_edge and matched_edge.to_node_id is None:
            if matched_edge.escalation_options:
                state.set_escalation(matched_edge.escalation_options)

        assert state.status == DocumentWorkflowStatus.PAUSED
        assert state.escalation_active is True
        assert state.escalation_options == ["retry", "abandon"]


# ===================================================================
# Test: Resolve escalation with "retry"
# ===================================================================

class TestResolveEscalationRetry:
    """Resolving escalation with 'retry' must reset retry count for the
    GENERATING node and re-enter QA gate."""

    @pytest.mark.asyncio
    async def test_retry_resets_generating_node_retry_count(self, executor):
        """'retry' must reset retry count for the generating node, not current node."""
        state = _make_state_at_qa_with_retries(2)
        state.set_escalation(["retry", "abandon"])

        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.handle_escalation_choice("exec-esc-test", "retry")

        # Retry count for generating node must be reset
        assert result.get_retry_count("generation") == 0, (
            "retry must reset the GENERATING node's retry count (generation), "
            f"but got {result.get_retry_count('generation')}"
        )

    @pytest.mark.asyncio
    async def test_retry_sets_running_status(self, executor):
        """'retry' must set status back to running."""
        state = _make_state_at_qa_with_retries(2)
        state.set_escalation(["retry", "abandon"])

        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.handle_escalation_choice("exec-esc-test", "retry")

        assert result.status == DocumentWorkflowStatus.RUNNING

    @pytest.mark.asyncio
    async def test_retry_clears_escalation(self, executor):
        """'retry' must clear escalation state."""
        state = _make_state_at_qa_with_retries(2)
        state.set_escalation(["retry", "abandon"])

        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.handle_escalation_choice("exec-esc-test", "retry")

        assert result.escalation_active is False
        assert result.escalation_options == []


# ===================================================================
# Test: Resolve escalation with "abandon"
# ===================================================================

class TestResolveEscalationAbandon:
    """Resolving with 'abandon' must terminate with terminal_outcome='abandoned'."""

    @pytest.mark.asyncio
    async def test_abandon_sets_terminal_outcome(self, executor):
        """'abandon' must set terminal_outcome to 'abandoned'."""
        state = _make_state_at_qa_with_retries(2)
        state.set_escalation(["retry", "abandon"])

        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.handle_escalation_choice("exec-esc-test", "abandon")

        assert result.terminal_outcome == "abandoned"
        assert result.status == DocumentWorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_abandon_clears_escalation(self, executor):
        """'abandon' must clear escalation state."""
        state = _make_state_at_qa_with_retries(2)
        state.set_escalation(["retry", "abandon"])

        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.handle_escalation_choice("exec-esc-test", "abandon")

        assert result.escalation_active is False


# ===================================================================
# Test: Escalation without prior circuit breaker trip -> 409
# ===================================================================

class TestEscalationWithoutCircuitBreaker:
    """Calling handle_escalation_choice without an active escalation must fail."""

    @pytest.mark.asyncio
    async def test_no_escalation_active_raises(self, executor):
        """Escalation without active escalation raises PlanExecutorError."""
        state = _make_state_at_qa_with_retries(0)
        # No escalation set
        assert state.escalation_active is False

        executor._persistence.load = AsyncMock(return_value=state)

        with pytest.raises(PlanExecutorError, match="no active escalation"):
            await executor.handle_escalation_choice("exec-esc-test", "retry")

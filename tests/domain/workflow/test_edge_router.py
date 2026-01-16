"""Tests for EdgeRouter (ADR-039)."""

import pytest

from app.domain.workflow.edge_router import EdgeRouter, EdgeRoutingError
from app.domain.workflow.plan_models import (
    ConditionOperator,
    Edge,
    EdgeCondition,
    EdgeKind,
    Node,
    NodeType,
    OutcomeMapping,
    WorkflowPlan,
    ThreadOwnership,
    Governance,
)
from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
)


def make_plan(nodes, edges, outcome_mapping=None) -> WorkflowPlan:
    """Helper to create a WorkflowPlan with required fields."""
    return WorkflowPlan(
        workflow_id="test_workflow",
        version="1.0.0",
        name="Test Workflow",
        description="Test workflow plan",
        scope_type="document",
        document_type="test_doc",
        entry_node_ids=["start"] if any(n.node_id == "start" for n in nodes) else [nodes[0].node_id if nodes else "start"],
        nodes=nodes,
        edges=edges,
        outcome_mapping=outcome_mapping or [],
        thread_ownership=ThreadOwnership(owns_thread=False),
        governance=Governance(),
    )


def make_node(node_id: str, node_type: NodeType, **kwargs) -> Node:
    """Helper to create a Node with required fields."""
    return Node(
        node_id=node_id,
        type=node_type,
        description=kwargs.pop("description", f"Node {node_id}"),
        **kwargs,
    )


def make_edge(edge_id: str, from_node_id: str, outcome: str, to_node_id: str = None, **kwargs) -> Edge:
    """Helper to create an Edge with required fields."""
    return Edge(
        edge_id=edge_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        outcome=outcome,
        label=kwargs.pop("label", f"Edge {edge_id}"),
        kind=kwargs.pop("kind", EdgeKind.AUTO),
        **kwargs,
    )


class TestEdgeRouter:
    """Tests for EdgeRouter."""

    @pytest.fixture
    def simple_plan(self):
        """Create a simple workflow plan for testing."""
        nodes = [
            make_node("start", NodeType.TASK, task_ref="task1"),
            make_node("qa", NodeType.QA),
            make_node("gate", NodeType.GATE),
            make_node("end_success", NodeType.END, terminal_outcome="stabilized"),
            make_node("end_blocked", NodeType.END, terminal_outcome="blocked"),
        ]
        edges = [
            make_edge("e1", "start", "success", "qa"),
            make_edge("e2", "start", "failed", "end_blocked"),
            make_edge("e3", "qa", "success", "gate"),
            make_edge("e4", "qa", "failed", "start"),
            make_edge("e5", "gate", "success", "end_success"),
            make_edge("e6", "gate", "blocked", "end_blocked"),
        ]
        return make_plan(
            nodes=nodes,
            edges=edges,
            outcome_mapping=[
                OutcomeMapping(gate_outcome="qualified", terminal_outcome="stabilized"),
            ],
        )

    @pytest.fixture
    def state(self):
        """Create a basic workflow state."""
        return DocumentWorkflowState(
            execution_id="exec-123",
            workflow_id="test_workflow",
            document_id="doc-456",
            document_type="test_doc",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )

    @pytest.fixture
    def router(self, simple_plan):
        """Create router with simple plan."""
        return EdgeRouter(simple_plan)

    def test_get_next_node_success(self, router, state):
        """Router returns correct next node for success outcome."""
        next_node, edge = router.get_next_node("start", "success", state)

        assert next_node == "qa"
        assert edge is not None
        assert edge.outcome == "success"

    def test_get_next_node_failed(self, router, state):
        """Router returns correct next node for failed outcome."""
        next_node, edge = router.get_next_node("start", "failed", state)

        assert next_node == "end_blocked"

    def test_get_next_node_no_matching_edge(self, router, state):
        """Router returns None when no edge matches outcome."""
        next_node, edge = router.get_next_node("start", "unknown_outcome", state)

        assert next_node is None
        assert edge is None

    def test_get_next_node_no_edges(self, router, state):
        """Router returns None for node with no outbound edges."""
        next_node, edge = router.get_next_node("end_success", "success", state)

        assert next_node is None
        assert edge is None

    def test_routing_is_deterministic(self, router, state):
        """Same inputs always produce same outputs (pure function)."""
        for _ in range(100):
            next_node, edge = router.get_next_node("start", "success", state)
            assert next_node == "qa"

    def test_first_matching_edge_wins(self):
        """When multiple edges match, first one wins."""
        nodes = [
            make_node("start", NodeType.TASK, task_ref="t1"),
            make_node("node_a", NodeType.TASK, task_ref="t2"),
            make_node("node_b", NodeType.TASK, task_ref="t3"),
        ]
        edges = [
            # Two edges with same outcome - first should win
            make_edge("e1", "start", "success", "node_a"),
            make_edge("e2", "start", "success", "node_b"),
        ]
        plan = make_plan(nodes=nodes, edges=edges)
        router = EdgeRouter(plan)
        state = DocumentWorkflowState(
            execution_id="e1",
            workflow_id="test",
            document_id="d1",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )

        next_node, _ = router.get_next_node("start", "success", state)

        # First edge wins
        assert next_node == "node_a"


class TestEdgeConditions:
    """Tests for edge condition evaluation."""

    @pytest.fixture
    def plan_with_conditions(self):
        """Create plan with conditional edges."""
        nodes = [
            make_node("start", NodeType.TASK, task_ref="t1"),
            make_node("retry", NodeType.TASK, task_ref="t1"),
            make_node("escalate", NodeType.GATE),
            make_node("end", NodeType.END, terminal_outcome="blocked"),
        ]
        edges = [
            # Retry if retry_count < 2
            make_edge(
                "e1", "start", "failed", "retry",
                conditions=[
                    EdgeCondition(
                        type="retry_count",
                        operator=ConditionOperator.LT,
                        value=2,
                    )
                ],
            ),
            # Escalate if retry_count >= 2
            make_edge(
                "e2", "start", "failed", "escalate",
                conditions=[
                    EdgeCondition(
                        type="retry_count",
                        operator=ConditionOperator.GTE,
                        value=2,
                    )
                ],
            ),
        ]
        return make_plan(nodes=nodes, edges=edges)

    @pytest.fixture
    def router(self, plan_with_conditions):
        """Create router with conditional plan."""
        return EdgeRouter(plan_with_conditions)

    def test_condition_lt_passes(self, router):
        """Edge selected when retry_count < threshold."""
        state = DocumentWorkflowState(
            execution_id="e1",
            workflow_id="conditional_workflow",
            document_id="d1",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )
        # retry_count is 0

        next_node, _ = router.get_next_node("start", "failed", state)

        assert next_node == "retry"

    def test_condition_lt_fails_escalate(self, router):
        """Edge not selected when retry_count >= threshold, escalate selected."""
        state = DocumentWorkflowState(
            execution_id="e1",
            workflow_id="conditional_workflow",
            document_id="d1",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )
        state.increment_retry("start")
        state.increment_retry("start")
        # retry_count is now 2

        next_node, _ = router.get_next_node("start", "failed", state)

        assert next_node == "escalate"

    def test_all_operators(self):
        """Test all condition operators."""
        nodes = [make_node("start", NodeType.TASK, task_ref="t1")]
        plan = make_plan(nodes=nodes, edges=[])
        router = EdgeRouter(plan)

        # Test each operator
        assert router._compare(5, ConditionOperator.EQ, 5) is True
        assert router._compare(5, ConditionOperator.EQ, 6) is False

        assert router._compare(5, ConditionOperator.NE, 6) is True
        assert router._compare(5, ConditionOperator.NE, 5) is False

        assert router._compare(5, ConditionOperator.LT, 6) is True
        assert router._compare(5, ConditionOperator.LT, 5) is False

        assert router._compare(5, ConditionOperator.LTE, 5) is True
        assert router._compare(5, ConditionOperator.LTE, 4) is False

        assert router._compare(5, ConditionOperator.GT, 4) is True
        assert router._compare(5, ConditionOperator.GT, 5) is False

        assert router._compare(5, ConditionOperator.GTE, 5) is True
        assert router._compare(5, ConditionOperator.GTE, 6) is False

    def test_condition_with_none_value(self):
        """Condition returns False when actual value is None."""
        nodes = [make_node("start", NodeType.TASK, task_ref="t1")]
        plan = make_plan(nodes=nodes, edges=[])
        router = EdgeRouter(plan)

        # None should always return False
        assert router._compare(None, ConditionOperator.EQ, 5) is False
        assert router._compare(None, ConditionOperator.LT, 5) is False

    def test_multiple_conditions_all_must_pass(self):
        """All conditions must pass for edge to match (AND logic)."""
        nodes = [
            make_node("start", NodeType.TASK, task_ref="t1"),
            make_node("target", NodeType.END, terminal_outcome="done"),
        ]
        edges = [
            make_edge(
                "e1", "start", "success", "target",
                conditions=[
                    EdgeCondition(
                        type="retry_count",
                        operator=ConditionOperator.GTE,
                        value=1,
                    ),
                    EdgeCondition(
                        type="retry_count",
                        operator=ConditionOperator.LTE,
                        value=3,
                    ),
                ],
            )
        ]
        plan = make_plan(nodes=nodes, edges=edges)
        router = EdgeRouter(plan)

        # retry_count = 0: first condition fails
        state = DocumentWorkflowState(
            execution_id="e1",
            workflow_id="test",
            document_id="d1",
            document_type="test",
            current_node_id="start",
            status=DocumentWorkflowStatus.RUNNING,
        )
        next_node, _ = router.get_next_node("start", "success", state)
        assert next_node is None

        # retry_count = 2: both conditions pass
        state.increment_retry("start")
        state.increment_retry("start")
        next_node, _ = router.get_next_node("start", "success", state)
        assert next_node == "target"


class TestTerminalNodes:
    """Tests for terminal node handling."""

    @pytest.fixture
    def plan(self):
        """Create plan with terminal nodes."""
        nodes = [
            make_node("start", NodeType.TASK, task_ref="t1"),
            make_node("end_stabilized", NodeType.END, terminal_outcome="stabilized"),
            make_node("end_blocked", NodeType.END, terminal_outcome="blocked"),
            make_node("end_abandoned", NodeType.END, terminal_outcome="abandoned"),
        ]
        edges = [
            make_edge("e1", "start", "success", "end_stabilized"),
        ]
        return make_plan(nodes=nodes, edges=edges)

    @pytest.fixture
    def router(self, plan):
        """Create router."""
        return EdgeRouter(plan)

    def test_is_terminal_node(self, router):
        """is_terminal_node identifies end nodes."""
        assert router.is_terminal_node("end_stabilized") is True
        assert router.is_terminal_node("end_blocked") is True
        assert router.is_terminal_node("start") is False

    def test_is_terminal_node_unknown(self, router):
        """is_terminal_node returns False for unknown node."""
        assert router.is_terminal_node("nonexistent") is False

    def test_get_terminal_outcome(self, router):
        """get_terminal_outcome returns configured outcome."""
        assert router.get_terminal_outcome("end_stabilized") == "stabilized"
        assert router.get_terminal_outcome("end_blocked") == "blocked"
        assert router.get_terminal_outcome("end_abandoned") == "abandoned"

    def test_get_terminal_outcome_non_terminal(self, router):
        """get_terminal_outcome returns None for non-terminal nodes."""
        assert router.get_terminal_outcome("start") is None
        assert router.get_terminal_outcome("nonexistent") is None


class TestOutcomeValidation:
    """Tests for outcome validation."""

    @pytest.fixture
    def plan(self):
        """Create plan."""
        nodes = [
            make_node("start", NodeType.TASK, task_ref="t1"),
            make_node("end", NodeType.END, terminal_outcome="done"),
        ]
        edges = [
            make_edge("e1", "start", "success", "end"),
            make_edge("e2", "start", "failed", "start"),
        ]
        return make_plan(nodes=nodes, edges=edges)

    @pytest.fixture
    def router(self, plan):
        """Create router."""
        return EdgeRouter(plan)

    def test_validate_outcome_valid(self, router):
        """validate_outcome returns True for valid outcomes."""
        assert router.validate_outcome("start", "success") is True
        assert router.validate_outcome("start", "failed") is True

    def test_validate_outcome_invalid(self, router):
        """validate_outcome returns False for invalid outcomes."""
        assert router.validate_outcome("start", "unknown") is False
        assert router.validate_outcome("end", "success") is False


class TestEscalationOptions:
    """Tests for escalation handling."""

    def test_get_escalation_options(self):
        """get_escalation_options returns edge's escalation options."""
        edge = make_edge(
            "e1", "qa", "failed", None,  # Non-advancing (circuit breaker)
            escalation_options=["retry", "narrow_scope", "abandon"],
        )
        nodes = [make_node("start", NodeType.TASK, task_ref="t1")]
        plan = make_plan(nodes=nodes, edges=[edge])
        router = EdgeRouter(plan)

        options = router.get_escalation_options(edge)

        assert options == ["retry", "narrow_scope", "abandon"]

    def test_get_escalation_options_empty(self):
        """get_escalation_options returns empty list when none defined."""
        edge = make_edge("e1", "start", "success", "end")
        nodes = [make_node("start", NodeType.TASK, task_ref="t1")]
        plan = make_plan(nodes=nodes, edges=[edge])
        router = EdgeRouter(plan)

        options = router.get_escalation_options(edge)

        assert options == []


class TestNonAdvancingEdges:
    """Tests for non-advancing edges (circuit breaker behavior)."""

    def test_non_advancing_edge_returns_none_target(self):
        """Non-advancing edge returns None as target node."""
        edge = make_edge(
            "e1", "qa", "failed", None,  # Non-advancing
            escalation_options=["retry", "abandon"],
        )
        nodes = [make_node("qa", NodeType.QA)]
        plan = make_plan(nodes=nodes, edges=[edge])
        router = EdgeRouter(plan)
        state = DocumentWorkflowState(
            execution_id="e1",
            workflow_id="test",
            document_id="d1",
            document_type="test",
            current_node_id="qa",
            status=DocumentWorkflowStatus.RUNNING,
        )

        next_node, matched_edge = router.get_next_node("qa", "failed", state)

        assert next_node is None
        assert matched_edge is not None
        assert matched_edge.escalation_options == ["retry", "abandon"]

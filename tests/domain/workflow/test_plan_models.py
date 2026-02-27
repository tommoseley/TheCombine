"""Tests for Document Interaction Workflow Plan models (ADR-039)."""

import pytest

from app.domain.workflow.plan_models import (
    CircuitBreaker,
    ConditionOperator,
    Edge,
    EdgeCondition,
    EdgeKind,
    Governance,
    Node,
    NodeType,
    OutcomeMapping,
    ThreadOwnership,
    WorkflowPlan,
)


class TestNodeType:
    """Tests for NodeType enum."""

    def test_valid_node_types(self):
        """All valid node types are defined."""
        assert NodeType.TASK.value == "task"
        assert NodeType.QA.value == "qa"
        assert NodeType.GATE.value == "gate"
        assert NodeType.END.value == "end"

    def test_node_type_from_string(self):
        """NodeType can be created from string."""
        assert NodeType("task") == NodeType.TASK


class TestEdgeCondition:
    """Tests for EdgeCondition model."""

    def test_from_dict(self):
        """EdgeCondition parses from dict correctly."""
        raw = {
            "type": "retry_count",
            "operator": "gte",
            "value": 2,
        }
        condition = EdgeCondition.from_dict(raw)

        assert condition.type == "retry_count"
        assert condition.operator == ConditionOperator.GTE
        assert condition.value == 2

    def test_all_operators(self):
        """All condition operators are supported."""
        for op in ["eq", "ne", "lt", "lte", "gt", "gte"]:
            raw = {"type": "test", "operator": op, "value": 1}
            condition = EdgeCondition.from_dict(raw)
            assert condition.operator.value == op


class TestEdge:
    """Tests for Edge model."""

    def test_from_dict_minimal(self):
        """Edge parses minimal dict correctly."""
        raw = {
            "edge_id": "test_edge",
            "from_node_id": "node_a",
            "to_node_id": "node_b",
            "outcome": "success",
        }
        edge = Edge.from_dict(raw)

        assert edge.edge_id == "test_edge"
        assert edge.from_node_id == "node_a"
        assert edge.to_node_id == "node_b"
        assert edge.outcome == "success"
        assert edge.kind == EdgeKind.AUTO
        assert edge.conditions == []
        assert edge.escalation_options == []

    def test_from_dict_full(self):
        """Edge parses full dict correctly."""
        raw = {
            "edge_id": "qa_fail_circuit_breaker",
            "from_node_id": "qa",
            "to_node_id": "end_blocked",
            "outcome": "failed",
            "label": "QA failed, circuit breaker tripped",
            "kind": "auto",
            "conditions": [
                {"type": "retry_count", "operator": "gte", "value": 2}
            ],
            "escalation_options": ["ask_more_questions", "narrow_scope"],
        }
        edge = Edge.from_dict(raw)

        assert edge.edge_id == "qa_fail_circuit_breaker"
        assert len(edge.conditions) == 1
        assert edge.conditions[0].type == "retry_count"
        assert edge.escalation_options == ["ask_more_questions", "narrow_scope"]

    def test_non_advancing_edge(self):
        """Non-advancing edge has null to_node_id."""
        raw = {
            "edge_id": "ask_more",
            "from_node_id": "clarification",
            "to_node_id": None,
            "outcome": "needs_user_input",
            "non_advancing": True,
        }
        edge = Edge.from_dict(raw)

        assert edge.to_node_id is None
        assert edge.non_advancing is True


class TestNode:
    """Tests for Node model."""

    def test_gate_node(self):
        """Gate node parses correctly."""
        raw = {
            "node_id": "consent_gate",
            "type": "gate",
            "description": "Consent checkpoint",
            "requires_consent": True,
        }
        node = Node.from_dict(raw)

        assert node.node_id == "consent_gate"
        assert node.type == NodeType.GATE
        assert node.requires_consent is True

    def test_task_node(self):
        """Task node parses correctly."""
        raw = {
            "node_id": "generation",
            "type": "task",
            "description": "Generate document",
            "task_ref": "Intent Reflection v1.0",
            "produces": "concierge_intake_document",
        }
        node = Node.from_dict(raw)

        assert node.node_id == "generation"
        assert node.type == NodeType.TASK
        assert node.produces == "concierge_intake_document"

    def test_end_node(self):
        """End node parses correctly."""
        raw = {
            "node_id": "end_stabilized",
            "type": "end",
            "description": "Stabilized outcome",
            "terminal_outcome": "stabilized",
            "gate_outcome": "qualified",
        }
        node = Node.from_dict(raw)

        assert node.node_id == "end_stabilized"
        assert node.type == NodeType.END
        assert node.terminal_outcome == "stabilized"
        assert node.gate_outcome == "qualified"


class TestOutcomeMapping:
    """Tests for OutcomeMapping model."""

    def test_from_dict(self):
        """OutcomeMapping parses correctly."""
        raw = {
            "gate_outcome": "qualified",
            "terminal_outcome": "stabilized",
        }
        mapping = OutcomeMapping.from_dict(raw)

        assert mapping.gate_outcome == "qualified"
        assert mapping.terminal_outcome == "stabilized"


class TestThreadOwnership:
    """Tests for ThreadOwnership model."""

    def test_owns_thread(self):
        """Thread ownership with thread."""
        raw = {
            "owns_thread": True,
            "thread_purpose": "intake_conversation",
        }
        ownership = ThreadOwnership.from_dict(raw)

        assert ownership.owns_thread is True
        assert ownership.thread_purpose == "intake_conversation"

    def test_no_thread(self):
        """No thread ownership."""
        ownership = ThreadOwnership.from_dict({})

        assert ownership.owns_thread is False
        assert ownership.thread_purpose is None


class TestCircuitBreaker:
    """Tests for CircuitBreaker model."""

    def test_from_dict(self):
        """CircuitBreaker parses correctly."""
        raw = {
            "max_retries": 2,
            "applies_to": ["qa", "remediation"],
            "escalation_per_adr": "ADR-037",
        }
        cb = CircuitBreaker.from_dict(raw)

        assert cb.max_retries == 2
        assert cb.applies_to == ["qa", "remediation"]
        assert cb.escalation_per_adr == "ADR-037"


class TestGovernance:
    """Tests for Governance model."""

    def test_full_governance(self):
        """Full governance section parses correctly."""
        raw = {
            "adr_references": ["ADR-025", "ADR-037"],
            "circuit_breaker": {
                "max_retries": 2,
                "applies_to": ["qa"],
            },
            "staleness_handling": {
                "auto_reentry": False,
                "refresh_option": "refresh_intake",
            },
            "downstream_requirements": {
                "conditions": ["gate_outcome == qualified"],
            },
        }
        governance = Governance.from_dict(raw)

        assert governance.adr_references == ["ADR-025", "ADR-037"]
        assert governance.circuit_breaker is not None
        assert governance.circuit_breaker.max_retries == 2
        assert governance.staleness_handling is not None
        assert governance.staleness_handling.auto_reentry is False
        assert governance.downstream_requirements is not None
        assert "gate_outcome == qualified" in governance.downstream_requirements.conditions


class TestWorkflowPlan:
    """Tests for WorkflowPlan model."""

    @pytest.fixture
    def minimal_plan_dict(self):
        """Minimal valid plan dict."""
        return {
            "workflow_id": "test_plan",
            "version": "1.0.0",
            "name": "Test Plan",
            "description": "A test plan",
            "scope_type": "document",
            "document_type": "test_document",
            "entry_node_ids": ["start"],
            "nodes": [
                {"node_id": "start", "type": "task", "description": "Start"},
                {"node_id": "end", "type": "end", "description": "End",
                 "terminal_outcome": "stabilized"},
            ],
            "edges": [
                {"edge_id": "e1", "from_node_id": "start",
                 "to_node_id": "end", "outcome": "success"},
            ],
            "outcome_mapping": {"mappings": []},
            "thread_ownership": {"owns_thread": False},
            "governance": {},
        }

    def test_from_dict(self, minimal_plan_dict):
        """WorkflowPlan parses from dict."""
        plan = WorkflowPlan.from_dict(minimal_plan_dict)

        assert plan.workflow_id == "test_plan"
        assert plan.version == "1.0.0"
        assert plan.scope_type == "document"
        assert len(plan.nodes) == 2
        assert len(plan.edges) == 1

    def test_get_node(self, minimal_plan_dict):
        """get_node returns node by ID."""
        plan = WorkflowPlan.from_dict(minimal_plan_dict)

        node = plan.get_node("start")
        assert node is not None
        assert node.node_id == "start"

        assert plan.get_node("nonexistent") is None

    def test_get_edges_from(self, minimal_plan_dict):
        """get_edges_from returns edges from a node."""
        plan = WorkflowPlan.from_dict(minimal_plan_dict)

        edges = plan.get_edges_from("start")
        assert len(edges) == 1
        assert edges[0].to_node_id == "end"

        assert plan.get_edges_from("end") == []

    def test_get_entry_node(self, minimal_plan_dict):
        """get_entry_node returns primary entry node."""
        plan = WorkflowPlan.from_dict(minimal_plan_dict)

        entry = plan.get_entry_node()
        assert entry is not None
        assert entry.node_id == "start"

    def test_get_end_nodes(self, minimal_plan_dict):
        """get_end_nodes returns all end nodes."""
        plan = WorkflowPlan.from_dict(minimal_plan_dict)

        end_nodes = plan.get_end_nodes()
        assert len(end_nodes) == 1
        assert end_nodes[0].node_id == "end"

    def test_map_gate_to_terminal(self):
        """map_gate_to_terminal is a pure lookup function."""
        plan_dict = {
            "workflow_id": "test",
            "entry_node_ids": ["start"],
            "nodes": [
                {"node_id": "start", "type": "gate", "description": "Gate",
                 "gate_outcomes": ["qualified", "not_ready"]},
            ],
            "edges": [],
            "outcome_mapping": {
                "mappings": [
                    {"gate_outcome": "qualified", "terminal_outcome": "stabilized"},
                    {"gate_outcome": "not_ready", "terminal_outcome": "blocked"},
                ]
            },
        }
        plan = WorkflowPlan.from_dict(plan_dict)

        assert plan.map_gate_to_terminal("qualified") == "stabilized"
        assert plan.map_gate_to_terminal("not_ready") == "blocked"
        assert plan.map_gate_to_terminal("unknown") is None

    def test_indexes_built_on_init(self, minimal_plan_dict):
        """Indexes are built during initialization."""
        plan = WorkflowPlan.from_dict(minimal_plan_dict)

        # Verify internal indexes exist and are populated
        assert "start" in plan._nodes_by_id
        assert "start" in plan._edges_by_from

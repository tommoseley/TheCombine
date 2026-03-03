"""Tests for Node.is_qa_gate() predicate (WS-RING0-001).

Validates the canonical definition of QA-ness on the Node model.
This predicate is the single source of truth for whether a node
is a QA gate, regardless of how it was defined in the workflow.

Uses importlib bypass to avoid circular import through workflow/__init__.py.
"""

import importlib.util

# Load plan_models directly (no app imports, safe from circular chain)
_spec = importlib.util.spec_from_file_location(
    "plan_models_test",
    "app/domain/workflow/plan_models.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Node = _mod.Node
NodeType = _mod.NodeType


def _make_node(node_type: str, gate_kind: str = None, **kwargs) -> Node:
    """Create a minimal Node for predicate testing."""
    return Node(
        node_id=kwargs.get("node_id", "test-node"),
        type=NodeType(node_type),
        description="test",
        gate_kind=gate_kind,
    )


class TestIsQaGate:
    """Node.is_qa_gate() — canonical QA identity predicate."""

    def test_node_type_qa_returns_true(self):
        """NodeType.QA is a QA gate (legacy/direct definition)."""
        node = _make_node("qa")
        assert node.is_qa_gate() is True

    def test_gate_type_with_gate_kind_qa_returns_true(self):
        """NodeType.GATE + gate_kind='qa' is a QA gate (workflow v2 pattern)."""
        node = _make_node("gate", gate_kind="qa")
        assert node.is_qa_gate() is True

    def test_gate_type_with_gate_kind_pgc_returns_false(self):
        """PGC gates are not QA gates."""
        node = _make_node("gate", gate_kind="pgc")
        assert node.is_qa_gate() is False

    def test_gate_type_with_no_gate_kind_returns_false(self):
        """Gate nodes without gate_kind are not QA gates."""
        node = _make_node("gate", gate_kind=None)
        assert node.is_qa_gate() is False

    def test_task_type_returns_false(self):
        """Task nodes are not QA gates."""
        node = _make_node("task")
        assert node.is_qa_gate() is False

    def test_end_type_returns_false(self):
        """End nodes are not QA gates."""
        node = _make_node("end")
        assert node.is_qa_gate() is False


class TestFromDictParsesGateKind:
    """Node.from_dict() must parse gate_kind from raw config."""

    def test_gate_kind_parsed_from_raw(self):
        raw = {
            "node_id": "qa_gate",
            "type": "gate",
            "gate_kind": "qa",
            "description": "QA gate",
        }
        node = Node.from_dict(raw)
        assert node.gate_kind == "qa"
        assert node.is_qa_gate() is True

    def test_gate_kind_none_when_absent(self):
        raw = {
            "node_id": "gen",
            "type": "task",
            "description": "task node",
        }
        node = Node.from_dict(raw)
        assert node.gate_kind is None

    def test_pgc_gate_kind_parsed(self):
        raw = {
            "node_id": "pgc_gate",
            "type": "gate",
            "gate_kind": "pgc",
            "description": "PGC gate",
        }
        node = Node.from_dict(raw)
        assert node.gate_kind == "pgc"
        assert node.is_qa_gate() is False

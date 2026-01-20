"""Tests for Concierge Intake Workflow Plan v1.2.0 schema structure.

This test validates the JSON structure of the intake workflow plan.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def workflow_plan():
    """Load the actual concierge_intake workflow plan."""
    plan_path = Path(__file__).parent.parent.parent.parent / "seed" / "workflows" / "concierge_intake.v1.json"
    with open(plan_path) as f:
        return json.load(f)


class TestWorkflowPlanStructure:
    """Tests for top-level workflow plan structure."""

    def test_workflow_id_is_snake_case(self, workflow_plan):
        assert workflow_plan["workflow_id"] == "concierge_intake"

    def test_has_version(self, workflow_plan):
        assert workflow_plan["version"] == "1.2.0"

    def test_has_entry_node(self, workflow_plan):
        assert "entry_node_ids" in workflow_plan
        assert "intake" in workflow_plan["entry_node_ids"]

    def test_scope_type_is_document(self, workflow_plan):
        assert workflow_plan["scope_type"] == "document"

    def test_has_nodes(self, workflow_plan):
        assert "nodes" in workflow_plan
        assert len(workflow_plan["nodes"]) == 7

    def test_has_edges(self, workflow_plan):
        assert "edges" in workflow_plan
        assert len(workflow_plan["edges"]) >= 10


class TestNodeTypes:
    """Tests for node type definitions."""

    def test_all_nodes_have_valid_type(self, workflow_plan):
        valid_types = {"intake_gate", "task", "qa", "end"}
        for node in workflow_plan["nodes"]:
            assert node["type"] in valid_types, f"Invalid type: {node['type']}"

    def test_intake_is_intake_gate_type(self, workflow_plan):
        intake = next(n for n in workflow_plan["nodes"] if n["node_id"] == "intake")
        assert intake["type"] == "intake_gate"

    def test_generation_is_task_type(self, workflow_plan):
        gen = next(n for n in workflow_plan["nodes"] if n["node_id"] == "generation")
        assert gen["type"] == "task"

    def test_qa_is_qa_type(self, workflow_plan):
        qa = next(n for n in workflow_plan["nodes"] if n["node_id"] == "qa")
        assert qa["type"] == "qa"

    def test_end_nodes_are_end_type(self, workflow_plan):
        end_nodes = [n for n in workflow_plan["nodes"] if n["node_id"].startswith("end_")]
        assert len(end_nodes) == 3
        for node in end_nodes:
            assert node["type"] == "end"


class TestEndNodeOutcomes:
    """Tests for end node terminal outcomes."""

    def test_end_stabilized_has_correct_terminal(self, workflow_plan):
        node = next(n for n in workflow_plan["nodes"] if n["node_id"] == "end_stabilized")
        assert node["terminal_outcome"] == "stabilized"
        assert node["gate_outcome"] == "qualified"

    def test_end_blocked_has_correct_terminal(self, workflow_plan):
        node = next(n for n in workflow_plan["nodes"] if n["node_id"] == "end_blocked")
        assert node["terminal_outcome"] == "blocked"
        assert node["gate_outcome"] == "not_ready"

    def test_end_abandoned_has_correct_terminal(self, workflow_plan):
        node = next(n for n in workflow_plan["nodes"] if n["node_id"] == "end_abandoned")
        assert node["terminal_outcome"] == "abandoned"


class TestThreadOwnership:
    """Tests for thread ownership configuration."""

    def test_declares_thread_ownership(self, workflow_plan):
        assert "thread_ownership" in workflow_plan

    def test_thread_has_null_purpose(self, workflow_plan):
        assert workflow_plan["thread_ownership"]["owns_thread"] == False
        assert workflow_plan["thread_ownership"]["thread_purpose"] is None


class TestIntakeToGeneration:
    """Tests for intake node routing."""

    def test_intake_routes_to_generation_on_qualified(self, workflow_plan):
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "intake_qualified")
        assert edge["from_node_id"] == "intake"
        assert edge["to_node_id"] == "generation"
        assert edge["outcome"] == "qualified"

    def test_intake_has_needs_user_input_edge(self, workflow_plan):
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "intake_insufficient")
        assert edge["outcome"] == "needs_user_input"
        assert edge.get("non_advancing") == True

    def test_intake_has_out_of_scope_edge(self, workflow_plan):
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "intake_out_of_scope")
        assert edge["to_node_id"] == "end_abandoned"
        assert edge["outcome"] == "out_of_scope"

    def test_intake_has_redirect_edge(self, workflow_plan):
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "intake_redirect")
        assert edge["to_node_id"] == "end_abandoned"
        assert edge["outcome"] == "redirect"


class TestQARouting:
    """Tests for QA node routing - auto-complete on success."""

    def test_qa_pass_goes_to_end_stabilized(self, workflow_plan):
        """QA success auto-completes as qualified (v1.2.0 change)."""
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "qa_pass")
        assert edge["from_node_id"] == "qa"
        assert edge["to_node_id"] == "end_stabilized"
        assert edge["outcome"] == "success"

    def test_qa_fail_routes_to_remediation(self, workflow_plan):
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "qa_fail_remediate")
        assert edge["from_node_id"] == "qa"
        assert edge["to_node_id"] == "remediation"
        assert edge["outcome"] == "failed"

    def test_qa_fail_has_circuit_breaker_edge(self, workflow_plan):
        edge = next(e for e in workflow_plan["edges"] if e["edge_id"] == "qa_fail_circuit_breaker")
        assert edge["from_node_id"] == "qa"
        assert edge["to_node_id"] == "end_blocked"
        assert "conditions" in edge


class TestCircuitBreaker:
    """Tests for circuit breaker configuration."""

    def test_governance_declares_circuit_breaker(self, workflow_plan):
        assert "governance" in workflow_plan
        assert "circuit_breaker" in workflow_plan["governance"]

    def test_circuit_breaker_has_max_retries(self, workflow_plan):
        cb = workflow_plan["governance"]["circuit_breaker"]
        assert cb["max_retries"] == 2

    def test_circuit_breaker_applies_to_qa_and_remediation(self, workflow_plan):
        cb = workflow_plan["governance"]["circuit_breaker"]
        assert "qa" in cb["applies_to"]
        assert "remediation" in cb["applies_to"]


class TestGraphIntegrity:
    """Tests for workflow graph integrity."""

    def test_all_edge_targets_exist(self, workflow_plan):
        node_ids = {n["node_id"] for n in workflow_plan["nodes"]}
        node_ids.add("")  # Allow empty target for non-advancing edges
        node_ids.add(None)  # Also allow None
        for edge in workflow_plan["edges"]:
            assert edge["to_node_id"] in node_ids, f"Edge {edge['edge_id']} targets non-existent node {edge['to_node_id']}"

    def test_all_edge_sources_exist(self, workflow_plan):
        node_ids = {n["node_id"] for n in workflow_plan["nodes"]}
        for edge in workflow_plan["edges"]:
            assert edge["from_node_id"] in node_ids, f"Edge {edge['edge_id']} sources from non-existent node {edge['from_node_id']}"

    def test_entry_node_exists(self, workflow_plan):
        node_ids = {n["node_id"] for n in workflow_plan["nodes"]}
        for entry in workflow_plan["entry_node_ids"]:
            assert entry in node_ids

    def test_all_non_end_nodes_have_outbound_edges(self, workflow_plan):
        non_end_nodes = {n["node_id"] for n in workflow_plan["nodes"] if n["type"] != "end"}
        edge_sources = {e["from_node_id"] for e in workflow_plan["edges"]}
        for node_id in non_end_nodes:
            assert node_id in edge_sources, f"Node {node_id} has no outbound edges"


class TestADRReferences:
    """Tests for ADR compliance references."""

    def test_has_governance_adr_references(self, workflow_plan):
        assert "governance" in workflow_plan
        assert "adr_references" in workflow_plan["governance"]

    def test_references_key_adrs(self, workflow_plan):
        refs = workflow_plan["governance"]["adr_references"]
        assert "ADR-025" in refs  # Intake Gate
        assert "ADR-039" in refs  # Document Interaction Workflows
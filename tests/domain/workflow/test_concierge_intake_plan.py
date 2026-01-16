"""
Tests for Concierge Intake Document Workflow Plan (WS-INTAKE-WORKFLOW-001).

Validates the workflow plan structure per ADR-038 and ADR-039 requirements.
"""

import pytest
import json
from pathlib import Path


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def workflow_plan():
    """Load the concierge intake workflow plan."""
    plan_path = Path(__file__).parent.parent.parent.parent / "seed" / "workflows" / "concierge_intake.v1.json"
    with open(plan_path) as f:
        return json.load(f)


@pytest.fixture
def nodes_by_id(workflow_plan):
    """Index nodes by node_id for easy lookup."""
    return {node["node_id"]: node for node in workflow_plan["nodes"]}


@pytest.fixture
def edges_by_from(workflow_plan):
    """Index edges by from_node_id."""
    result = {}
    for edge in workflow_plan["edges"]:
        from_id = edge["from_node_id"]
        if from_id not in result:
            result[from_id] = []
        result[from_id].append(edge)
    return result


# =============================================================================
# Test: Basic Structure
# =============================================================================

class TestWorkflowPlanStructure:
    """Tests for basic workflow plan structure."""

    def test_workflow_id_is_snake_case(self, workflow_plan):
        """Workflow ID follows snake_case convention."""
        assert workflow_plan["workflow_id"] == "concierge_intake"

    def test_has_version(self, workflow_plan):
        """Workflow has a version."""
        assert "version" in workflow_plan
        assert workflow_plan["version"] == "1.0.0"

    def test_has_entry_node(self, workflow_plan):
        """Workflow has exactly one entry node."""
        assert "entry_node_ids" in workflow_plan
        assert len(workflow_plan["entry_node_ids"]) == 1
        assert workflow_plan["entry_node_ids"][0] == "clarification"

    def test_scope_type_is_document(self, workflow_plan):
        """Workflow is document-scoped per ADR-039."""
        assert workflow_plan["scope_type"] == "document"

    def test_has_nodes(self, workflow_plan):
        """Workflow has nodes defined."""
        assert "nodes" in workflow_plan
        assert len(workflow_plan["nodes"]) > 0

    def test_has_edges(self, workflow_plan):
        """Workflow has edges defined."""
        assert "edges" in workflow_plan
        assert len(workflow_plan["edges"]) > 0


# =============================================================================
# Test: Node Types (ADR-039)
# =============================================================================

class TestNodeTypes:
    """Tests for node type validity per ADR-039."""

    VALID_NODE_TYPES = {"concierge", "task", "qa", "gate", "end"}

    def test_all_nodes_have_valid_type(self, workflow_plan):
        """All nodes have a valid type."""
        for node in workflow_plan["nodes"]:
            assert node["type"] in self.VALID_NODE_TYPES, \
                f"Node {node['node_id']} has invalid type: {node['type']}"

    def test_clarification_is_concierge_type(self, nodes_by_id):
        """Clarification node is concierge type."""
        assert nodes_by_id["clarification"]["type"] == "concierge"

    def test_consent_gate_is_gate_type(self, nodes_by_id):
        """Consent gate is gate type."""
        assert nodes_by_id["consent_gate"]["type"] == "gate"

    def test_generation_is_task_type(self, nodes_by_id):
        """Generation node is task type."""
        assert nodes_by_id["generation"]["type"] == "task"

    def test_qa_is_qa_type(self, nodes_by_id):
        """QA node is qa type."""
        assert nodes_by_id["qa"]["type"] == "qa"

    def test_end_nodes_are_end_type(self, nodes_by_id):
        """All end nodes are end type."""
        end_nodes = ["end_stabilized", "end_blocked", "end_abandoned"]
        for node_id in end_nodes:
            assert nodes_by_id[node_id]["type"] == "end"


# =============================================================================
# Test: Terminal Outcome Mapping (ADR-025 / ADR-039)
# =============================================================================

class TestOutcomeMapping:
    """Tests for deterministic outcome mapping per ADR-025 amendment."""

    def test_has_outcome_mapping(self, workflow_plan):
        """Workflow has explicit outcome mapping."""
        assert "outcome_mapping" in workflow_plan
        assert "mappings" in workflow_plan["outcome_mapping"]

    def test_qualified_maps_to_stabilized(self, workflow_plan):
        """Gate outcome 'qualified' maps to terminal 'stabilized'."""
        mappings = {m["gate_outcome"]: m["terminal_outcome"]
                   for m in workflow_plan["outcome_mapping"]["mappings"]}
        assert mappings["qualified"] == "stabilized"

    def test_not_ready_maps_to_blocked(self, workflow_plan):
        """Gate outcome 'not_ready' maps to terminal 'blocked'."""
        mappings = {m["gate_outcome"]: m["terminal_outcome"]
                   for m in workflow_plan["outcome_mapping"]["mappings"]}
        assert mappings["not_ready"] == "blocked"

    def test_out_of_scope_maps_to_abandoned(self, workflow_plan):
        """Gate outcome 'out_of_scope' maps to terminal 'abandoned'."""
        mappings = {m["gate_outcome"]: m["terminal_outcome"]
                   for m in workflow_plan["outcome_mapping"]["mappings"]}
        assert mappings["out_of_scope"] == "abandoned"

    def test_redirect_maps_to_abandoned(self, workflow_plan):
        """Gate outcome 'redirect' maps to terminal 'abandoned'."""
        mappings = {m["gate_outcome"]: m["terminal_outcome"]
                   for m in workflow_plan["outcome_mapping"]["mappings"]}
        assert mappings["redirect"] == "abandoned"

    def test_end_stabilized_has_correct_terminal(self, nodes_by_id):
        """end_stabilized node has terminal_outcome = stabilized."""
        assert nodes_by_id["end_stabilized"]["terminal_outcome"] == "stabilized"

    def test_end_blocked_has_correct_terminal(self, nodes_by_id):
        """end_blocked node has terminal_outcome = blocked."""
        assert nodes_by_id["end_blocked"]["terminal_outcome"] == "blocked"

    def test_end_abandoned_has_correct_terminal(self, nodes_by_id):
        """end_abandoned node has terminal_outcome = abandoned."""
        assert nodes_by_id["end_abandoned"]["terminal_outcome"] == "abandoned"


# =============================================================================
# Test: Thread Ownership (ADR-035)
# =============================================================================

class TestThreadOwnership:
    """Tests for thread ownership per ADR-035."""

    def test_declares_thread_ownership(self, workflow_plan):
        """Workflow declares thread ownership."""
        assert "thread_ownership" in workflow_plan
        assert workflow_plan["thread_ownership"]["owns_thread"] is True

    def test_thread_has_purpose(self, workflow_plan):
        """Thread has a declared purpose."""
        assert "thread_purpose" in workflow_plan["thread_ownership"]
        assert workflow_plan["thread_ownership"]["thread_purpose"] == "intake_conversation"


# =============================================================================
# Test: Consent Gate (Explicit Consent)
# =============================================================================

class TestConsentGate:
    """Tests for explicit consent requirement."""

    def test_consent_gate_exists(self, nodes_by_id):
        """Consent gate node exists."""
        assert "consent_gate" in nodes_by_id

    def test_consent_gate_requires_consent(self, nodes_by_id):
        """Consent gate has requires_consent = true."""
        assert nodes_by_id["consent_gate"].get("requires_consent") is True

    def test_consent_gate_before_generation(self, edges_by_from):
        """Consent gate is between clarification and generation."""
        # clarification -> consent_gate
        clarification_edges = edges_by_from.get("clarification", [])
        consent_edge = next((e for e in clarification_edges
                            if e["to_node_id"] == "consent_gate"), None)
        assert consent_edge is not None, "No edge from clarification to consent_gate"

        # consent_gate -> generation
        consent_edges = edges_by_from.get("consent_gate", [])
        generation_edge = next((e for e in consent_edges
                               if e["to_node_id"] == "generation"), None)
        assert generation_edge is not None, "No edge from consent_gate to generation"


# =============================================================================
# Test: Circuit Breaker (max_retries = 2)
# =============================================================================

class TestCircuitBreaker:
    """Tests for circuit breaker per ADR-037."""

    def test_governance_declares_circuit_breaker(self, workflow_plan):
        """Governance section declares circuit breaker."""
        assert "governance" in workflow_plan
        assert "circuit_breaker" in workflow_plan["governance"]
        assert workflow_plan["governance"]["circuit_breaker"]["max_retries"] == 2

    def test_qa_fail_has_circuit_breaker_edge(self, edges_by_from):
        """QA failure has circuit breaker edge to end_blocked."""
        qa_edges = edges_by_from.get("qa", [])
        circuit_breaker_edge = next(
            (e for e in qa_edges
             if e["to_node_id"] == "end_blocked" and e["outcome"] == "failed"),
            None
        )
        assert circuit_breaker_edge is not None, "No circuit breaker edge from QA"

    def test_circuit_breaker_has_retry_condition(self, edges_by_from):
        """Circuit breaker edge has retry count condition."""
        qa_edges = edges_by_from.get("qa", [])
        circuit_breaker_edge = next(
            (e for e in qa_edges
             if e["to_node_id"] == "end_blocked" and e["outcome"] == "failed"),
            None
        )
        assert "conditions" in circuit_breaker_edge
        condition = circuit_breaker_edge["conditions"][0]
        assert condition["type"] == "retry_count"
        assert condition["operator"] == "gte"
        assert condition["value"] == 2

    def test_circuit_breaker_has_escalation_options(self, edges_by_from):
        """Circuit breaker edge declares escalation options."""
        qa_edges = edges_by_from.get("qa", [])
        circuit_breaker_edge = next(
            (e for e in qa_edges
             if e["to_node_id"] == "end_blocked" and e["outcome"] == "failed"),
            None
        )
        assert "escalation_options" in circuit_breaker_edge
        options = circuit_breaker_edge["escalation_options"]
        assert "ask_more_questions" in options
        assert "narrow_scope" in options
        assert "abandon" in options


# =============================================================================
# Test: Staleness Handling (ADR-036)
# =============================================================================

class TestStalenessHandling:
    """Tests for staleness handling per ADR-036."""

    def test_governance_declares_staleness_handling(self, workflow_plan):
        """Governance section declares staleness handling."""
        assert "staleness_handling" in workflow_plan["governance"]

    def test_no_auto_reentry(self, workflow_plan):
        """Auto re-entry is disabled."""
        staleness = workflow_plan["governance"]["staleness_handling"]
        assert staleness["auto_reentry"] is False

    def test_has_refresh_option(self, workflow_plan):
        """Refresh option is declared."""
        staleness = workflow_plan["governance"]["staleness_handling"]
        assert "refresh_option" in staleness


# =============================================================================
# Test: Downstream Requirements
# =============================================================================

class TestDownstreamRequirements:
    """Tests for downstream document creation requirements."""

    def test_governance_declares_downstream_requirements(self, workflow_plan):
        """Governance section declares downstream requirements."""
        assert "downstream_requirements" in workflow_plan["governance"]

    def test_requires_qualified_gate_outcome(self, workflow_plan):
        """Downstream requires gate_outcome == qualified."""
        conditions = workflow_plan["governance"]["downstream_requirements"]["conditions"]
        assert "gate_outcome == qualified" in conditions

    def test_requires_stabilized_terminal(self, workflow_plan):
        """Downstream requires document_workflow_terminal == stabilized."""
        conditions = workflow_plan["governance"]["downstream_requirements"]["conditions"]
        assert "document_workflow_terminal == stabilized" in conditions

    def test_requires_accepted_lifecycle(self, workflow_plan):
        """Downstream requires document_lifecycle_state == accepted."""
        conditions = workflow_plan["governance"]["downstream_requirements"]["conditions"]
        assert "document_lifecycle_state == accepted" in conditions


# =============================================================================
# Test: Graph Integrity
# =============================================================================

class TestGraphIntegrity:
    """Tests for workflow graph integrity."""

    def test_all_edge_targets_exist(self, workflow_plan, nodes_by_id):
        """All edge to_node_id values reference existing nodes (or null)."""
        for edge in workflow_plan["edges"]:
            to_node = edge.get("to_node_id")
            if to_node is not None:
                assert to_node in nodes_by_id, \
                    f"Edge {edge['edge_id']} references non-existent node: {to_node}"

    def test_all_edge_sources_exist(self, workflow_plan, nodes_by_id):
        """All edge from_node_id values reference existing nodes."""
        for edge in workflow_plan["edges"]:
            from_node = edge["from_node_id"]
            assert from_node in nodes_by_id, \
                f"Edge {edge['edge_id']} has non-existent source: {from_node}"

    def test_entry_node_exists(self, workflow_plan, nodes_by_id):
        """Entry node exists in nodes list."""
        for entry_id in workflow_plan["entry_node_ids"]:
            assert entry_id in nodes_by_id, \
                f"Entry node {entry_id} not found in nodes"

    def test_all_non_end_nodes_have_outbound_edges(self, workflow_plan, nodes_by_id, edges_by_from):
        """All non-end nodes have at least one outbound edge."""
        for node in workflow_plan["nodes"]:
            if node["type"] != "end":
                assert node["node_id"] in edges_by_from, \
                    f"Node {node['node_id']} has no outbound edges"


# =============================================================================
# Test: ADR References
# =============================================================================

class TestADRReferences:
    """Tests for ADR governance references."""

    REQUIRED_ADRS = ["ADR-025", "ADR-035", "ADR-036", "ADR-037", "ADR-038", "ADR-039"]

    def test_has_governance_adr_references(self, workflow_plan):
        """Workflow has ADR references in governance."""
        assert "governance" in workflow_plan
        assert "adr_references" in workflow_plan["governance"]

    def test_references_all_required_adrs(self, workflow_plan):
        """Workflow references all required ADRs."""
        refs = workflow_plan["governance"]["adr_references"]
        for adr in self.REQUIRED_ADRS:
            assert adr in refs, f"Missing ADR reference: {adr}"

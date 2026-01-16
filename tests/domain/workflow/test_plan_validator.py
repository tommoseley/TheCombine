"""Tests for Document Interaction Workflow Plan validator (ADR-039)."""

import pytest

from app.domain.workflow.plan_validator import (
    PlanValidationErrorCode,
    PlanValidator,
)


@pytest.fixture
def validator():
    """Create a PlanValidator instance."""
    return PlanValidator()


@pytest.fixture
def valid_plan():
    """A minimal valid workflow plan."""
    return {
        "workflow_id": "test_plan",
        "version": "1.0.0",
        "entry_node_ids": ["start"],
        "nodes": [
            {"node_id": "start", "type": "task", "description": "Start task"},
            {"node_id": "end", "type": "end", "description": "End",
             "terminal_outcome": "stabilized"},
        ],
        "edges": [
            {"edge_id": "e1", "from_node_id": "start",
             "to_node_id": "end", "outcome": "success"},
        ],
    }


class TestSchemaValidation:
    """Tests for basic schema validation."""

    def test_valid_plan_passes(self, validator, valid_plan):
        """Valid plan passes validation."""
        result = validator.validate(valid_plan)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_workflow_id(self, validator, valid_plan):
        """Missing workflow_id fails validation."""
        del valid_plan["workflow_id"]
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.MISSING_REQUIRED_FIELD
            for e in result.errors
        )

    def test_missing_nodes(self, validator, valid_plan):
        """Missing nodes array fails validation."""
        del valid_plan["nodes"]
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.MISSING_REQUIRED_FIELD
            and "nodes" in e.message
            for e in result.errors
        )

    def test_missing_edges(self, validator, valid_plan):
        """Missing edges array fails validation."""
        del valid_plan["edges"]
        result = validator.validate(valid_plan)

        assert result.valid is False

    def test_missing_entry_node_ids(self, validator, valid_plan):
        """Missing entry_node_ids fails validation."""
        del valid_plan["entry_node_ids"]
        result = validator.validate(valid_plan)

        assert result.valid is False

    def test_empty_entry_node_ids(self, validator, valid_plan):
        """Empty entry_node_ids fails validation."""
        valid_plan["entry_node_ids"] = []
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            "at least one entry" in e.message
            for e in result.errors
        )

    def test_invalid_node_type(self, validator, valid_plan):
        """Invalid node type fails validation."""
        valid_plan["nodes"][0]["type"] = "invalid_type"
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.INVALID_ENUM_VALUE
            for e in result.errors
        )

    def test_end_node_missing_terminal_outcome(self, validator, valid_plan):
        """End node without terminal_outcome fails validation."""
        valid_plan["nodes"][1] = {
            "node_id": "end",
            "type": "end",
            "description": "End without terminal",
        }
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            "terminal_outcome" in e.message
            for e in result.errors
        )

    def test_edge_missing_required_fields(self, validator, valid_plan):
        """Edge missing required fields fails validation."""
        valid_plan["edges"][0] = {"edge_id": "e1"}
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.MISSING_REQUIRED_FIELD
            for e in result.errors
        )

    def test_invalid_edge_kind(self, validator, valid_plan):
        """Invalid edge kind fails validation."""
        valid_plan["edges"][0]["kind"] = "invalid_kind"
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.INVALID_ENUM_VALUE
            for e in result.errors
        )

    def test_condition_missing_fields(self, validator, valid_plan):
        """Condition missing required fields fails validation."""
        valid_plan["edges"][0]["conditions"] = [{"type": "retry_count"}]
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            "operator" in e.message or "value" in e.message
            for e in result.errors
        )

    def test_invalid_condition_operator(self, validator, valid_plan):
        """Invalid condition operator fails validation."""
        valid_plan["edges"][0]["conditions"] = [
            {"type": "retry_count", "operator": "invalid", "value": 1}
        ]
        result = validator.validate(valid_plan)

        assert result.valid is False


class TestGraphIntegrityValidation:
    """Tests for graph integrity validation."""

    def test_edge_target_not_found(self, validator, valid_plan):
        """Edge referencing non-existent target fails."""
        valid_plan["edges"][0]["to_node_id"] = "nonexistent"
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.EDGE_TARGET_NOT_FOUND
            for e in result.errors
        )

    def test_edge_source_not_found(self, validator, valid_plan):
        """Edge referencing non-existent source fails."""
        valid_plan["edges"][0]["from_node_id"] = "nonexistent"
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.EDGE_SOURCE_NOT_FOUND
            for e in result.errors
        )

    def test_entry_node_not_found(self, validator, valid_plan):
        """Entry node not in nodes fails."""
        valid_plan["entry_node_ids"] = ["nonexistent"]
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.ENTRY_NODE_NOT_FOUND
            for e in result.errors
        )

    def test_non_end_node_without_outbound_edges(self, validator, valid_plan):
        """Non-end node without outbound edges fails."""
        # Add a node with no outbound edge
        valid_plan["nodes"].insert(1, {
            "node_id": "orphan_task",
            "type": "task",
            "description": "Orphan",
        })
        # Add edge TO it but not FROM it
        valid_plan["edges"].append({
            "edge_id": "e2",
            "from_node_id": "start",
            "to_node_id": "orphan_task",
            "outcome": "success",
        })
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.NO_OUTBOUND_EDGES
            and "orphan_task" in e.message
            for e in result.errors
        )

    def test_null_to_node_id_is_valid(self, validator, valid_plan):
        """Null to_node_id (non-advancing edge) is valid."""
        valid_plan["edges"].append({
            "edge_id": "e2",
            "from_node_id": "start",
            "to_node_id": None,
            "outcome": "needs_input",
            "non_advancing": True,
        })
        result = validator.validate(valid_plan)

        assert result.valid is True

    def test_orphan_node_warning(self, validator, valid_plan):
        """Unreachable node generates warning."""
        # Add an orphan node
        valid_plan["nodes"].append({
            "node_id": "orphan",
            "type": "end",
            "description": "Orphan end",
            "terminal_outcome": "abandoned",
        })
        result = validator.validate(valid_plan)

        # Should be valid but with warning
        assert result.valid is True
        assert any(
            e.code == PlanValidationErrorCode.ORPHAN_NODE
            for e in result.warnings
        )


class TestOutcomeMappingValidation:
    """Tests for outcome mapping validation."""

    def test_missing_outcome_mapping_with_gates(self, validator, valid_plan):
        """Plan with gates but no outcome_mapping fails."""
        valid_plan["nodes"][0] = {
            "node_id": "start",
            "type": "gate",
            "description": "Gate",
            "gate_outcomes": ["qualified", "not_ready"],
        }
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.MISSING_OUTCOME_MAPPING
            for e in result.errors
        )

    def test_incomplete_outcome_mapping(self, validator, valid_plan):
        """Outcome mapping missing some gate outcomes fails."""
        valid_plan["nodes"][0] = {
            "node_id": "start",
            "type": "gate",
            "description": "Gate",
            "gate_outcomes": ["qualified", "not_ready"],
        }
        valid_plan["outcome_mapping"] = {
            "mappings": [
                {"gate_outcome": "qualified", "terminal_outcome": "stabilized"},
                # Missing: not_ready
            ]
        }
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.INCOMPLETE_OUTCOME_MAPPING
            for e in result.errors
        )

    def test_complete_outcome_mapping(self, validator, valid_plan):
        """Complete outcome mapping passes."""
        valid_plan["nodes"][0] = {
            "node_id": "start",
            "type": "gate",
            "description": "Gate",
            "gate_outcomes": ["qualified", "not_ready"],
        }
        valid_plan["outcome_mapping"] = {
            "mappings": [
                {"gate_outcome": "qualified", "terminal_outcome": "stabilized"},
                {"gate_outcome": "not_ready", "terminal_outcome": "blocked"},
            ]
        }
        result = validator.validate(valid_plan)

        assert result.valid is True


class TestGovernanceValidation:
    """Tests for governance validation."""

    def test_circuit_breaker_missing_max_retries(self, validator, valid_plan):
        """Circuit breaker without max_retries fails."""
        valid_plan["governance"] = {
            "circuit_breaker": {
                "applies_to": ["qa"],
            }
        }
        result = validator.validate(valid_plan)

        assert result.valid is False
        assert any(
            e.code == PlanValidationErrorCode.INVALID_CIRCUIT_BREAKER
            for e in result.errors
        )

    def test_circuit_breaker_invalid_max_retries(self, validator, valid_plan):
        """Circuit breaker with invalid max_retries fails."""
        valid_plan["governance"] = {
            "circuit_breaker": {
                "max_retries": "two",  # Should be int
            }
        }
        result = validator.validate(valid_plan)

        assert result.valid is False

    def test_circuit_breaker_zero_retries(self, validator, valid_plan):
        """Circuit breaker with zero max_retries fails."""
        valid_plan["governance"] = {
            "circuit_breaker": {
                "max_retries": 0,
            }
        }
        result = validator.validate(valid_plan)

        assert result.valid is False

    def test_valid_governance(self, validator, valid_plan):
        """Valid governance section passes."""
        valid_plan["governance"] = {
            "adr_references": ["ADR-025", "ADR-037"],
            "circuit_breaker": {
                "max_retries": 2,
                "applies_to": ["qa"],
            },
            "staleness_handling": {
                "auto_reentry": False,
            },
        }
        result = validator.validate(valid_plan)

        assert result.valid is True


class TestConciergeIntakePlanValidation:
    """Integration tests using the actual concierge_intake plan structure."""

    @pytest.fixture
    def concierge_intake_plan(self):
        """Structure matching concierge_intake.v1.json."""
        return {
            "workflow_id": "concierge_intake",
            "version": "1.0.0",
            "scope_type": "document",
            "document_type": "concierge_intake",
            "entry_node_ids": ["clarification"],
            "nodes": [
                {"node_id": "clarification", "type": "concierge",
                 "description": "Clarification"},
                {"node_id": "consent_gate", "type": "gate",
                 "description": "Consent", "requires_consent": True},
                {"node_id": "generation", "type": "task",
                 "description": "Generation", "produces": "concierge_intake_document"},
                {"node_id": "qa", "type": "qa",
                 "description": "QA", "requires_qa": True},
                {"node_id": "remediation", "type": "task",
                 "description": "Remediation"},
                {"node_id": "outcome_gate", "type": "gate",
                 "description": "Outcome",
                 "gate_outcomes": ["qualified", "not_ready", "out_of_scope", "redirect"]},
                {"node_id": "end_stabilized", "type": "end",
                 "description": "Stabilized", "terminal_outcome": "stabilized"},
                {"node_id": "end_blocked", "type": "end",
                 "description": "Blocked", "terminal_outcome": "blocked"},
                {"node_id": "end_abandoned", "type": "end",
                 "description": "Abandoned", "terminal_outcome": "abandoned"},
            ],
            "edges": [
                {"edge_id": "e1", "from_node_id": "clarification",
                 "to_node_id": "consent_gate", "outcome": "success"},
                {"edge_id": "e2", "from_node_id": "clarification",
                 "to_node_id": None, "outcome": "needs_user_input", "non_advancing": True},
                {"edge_id": "e3", "from_node_id": "clarification",
                 "to_node_id": "end_abandoned", "outcome": "out_of_scope"},
                {"edge_id": "e4", "from_node_id": "consent_gate",
                 "to_node_id": "generation", "outcome": "success"},
                {"edge_id": "e5", "from_node_id": "consent_gate",
                 "to_node_id": "end_blocked", "outcome": "blocked"},
                {"edge_id": "e6", "from_node_id": "generation",
                 "to_node_id": "qa", "outcome": "success"},
                {"edge_id": "e7", "from_node_id": "qa",
                 "to_node_id": "outcome_gate", "outcome": "success"},
                {"edge_id": "e8", "from_node_id": "qa",
                 "to_node_id": "remediation", "outcome": "failed",
                 "conditions": [{"type": "retry_count", "operator": "lt", "value": 2}]},
                {"edge_id": "e9", "from_node_id": "qa",
                 "to_node_id": "end_blocked", "outcome": "failed",
                 "conditions": [{"type": "retry_count", "operator": "gte", "value": 2}]},
                {"edge_id": "e10", "from_node_id": "remediation",
                 "to_node_id": "qa", "outcome": "success"},
                {"edge_id": "e11", "from_node_id": "outcome_gate",
                 "to_node_id": "end_stabilized", "outcome": "qualified"},
                {"edge_id": "e12", "from_node_id": "outcome_gate",
                 "to_node_id": "end_blocked", "outcome": "not_ready"},
                {"edge_id": "e13", "from_node_id": "outcome_gate",
                 "to_node_id": "end_abandoned", "outcome": "out_of_scope"},
                {"edge_id": "e14", "from_node_id": "outcome_gate",
                 "to_node_id": "end_abandoned", "outcome": "redirect"},
            ],
            "outcome_mapping": {
                "mappings": [
                    {"gate_outcome": "qualified", "terminal_outcome": "stabilized"},
                    {"gate_outcome": "not_ready", "terminal_outcome": "blocked"},
                    {"gate_outcome": "out_of_scope", "terminal_outcome": "abandoned"},
                    {"gate_outcome": "redirect", "terminal_outcome": "abandoned"},
                ]
            },
            "governance": {
                "circuit_breaker": {"max_retries": 2},
                "staleness_handling": {"auto_reentry": False},
            },
        }

    def test_concierge_intake_structure_valid(self, validator, concierge_intake_plan):
        """Concierge intake plan structure validates successfully."""
        result = validator.validate(concierge_intake_plan)

        assert result.valid is True
        assert len(result.errors) == 0

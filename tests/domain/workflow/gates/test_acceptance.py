"""Tests for acceptance gate."""

import pytest

from app.domain.workflow.gates.acceptance import AcceptanceGate
from app.domain.workflow.workflow_state import AcceptanceDecision
from app.domain.workflow.models import Workflow, ScopeConfig, DocumentTypeConfig


@pytest.fixture
def workflow():
    """Create a test workflow with acceptance requirements."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test",
        revision="1",
        effective_date="2026-01-01",
        name="Test",
        description="",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "project_discovery": DocumentTypeConfig(
                name="Discovery",
                scope="project",
                acceptance_required=True,
                accepted_by=["PM", "Stakeholder"],
            ),
            "internal_notes": DocumentTypeConfig(
                name="Notes",
                scope="project",
                acceptance_required=False,
            ),
            "auto_accepted": DocumentTypeConfig(
                name="Auto",
                scope="project",
                acceptance_required=True,
                # No accepted_by means anyone can accept
            ),
        },
        entity_types={},
        steps=[],
    )


class TestAcceptanceGate:
    """Tests for AcceptanceGate."""
    
    def test_requires_acceptance_true(self, workflow):
        gate = AcceptanceGate(workflow)
        assert gate.requires_acceptance("project_discovery") is True
    
    def test_requires_acceptance_false(self, workflow):
        gate = AcceptanceGate(workflow)
        assert gate.requires_acceptance("internal_notes") is False
    
    def test_requires_acceptance_unknown_doc(self, workflow):
        gate = AcceptanceGate(workflow)
        assert gate.requires_acceptance("unknown") is False
    
    def test_get_acceptors(self, workflow):
        gate = AcceptanceGate(workflow)
        acceptors = gate.get_acceptors("project_discovery")
        assert acceptors == ["PM", "Stakeholder"]
    
    def test_get_acceptors_empty(self, workflow):
        gate = AcceptanceGate(workflow)
        acceptors = gate.get_acceptors("auto_accepted")
        assert acceptors == []
    
    def test_can_accept_with_role(self, workflow):
        gate = AcceptanceGate(workflow)
        assert gate.can_accept("project_discovery", "PM") is True
        assert gate.can_accept("project_discovery", "Developer") is False
    
    def test_can_accept_anyone_when_no_acceptors(self, workflow):
        gate = AcceptanceGate(workflow)
        assert gate.can_accept("auto_accepted", "Anyone") is True
    
    def test_record_decision(self, workflow):
        gate = AcceptanceGate(workflow)
        decision = gate.record_decision(
            doc_type="project_discovery",
            scope_id=None,
            accepted=True,
            decided_by="user_pm",
            comment="Approved",
        )
        assert decision.doc_type == "project_discovery"
        assert decision.accepted is True
        assert decision.decided_by == "user_pm"
        assert decision.decided_at is not None
    
    def test_make_decision_key(self, workflow):
        gate = AcceptanceGate(workflow)
        key1 = gate.make_decision_key("doc", None)
        key2 = gate.make_decision_key("doc", "scope_1")
        assert key1 == "doc:root"
        assert key2 == "doc:scope_1"
    
    def test_can_proceed_when_accepted(self, workflow):
        gate = AcceptanceGate(workflow)
        decisions = {
            "project_discovery:root": AcceptanceDecision(
                doc_type="project_discovery",
                scope_id=None,
                accepted=True,
                comment=None,
                decided_by="pm",
            )
        }
        assert gate.can_proceed("project_discovery", None, decisions) is True
    
    def test_cannot_proceed_when_rejected(self, workflow):
        gate = AcceptanceGate(workflow)
        decisions = {
            "project_discovery:root": AcceptanceDecision(
                doc_type="project_discovery",
                scope_id=None,
                accepted=False,
                comment="Not ready",
                decided_by="pm",
            )
        }
        assert gate.can_proceed("project_discovery", None, decisions) is False
    
    def test_cannot_proceed_when_pending(self, workflow):
        gate = AcceptanceGate(workflow)
        decisions = {}  # No decision recorded
        assert gate.can_proceed("project_discovery", None, decisions) is False
    
    def test_can_proceed_no_acceptance_required(self, workflow):
        gate = AcceptanceGate(workflow)
        decisions = {}
        assert gate.can_proceed("internal_notes", None, decisions) is True
    
    def test_is_rejected(self, workflow):
        gate = AcceptanceGate(workflow)
        decisions = {
            "project_discovery:root": AcceptanceDecision(
                doc_type="project_discovery",
                scope_id=None,
                accepted=False,
                comment=None,
                decided_by="pm",
            )
        }
        assert gate.is_rejected("project_discovery", None, decisions) is True
    
    def test_is_pending(self, workflow):
        gate = AcceptanceGate(workflow)
        decisions = {}
        assert gate.is_pending("project_discovery", None, decisions) is True
        assert gate.is_pending("internal_notes", None, decisions) is False

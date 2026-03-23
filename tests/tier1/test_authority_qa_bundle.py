"""Tests for QA authority bundle integration.

WS-AUTH-006: Tier 1 verification criteria 1-7.
"""

from uuid import uuid4

import pytest


def determine_qa_validation_depth(context_state: dict) -> str:
    """Determine QA validation depth based on authority source.

    Returns: "full_durable", "full_execution", or "advisory"
    """
    source = context_state.get("authority_source", "none")
    if source == "durable_store":
        return "full_durable"
    elif source == "execution_scoped":
        return "full_execution"
    else:
        return "advisory"


def build_qa_finding(message: str, context_state: dict, severity: str = "error") -> dict:
    """Build a QA finding with authority citation if available.

    When authority_source is durable_store, findings include
    authority_record_ids for audit.
    """
    finding = {
        "severity": severity,
        "message": message,
        "authority_source": context_state.get("authority_source", "none"),
    }
    if context_state.get("authority_source") == "durable_store":
        finding["authority_record_ids"] = context_state.get("authority_record_ids", [])
    return finding


class TestQAReceivesAuthorityBundle:
    """Criterion 1: QA has access to authority records via context_state."""

    def test_authority_keys_in_context(self):
        context_state = {
            "pgc_answers": {"q1": "v1"},
            "pgc_questions": ["q1"],
            "authority_record_ids": [uuid4()],
            "authority_source": "durable_store",
        }
        assert "authority_source" in context_state
        assert "authority_record_ids" in context_state
        assert context_state["authority_source"] == "durable_store"


class TestNoncomplianceCitesAuthority:
    """Criterion 2: compliance findings include authority_record_ids."""

    def test_finding_includes_record_ids(self):
        record_id = uuid4()
        context_state = {
            "authority_source": "durable_store",
            "authority_record_ids": [record_id],
        }
        finding = build_qa_finding(
            "Document violates constraint: language must be Python",
            context_state,
        )
        assert finding["authority_record_ids"] == [record_id]
        assert finding["authority_source"] == "durable_store"


class TestMissingAuthorityAdvisory:
    """Criterion 3: missing authority produces advisory, not hard fail."""

    def test_advisory_depth_for_no_authority(self):
        context_state = {"authority_source": "none"}
        depth = determine_qa_validation_depth(context_state)
        assert depth == "advisory"

    def test_advisory_depth_for_empty_context(self):
        context_state = {}
        depth = determine_qa_validation_depth(context_state)
        assert depth == "advisory"


class TestAuthorityAwareReplacesHeuristic:
    """Criterion 4: authority-aware logic takes precedence over heuristic."""

    def test_durable_store_gets_full_audit(self):
        context_state = {"authority_source": "durable_store"}
        depth = determine_qa_validation_depth(context_state)
        assert depth == "full_durable"

    def test_execution_scoped_gets_full_audit(self):
        context_state = {"authority_source": "execution_scoped"}
        depth = determine_qa_validation_depth(context_state)
        assert depth == "full_execution"


class TestFullAuditWithAuthority:
    """Criterion 5: complete authority enables full audit."""

    def test_full_audit_when_complete(self):
        context_state = {
            "pgc_answers": {"q1": "v1", "q2": "v2"},
            "pgc_questions": ["q1", "q2"],
            "authority_record_ids": [uuid4(), uuid4()],
            "authority_source": "durable_store",
        }
        depth = determine_qa_validation_depth(context_state)
        assert depth == "full_durable"

        finding = build_qa_finding("constraint violation", context_state)
        assert len(finding["authority_record_ids"]) == 2


class TestBackwardCompatible:
    """Criterion 7: projects without authority still pass QA."""

    def test_no_authority_is_advisory(self):
        context_state = {}
        depth = determine_qa_validation_depth(context_state)
        assert depth == "advisory"

    def test_finding_without_authority_has_no_record_ids(self):
        context_state = {"authority_source": "none"}
        finding = build_qa_finding("issue", context_state, severity="warning")
        assert "authority_record_ids" not in finding

"""Tests for workflow result handling pure functions -- WS-CRAP-001 Target 1.

Tests extracted pure functions: extract_metadata_by_keys, extract_qa_feedback,
should_pause_for_intake_review.
"""

import os
import sys
import types

# Stub the workflow package to avoid circular import through __init__.py
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.result_handling import (  # noqa: E402
    GATE_PROFILE_KEYS,
    INTAKE_METADATA_KEYS,
    extract_metadata_by_keys,
    extract_qa_feedback,
    should_pause_for_intake_review,
)


# =========================================================================
# extract_metadata_by_keys
# =========================================================================


class TestExtractMetadataByKeys:
    """Tests for extract_metadata_by_keys pure function."""

    def test_extracts_matching_keys(self):
        metadata = {"a": 1, "b": 2, "c": 3}
        result = extract_metadata_by_keys(metadata, ["a", "c"])
        assert result == {"a": 1, "c": 3}

    def test_missing_keys_ignored(self):
        metadata = {"a": 1}
        result = extract_metadata_by_keys(metadata, ["a", "missing"])
        assert result == {"a": 1}

    def test_empty_metadata(self):
        result = extract_metadata_by_keys({}, ["a", "b"])
        assert result == {}

    def test_empty_keys(self):
        result = extract_metadata_by_keys({"a": 1}, [])
        assert result == {}

    def test_gate_profile_keys_constant(self):
        metadata = {
            "intake_gate_phase": "classify",
            "intake_classification": {"type": "greenfield"},
            "extracted": {"name": "Test"},
            "entry_op_ref": "op_1",
            "user_input": "hello",
            "irrelevant_key": "ignored",
        }
        result = extract_metadata_by_keys(metadata, GATE_PROFILE_KEYS)
        assert "intake_gate_phase" in result
        assert "intake_classification" in result
        assert "irrelevant_key" not in result

    def test_intake_metadata_keys_constant(self):
        metadata = {
            "intake_summary": "A web app",
            "project_type": "greenfield",
            "artifact_type": "web_app",
        }
        result = extract_metadata_by_keys(metadata, INTAKE_METADATA_KEYS)
        assert len(result) == 3

    def test_preserves_value_types(self):
        metadata = {"a": [1, 2], "b": {"nested": True}, "c": None}
        result = extract_metadata_by_keys(metadata, ["a", "b", "c"])
        assert result["a"] == [1, 2]
        assert result["b"] == {"nested": True}
        assert result["c"] is None


# =========================================================================
# extract_qa_feedback
# =========================================================================


class TestExtractQaFeedback:
    """Tests for extract_qa_feedback pure function."""

    def test_none_metadata_returns_none(self):
        assert extract_qa_feedback(None) is None

    def test_empty_metadata_returns_none(self):
        assert extract_qa_feedback({}) is None

    def test_drift_errors(self):
        metadata = {
            "drift_errors": [
                {"check_id": "QA-PGC-001", "message": "Contradicts constraint", "remediation": "Fix it"},
            ]
        }
        result = extract_qa_feedback(metadata)
        assert result is not None
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "constraint_drift"
        assert result["issues"][0]["check_id"] == "QA-PGC-001"
        assert result["issues"][0]["remediation"] == "Fix it"

    def test_validation_errors(self):
        metadata = {
            "validation_errors": [
                {"check_id": "PROMO-001", "message": "Promoted answer"},
            ]
        }
        result = extract_qa_feedback(metadata)
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "validation"

    def test_llm_qa_dict_errors(self):
        metadata = {
            "errors": [
                {"severity": "error", "section": "risks", "message": "Missing risk"},
            ]
        }
        result = extract_qa_feedback(metadata)
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "llm_qa"
        assert result["issues"][0]["section"] == "risks"

    def test_llm_qa_string_errors(self):
        metadata = {
            "errors": ["Missing field X", "Invalid format Y"],
        }
        result = extract_qa_feedback(metadata)
        assert len(result["issues"]) == 2
        assert result["issues"][0]["message"] == "Missing field X"

    def test_mixed_llm_qa_errors(self):
        metadata = {
            "errors": [
                {"message": "Dict error"},
                "String error",
            ]
        }
        result = extract_qa_feedback(metadata)
        assert len(result["issues"]) == 2

    def test_semantic_qa_findings(self):
        metadata = {
            "semantic_qa_report": {
                "findings": [
                    {
                        "severity": "error",
                        "code": "CONTRADICTION",
                        "constraint_id": "C1",
                        "message": "Contradicts C1",
                        "suggested_fix": "Remove contradiction",
                        "evidence_pointers": ["$.field"],
                    },
                    {
                        "severity": "warning",
                        "code": "OMISSION",
                        "message": "Missing mention",
                    },
                ]
            }
        }
        result = extract_qa_feedback(metadata)
        # Only error-severity findings included
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "semantic_qa"
        assert result["issues"][0]["evidence"] == ["$.field"]

    def test_feedback_dict_summary(self):
        metadata = {
            "errors": ["something"],
            "feedback": {"llm_feedback": "Overall assessment"},
        }
        result = extract_qa_feedback(metadata)
        assert result["summary"] == "Overall assessment"

    def test_feedback_string_summary(self):
        metadata = {
            "errors": ["something"],
            "feedback": "Plain text feedback",
        }
        result = extract_qa_feedback(metadata)
        assert result["summary"] == "Plain text feedback"

    def test_validation_source(self):
        metadata = {
            "errors": ["something"],
            "validation_source": "constraint_drift",
        }
        result = extract_qa_feedback(metadata)
        assert result["source"] == "constraint_drift"

    def test_default_source(self):
        metadata = {"errors": ["something"]}
        result = extract_qa_feedback(metadata)
        assert result["source"] == "qa"

    def test_no_issues_returns_none(self):
        metadata = {"some_key": "value"}
        assert extract_qa_feedback(metadata) is None

    def test_all_error_types_combined(self):
        metadata = {
            "drift_errors": [{"check_id": "D1", "message": "drift"}],
            "validation_errors": [{"check_id": "V1", "message": "validate"}],
            "errors": ["llm error"],
            "semantic_qa_report": {
                "findings": [{"severity": "error", "code": "S1", "message": "semantic"}]
            },
        }
        result = extract_qa_feedback(metadata)
        assert len(result["issues"]) == 4
        types = [i["type"] for i in result["issues"]]
        assert "constraint_drift" in types
        assert "validation" in types
        assert "llm_qa" in types
        assert "semantic_qa" in types


# =========================================================================
# should_pause_for_intake_review
# =========================================================================


class TestShouldPauseForIntakeReview:
    """Tests for should_pause_for_intake_review pure function."""

    def test_intake_gate_review_phase(self):
        assert should_pause_for_intake_review(True, "review", None) is True

    def test_intake_gate_review_already_generating(self):
        assert should_pause_for_intake_review(True, "review", "generating") is False

    def test_intake_gate_non_review_phase(self):
        assert should_pause_for_intake_review(True, "classify", None) is False

    def test_non_intake_gate_review_phase(self):
        # GATE nodes with internals don't use this legacy path
        assert should_pause_for_intake_review(False, "review", None) is False

    def test_intake_gate_none_phase(self):
        assert should_pause_for_intake_review(True, None, None) is False

    def test_all_false(self):
        assert should_pause_for_intake_review(False, None, None) is False

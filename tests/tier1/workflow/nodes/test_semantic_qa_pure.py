"""Tests for semantic_qa_pure functions.

Extracted from qa._run_semantic_qa() per WS-CRAP-007.
Tier-1: in-memory, no DB, no LLM.
"""

import os
import sys
import types

# Stub the workflow package to avoid circular import through __init__.py
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.semantic_qa_pure import (  # noqa: E402
    build_error_report,
    build_semantic_qa_prompt,
    extract_semantic_qa_inputs,
)


# ---------------------------------------------------------------------------
# extract_semantic_qa_inputs
# ---------------------------------------------------------------------------


class TestExtractSemanticQaInputs:
    """Tests for extract_semantic_qa_inputs."""

    def test_empty_context(self):
        invariants, questions, answers = extract_semantic_qa_inputs({})
        assert invariants == []
        assert questions == []
        assert answers == {}

    def test_extracts_invariants(self):
        ctx = {"pgc_invariants": [{"id": "PLATFORM", "binding": True}]}
        invariants, _, _ = extract_semantic_qa_inputs(ctx)
        assert len(invariants) == 1
        assert invariants[0]["id"] == "PLATFORM"

    def test_extracts_pgc_questions_list(self):
        ctx = {
            "pgc_invariants": [],
            "pgc_questions": [{"id": "Q1", "text": "What?"}],
        }
        _, questions, _ = extract_semantic_qa_inputs(ctx)
        assert len(questions) == 1
        assert questions[0]["id"] == "Q1"

    def test_extracts_pgc_questions_from_dict_wrapper(self):
        ctx = {
            "pgc_invariants": [],
            "pgc_questions": {
                "questions": [{"id": "Q1", "text": "What?"}],
                "schema_version": "pgc_questions.v1",
            },
        }
        _, questions, _ = extract_semantic_qa_inputs(ctx)
        assert len(questions) == 1
        assert questions[0]["id"] == "Q1"

    def test_extracts_pgc_answers(self):
        ctx = {
            "pgc_invariants": [],
            "pgc_answers": {"Q1": "web"},
        }
        _, _, answers = extract_semantic_qa_inputs(ctx)
        assert answers == {"Q1": "web"}

    def test_missing_keys_default_gracefully(self):
        ctx = {"some_other_key": "value"}
        invariants, questions, answers = extract_semantic_qa_inputs(ctx)
        assert invariants == []
        assert questions == []
        assert answers == {}


# ---------------------------------------------------------------------------
# build_semantic_qa_prompt
# ---------------------------------------------------------------------------


class TestBuildSemanticQaPrompt:
    """Tests for build_semantic_qa_prompt."""

    def test_includes_policy_prompt(self):
        result = build_semantic_qa_prompt(
            pgc_questions=[], pgc_answers={}, invariants=[],
            document={}, correlation_id="", policy_prompt="# Policy here",
        )
        assert result.startswith("# Policy here")

    def test_includes_questions_section(self):
        questions = [{"id": "Q1", "priority": "must"}]
        answers = {"Q1": "web"}
        result = build_semantic_qa_prompt(
            pgc_questions=questions, pgc_answers=answers, invariants=[],
            document={}, correlation_id="", policy_prompt="P",
        )
        assert "## PGC Questions and Answers" in result
        assert "Q1 (priority=must): web" in result

    def test_dict_answer_uses_label(self):
        questions = [{"id": "Q1", "priority": "should"}]
        answers = {"Q1": {"label": "Mobile App", "value": "mobile"}}
        result = build_semantic_qa_prompt(
            pgc_questions=questions, pgc_answers=answers, invariants=[],
            document={}, correlation_id="", policy_prompt="P",
        )
        assert "Mobile App" in result

    def test_includes_constraints_section(self):
        invariants = [
            {"id": "PLATFORM", "invariant_kind": "requirement", "normalized_text": "Must be web"},
        ]
        result = build_semantic_qa_prompt(
            pgc_questions=[], pgc_answers={}, invariants=invariants,
            document={}, correlation_id="", policy_prompt="P",
        )
        assert "## Bound Constraints" in result
        assert "PLATFORM [requirement]: Must be web" in result

    def test_constraint_text_fallback_chain(self):
        # Falls back: normalized_text -> user_answer_label -> user_answer
        inv1 = {"id": "A", "user_answer_label": "Label"}
        inv2 = {"id": "B", "user_answer": "Raw answer"}
        result = build_semantic_qa_prompt(
            pgc_questions=[], pgc_answers={},
            invariants=[inv1, inv2],
            document={}, correlation_id="", policy_prompt="P",
        )
        assert "Label" in result
        assert "Raw answer" in result

    def test_includes_document_json(self):
        doc = {"title": "Test Document"}
        result = build_semantic_qa_prompt(
            pgc_questions=[], pgc_answers={}, invariants=[],
            document=doc, correlation_id="", policy_prompt="P",
        )
        assert "## Generated Document" in result
        assert '"title": "Test Document"' in result

    def test_includes_correlation_id(self):
        result = build_semantic_qa_prompt(
            pgc_questions=[], pgc_answers={}, invariants=[],
            document={}, correlation_id="exec-123", policy_prompt="P",
        )
        assert "correlation_id for output: exec-123" in result

    def test_includes_output_instruction(self):
        result = build_semantic_qa_prompt(
            pgc_questions=[], pgc_answers={}, invariants=[],
            document={}, correlation_id="", policy_prompt="P",
        )
        assert "qa_semantic_compliance_output.v1" in result

    def test_question_default_priority(self):
        questions = [{"id": "Q1"}]  # no priority key
        result = build_semantic_qa_prompt(
            pgc_questions=questions, pgc_answers={}, invariants=[],
            document={}, correlation_id="", policy_prompt="P",
        )
        assert "Q1 (priority=could):" in result

    def test_none_answer_shows_empty(self):
        questions = [{"id": "Q1"}]
        result = build_semantic_qa_prompt(
            pgc_questions=questions, pgc_answers={}, invariants=[],
            document={}, correlation_id="", policy_prompt="P",
        )
        # No answer -> empty label
        assert "Q1 (priority=could): \n" in result


# ---------------------------------------------------------------------------
# build_error_report
# ---------------------------------------------------------------------------


class TestBuildErrorReport:
    """Tests for build_error_report."""

    def test_schema_version(self):
        report = build_error_report("cid", 3, ValueError("boom"))
        assert report["schema_version"] == "qa_semantic_compliance_output.v1"

    def test_correlation_id(self):
        report = build_error_report("exec-42", 3, ValueError("boom"))
        assert report["correlation_id"] == "exec-42"

    def test_gate_fail(self):
        report = build_error_report("", 3, ValueError("boom"))
        assert report["gate"] == "fail"

    def test_summary_counts(self):
        report = build_error_report("", 5, ValueError("boom"))
        assert report["summary"]["errors"] == 1
        assert report["summary"]["warnings"] == 0
        assert report["summary"]["expected_constraints"] == 5
        assert report["summary"]["evaluated_constraints"] == 0

    def test_blocked_reasons(self):
        report = build_error_report("", 2, RuntimeError("timeout"))
        assert len(report["summary"]["blocked_reasons"]) == 1
        assert "timeout" in report["summary"]["blocked_reasons"][0]

    def test_coverage(self):
        report = build_error_report("", 4, ValueError("x"))
        assert report["coverage"]["expected_count"] == 4
        assert report["coverage"]["evaluated_count"] == 0
        assert report["coverage"]["items"] == []

    def test_findings(self):
        report = build_error_report("", 1, ValueError("bad input"))
        assert len(report["findings"]) == 1
        f = report["findings"][0]
        assert f["severity"] == "error"
        assert f["code"] == "OTHER"
        assert f["constraint_id"] == "SYSTEM"
        assert "bad input" in f["message"]

    def test_zero_invariants(self):
        report = build_error_report("", 0, ValueError("x"))
        assert report["summary"]["expected_constraints"] == 0
        assert report["coverage"]["expected_count"] == 0

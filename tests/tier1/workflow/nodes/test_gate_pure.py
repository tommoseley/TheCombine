"""Tests for gate_pure functions.

Extracted from gate._execute_pgc_gate() per WS-CRAP-007.
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

from app.domain.workflow.nodes.gate_pure import (  # noqa: E402
    build_pgc_task_config,
    determine_pgc_phase,
    merge_questions_with_answers,
)


# ---------------------------------------------------------------------------
# determine_pgc_phase
# ---------------------------------------------------------------------------


class TestDeterminePgcPhase:
    """Tests for determine_pgc_phase."""

    def test_both_present_is_merge(self):
        assert determine_pgc_phase({"questions": []}, {"Q1": "A"}) == "merge"

    def test_questions_only_is_entry(self):
        assert determine_pgc_phase({"questions": []}, None) == "entry"

    def test_questions_with_empty_answers_is_entry(self):
        # Empty dict is falsy, so this should be entry
        assert determine_pgc_phase({"questions": []}, {}) == "entry"

    def test_neither_is_pass_a(self):
        assert determine_pgc_phase(None, None) == "pass_a"

    def test_none_questions_is_pass_a(self):
        assert determine_pgc_phase(None, {"Q1": "A"}) == "pass_a"

    def test_empty_questions_dict_is_pass_a(self):
        # Empty dict is falsy
        assert determine_pgc_phase({}, None) == "pass_a"


# ---------------------------------------------------------------------------
# merge_questions_with_answers
# ---------------------------------------------------------------------------


class TestMergeQuestionsWithAnswers:
    """Tests for merge_questions_with_answers."""

    def test_empty_questions(self):
        merged, doc = merge_questions_with_answers({"questions": []}, {})
        assert merged == []
        assert doc["schema_version"] == "pgc_clarifications.v1"
        assert doc["question_count"] == 0
        assert doc["answered_count"] == 0

    def test_single_question_with_answer(self):
        questions = {
            "questions": [
                {
                    "id": "Q1",
                    "text": "What platform?",
                    "priority": "must",
                    "why_it_matters": "Drives architecture",
                }
            ]
        }
        answers = {"Q1": "Web application"}
        merged, doc = merge_questions_with_answers(questions, answers)

        assert len(merged) == 1
        assert merged[0]["id"] == "Q1"
        assert merged[0]["question"] == "What platform?"
        assert merged[0]["answer"] == "Web application"
        assert merged[0]["priority"] == "must"
        assert merged[0]["why_it_matters"] == "Drives architecture"
        assert doc["question_count"] == 1
        assert doc["answered_count"] == 1

    def test_unanswered_question(self):
        questions = {"questions": [{"id": "Q1", "text": "What?"}]}
        answers = {}
        merged, doc = merge_questions_with_answers(questions, answers)

        assert merged[0]["answer"] == ""
        assert doc["answered_count"] == 0

    def test_multiple_questions_mixed_answers(self):
        questions = {
            "questions": [
                {"id": "Q1", "text": "Platform?"},
                {"id": "Q2", "text": "Users?"},
                {"id": "Q3", "text": "Budget?"},
            ]
        }
        answers = {"Q1": "Web", "Q3": "High"}
        merged, doc = merge_questions_with_answers(questions, answers)

        assert len(merged) == 3
        assert doc["question_count"] == 3
        assert doc["answered_count"] == 2
        assert merged[0]["answer"] == "Web"
        assert merged[1]["answer"] == ""
        assert merged[2]["answer"] == "High"

    def test_default_priority(self):
        questions = {"questions": [{"id": "Q1", "text": "Q"}]}
        merged, _ = merge_questions_with_answers(questions, {})
        assert merged[0]["priority"] == "should"

    def test_question_field_fallback(self):
        # If "text" is missing, falls back to "question"
        questions = {"questions": [{"id": "Q1", "question": "Fallback Q"}]}
        merged, _ = merge_questions_with_answers(questions, {})
        assert merged[0]["question"] == "Fallback Q"

    def test_missing_id_defaults_to_empty(self):
        questions = {"questions": [{"text": "No ID question"}]}
        merged, _ = merge_questions_with_answers(questions, {})
        assert merged[0]["id"] == ""

    def test_schema_version(self):
        _, doc = merge_questions_with_answers({"questions": []}, {})
        assert doc["schema_version"] == "pgc_clarifications.v1"

    def test_no_questions_key(self):
        # If "questions" key is missing, treats as empty list
        merged, doc = merge_questions_with_answers({}, {"Q1": "A"})
        assert merged == []
        assert doc["question_count"] == 0


# ---------------------------------------------------------------------------
# build_pgc_task_config
# ---------------------------------------------------------------------------


class TestBuildPgcTaskConfig:
    """Tests for build_pgc_task_config."""

    def test_basic_config(self):
        pass_a = {
            "template_ref": "prompt:template:pgc_clarifier:1.0.0",
            "includes": {},
        }
        result = build_pgc_task_config(
            pass_a, "pgc_clarifications",
            resolve_urn_fn=lambda x: f"resolved:{x}",
        )
        assert result["type"] == "pgc"
        assert result["task_ref"] == "resolved:prompt:template:pgc_clarifier:1.0.0"
        assert result["produces"] == "pgc_clarifications"
        assert result["includes"] == {}

    def test_includes_resolved(self):
        pass_a = {
            "template_ref": "urn:task",
            "includes": {
                "ROLE": "urn:role:ba:1.0.0",
                "CONTEXT": "urn:context:project:1.0.0",
            },
        }
        result = build_pgc_task_config(
            pass_a, "out",
            resolve_urn_fn=lambda x: x.replace("urn:", "path/"),
        )
        assert result["includes"]["ROLE"] == "path/role:ba:1.0.0"
        assert result["includes"]["CONTEXT"] == "path/context:project:1.0.0"

    def test_output_schema_ref(self):
        pass_a = {
            "template_ref": "urn:task",
            "includes": {},
            "output_schema_ref": "schema:pgc_output:1.0.0",
        }
        result = build_pgc_task_config(
            pass_a, "out",
            resolve_urn_fn=lambda x: f"resolved:{x}",
        )
        assert result["includes"]["OUTPUT_SCHEMA"] == "resolved:schema:pgc_output:1.0.0"

    def test_no_output_schema_ref(self):
        pass_a = {
            "template_ref": "urn:task",
            "includes": {},
        }
        result = build_pgc_task_config(
            pass_a, "out",
            resolve_urn_fn=lambda x: x,
        )
        assert "OUTPUT_SCHEMA" not in result["includes"]

    def test_empty_pass_a(self):
        result = build_pgc_task_config(
            {}, "out",
            resolve_urn_fn=lambda x: x,
        )
        assert result["task_ref"] == ""
        assert result["includes"] == {}
        assert result["type"] == "pgc"

"""Tests for PGC pure functions -- WS-CRAP-002.

Tests extracted pure functions: resolve_answer_label, build_pgc_from_answers,
build_pgc_from_context_state, build_resolution_dict.
"""

from app.api.v1.services.pgc_pure import (
    resolve_answer_label,
    build_pgc_from_answers,
    build_pgc_from_context_state,
    build_resolution_dict,
)


# =========================================================================
# resolve_answer_label
# =========================================================================


class TestResolveAnswerLabel:
    """Tests for resolve_answer_label pure function."""

    def test_none_answer(self):
        assert resolve_answer_label({}, None) is None

    def test_free_text_default(self):
        assert resolve_answer_label({}, "hello") == "hello"

    def test_single_choice_by_id(self):
        q = {
            "answer_type": "single_choice",
            "choices": [
                {"id": "a", "label": "Option A"},
                {"id": "b", "label": "Option B"},
            ],
        }
        assert resolve_answer_label(q, "b") == "Option B"

    def test_single_choice_by_value(self):
        q = {
            "answer_type": "single_choice",
            "choices": [{"value": "v1", "label": "Val One"}],
        }
        assert resolve_answer_label(q, "v1") == "Val One"

    def test_single_choice_no_match(self):
        q = {
            "answer_type": "single_choice",
            "choices": [{"id": "a", "label": "A"}],
        }
        # Falls through to str(user_answer)
        assert resolve_answer_label(q, "unknown") == "unknown"

    def test_single_choice_empty_choices(self):
        q = {"answer_type": "single_choice", "choices": []}
        assert resolve_answer_label(q, "x") == "x"

    def test_multi_choice(self):
        q = {
            "answer_type": "multi_choice",
            "choices": [
                {"id": "a", "label": "Alpha"},
                {"id": "b", "label": "Beta"},
                {"id": "c", "label": "Gamma"},
            ],
        }
        result = resolve_answer_label(q, ["a", "c"])
        assert result == "Alpha, Gamma"

    def test_multi_choice_with_unknown_ids(self):
        q = {
            "answer_type": "multi_choice",
            "choices": [{"id": "a", "label": "Alpha"}],
        }
        result = resolve_answer_label(q, ["a", "missing"])
        assert result == "Alpha, missing"

    def test_multi_choice_non_list_answer(self):
        q = {
            "answer_type": "multi_choice",
            "choices": [{"id": "a", "label": "Alpha"}],
        }
        # Non-list answer falls through
        assert resolve_answer_label(q, "a") == "a"

    def test_yes_no_true(self):
        q = {"answer_type": "yes_no"}
        assert resolve_answer_label(q, True) == "Yes"

    def test_yes_no_false(self):
        q = {"answer_type": "yes_no"}
        assert resolve_answer_label(q, False) == "No"

    def test_yes_no_non_bool(self):
        q = {"answer_type": "yes_no"}
        assert resolve_answer_label(q, "yes") == "yes"

    def test_list_answer_joined(self):
        q = {}
        assert resolve_answer_label(q, ["a", "b"]) == "a, b"

    def test_int_answer_to_string(self):
        q = {}
        assert resolve_answer_label(q, 42) == "42"

    def test_empty_question(self):
        assert resolve_answer_label({}, "answer") == "answer"


# =========================================================================
# build_pgc_from_answers
# =========================================================================


class TestBuildPgcFromAnswers:
    """Tests for build_pgc_from_answers pure function."""

    def test_basic_question_answer(self):
        questions = [{"id": "q1", "text": "What lang?"}]
        answers = {"q1": "Python"}
        result = build_pgc_from_answers(questions, answers)
        assert len(result) == 1
        assert result[0]["question_id"] == "q1"
        assert result[0]["question"] == "What lang?"
        assert result[0]["answer"] == "Python"

    def test_missing_answer(self):
        questions = [{"id": "q1", "text": "Q1"}]
        answers = {}
        result = build_pgc_from_answers(questions, answers)
        assert result[0]["answer"] is None

    def test_binding_from_constraint_kind(self):
        questions = [{"id": "q1", "text": "Q1", "constraint_kind": "exclusion"}]
        result = build_pgc_from_answers(questions, {"q1": "no"})
        assert result[0]["binding"] is True

    def test_binding_from_priority_must(self):
        questions = [{"id": "q1", "text": "Q1", "priority": "must"}]
        result = build_pgc_from_answers(questions, {"q1": "yes"})
        assert result[0]["binding"] is True

    def test_non_binding_default(self):
        questions = [{"id": "q1", "text": "Q1"}]
        result = build_pgc_from_answers(questions, {"q1": "val"})
        assert result[0]["binding"] is False

    def test_why_it_matters(self):
        questions = [{"id": "q1", "text": "Q1", "why_it_matters": "Important"}]
        result = build_pgc_from_answers(questions, {})
        assert result[0]["why_it_matters"] == "Important"

    def test_multiple_questions(self):
        questions = [
            {"id": "q1", "text": "Q1"},
            {"id": "q2", "text": "Q2"},
        ]
        answers = {"q1": "A1", "q2": "A2"}
        result = build_pgc_from_answers(questions, answers)
        assert len(result) == 2

    def test_empty_questions(self):
        assert build_pgc_from_answers([], {}) == []

    def test_with_choices_resolution(self):
        questions = [
            {
                "id": "q1",
                "text": "Which?",
                "answer_type": "single_choice",
                "choices": [{"id": "a", "label": "Option A"}],
            }
        ]
        answers = {"q1": "a"}
        result = build_pgc_from_answers(questions, answers)
        assert result[0]["answer"] == "Option A"


# =========================================================================
# build_pgc_from_context_state
# =========================================================================


class TestBuildPgcFromContextState:
    """Tests for build_pgc_from_context_state pure function."""

    def test_empty_context(self):
        assert build_pgc_from_context_state({}) == []

    def test_pgc_clarifications_format(self):
        context = {
            "pgc_clarifications": [
                {
                    "id": "q1",
                    "text": "What?",
                    "why_it_matters": "Because",
                    "user_answer_label": "Python",
                    "binding": True,
                    "resolved": True,
                },
            ]
        }
        result = build_pgc_from_context_state(context)
        assert len(result) == 1
        assert result[0]["question_id"] == "q1"
        assert result[0]["answer"] == "Python"
        assert result[0]["binding"] is True

    def test_pgc_clarifications_unresolved_excluded(self):
        context = {
            "pgc_clarifications": [
                {"id": "q1", "text": "Resolved", "resolved": True, "user_answer_label": "Yes"},
                {"id": "q2", "text": "Unresolved", "resolved": False, "user_answer_label": "No"},
            ]
        }
        result = build_pgc_from_context_state(context)
        assert len(result) == 1
        assert result[0]["question_id"] == "q1"

    def test_pgc_clarifications_falls_back_to_user_answer(self):
        context = {
            "pgc_clarifications": [
                {"id": "q1", "text": "Q", "user_answer": "fallback_val"},
            ]
        }
        result = build_pgc_from_context_state(context)
        assert result[0]["answer"] == "fallback_val"

    def test_document_pgc_clarifications_format(self):
        context = {
            "document_pgc_clarifications.intake": {
                "clarifications": [
                    {"id": "q1", "question": "What?", "answer": "Python", "binding": True},
                ]
            },
            "pgc_questions": {
                "questions": [
                    {"id": "q1", "why_it_matters": "Reason"},
                ]
            },
        }
        result = build_pgc_from_context_state(context)
        assert len(result) == 1
        assert result[0]["why_it_matters"] == "Reason"

    def test_document_pgc_priority_must_is_binding(self):
        context = {
            "document_pgc_clarifications.intake": {
                "clarifications": [
                    {"id": "q1", "question": "What?", "answer": "Yes", "priority": "must"},
                ]
            },
        }
        result = build_pgc_from_context_state(context)
        assert result[0]["binding"] is True

    def test_raw_fallback_questions_answers(self):
        context = {
            "pgc_questions": {
                "questions": [
                    {"id": "q1", "text": "Which?", "why_it_matters": "Important"},
                ]
            },
            "pgc_answers": {"q1": "Python"},
        }
        result = build_pgc_from_context_state(context)
        assert len(result) == 1
        assert result[0]["question"] == "Which?"
        assert result[0]["answer"] == "Python"
        assert result[0]["why_it_matters"] == "Important"

    def test_raw_fallback_empty_answers(self):
        context = {
            "pgc_questions": {"questions": [{"id": "q1", "text": "Q"}]},
            "pgc_answers": {},
        }
        # Both questions_list and raw_answers must be truthy
        result = build_pgc_from_context_state(context)
        assert result == []

    def test_raw_fallback_binding_from_constraint_kind(self):
        context = {
            "pgc_questions": {
                "questions": [
                    {"id": "q1", "text": "Q", "constraint_kind": "requirement"},
                ]
            },
            "pgc_answers": {"q1": "yes"},
        }
        result = build_pgc_from_context_state(context)
        assert result[0]["binding"] is True

    def test_priority_order_pgc_clarifications_first(self):
        """pgc_clarifications takes priority over other formats."""
        context = {
            "pgc_clarifications": [
                {"id": "q1", "text": "From clars", "user_answer_label": "A"},
            ],
            "pgc_questions": {"questions": [{"id": "q1", "text": "From raw"}]},
            "pgc_answers": {"q1": "B"},
        }
        result = build_pgc_from_context_state(context)
        assert result[0]["answer"] == "A"


# =========================================================================
# build_resolution_dict
# =========================================================================


class TestBuildResolutionDict:
    """Tests for build_resolution_dict pure function."""

    def test_all_fields(self):
        result = build_resolution_dict(
            answers={"q1": "a"},
            decision="approve",
            notes="looks good",
            escalation_option="retry",
        )
        assert result["answers"] == {"q1": "a"}
        assert result["decision"] == "approve"
        assert result["notes"] == "looks good"
        assert result["escalation_option"] == "retry"

    def test_answers_only(self):
        result = build_resolution_dict(answers={"q1": "a"}, decision=None, notes=None, escalation_option=None)
        assert result == {"answers": {"q1": "a"}}

    def test_none_all(self):
        result = build_resolution_dict(answers=None, decision=None, notes=None, escalation_option=None)
        assert result == {}

    def test_empty_dict_answers_falsy(self):
        result = build_resolution_dict(answers={}, decision=None, notes=None, escalation_option=None)
        assert result == {}

    def test_decision_only(self):
        result = build_resolution_dict(answers=None, decision="reject", notes=None, escalation_option=None)
        assert result == {"decision": "reject"}

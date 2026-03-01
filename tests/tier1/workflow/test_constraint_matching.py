"""Tests for constraint_matching pure functions.

Extracted from plan_executor._pin_invariants_to_known_constraints() per WS-CRAP-007.
Tier-1: in-memory, no DB.
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

from app.domain.workflow.constraint_matching import (  # noqa: E402
    build_pinned_constraints,
    filter_duplicate_constraints,
    is_duplicate_of_pinned,
    pin_invariants_to_constraints,
)


# ---------------------------------------------------------------------------
# build_pinned_constraints
# ---------------------------------------------------------------------------


class TestBuildPinnedConstraints:
    """Tests for build_pinned_constraints."""

    def test_empty_invariants(self):
        constraints, keywords = build_pinned_constraints([])
        assert constraints == []
        assert keywords == set()

    def test_single_invariant_with_answer_label(self):
        invariants = [
            {
                "id": "TARGET_PLATFORM",
                "user_answer_label": "Web application",
            }
        ]
        constraints, keywords = build_pinned_constraints(invariants)
        assert len(constraints) == 1
        assert constraints[0]["text"] == "Web application"
        assert constraints[0]["source"] == "user_clarification"
        assert constraints[0]["constraint_id"] == "TARGET_PLATFORM"
        assert constraints[0]["binding"] is True

    def test_normalized_text_preferred(self):
        invariants = [
            {
                "id": "SCOPE",
                "user_answer_label": "include math",
                "normalized_text": "Must include math operations",
            }
        ]
        constraints, keywords = build_pinned_constraints(invariants)
        assert constraints[0]["text"] == "Must include math operations"

    def test_keywords_include_answer_words(self):
        invariants = [
            {
                "id": "PLATFORM",
                "user_answer_label": "React web application",
            }
        ]
        _, keywords = build_pinned_constraints(invariants)
        assert "react" in keywords
        assert "application" in keywords
        # Short words skipped
        assert "web" not in keywords  # len("web") == 3

    def test_keywords_include_normalized_words(self):
        invariants = [
            {
                "id": "SCOPE",
                "user_answer_label": "yes",
                "normalized_text": "Must include advanced features",
            }
        ]
        _, keywords = build_pinned_constraints(invariants)
        assert "must" in keywords
        assert "include" in keywords
        assert "advanced" in keywords
        assert "features" in keywords

    def test_keywords_include_constraint_id_parts(self):
        invariants = [
            {
                "id": "TARGET_PLATFORM",
                "user_answer_label": "Desktop app",
            }
        ]
        _, keywords = build_pinned_constraints(invariants)
        assert "target" in keywords
        assert "platform" in keywords

    def test_empty_answer_label_skipped(self):
        invariants = [
            {
                "id": "EMPTY",
                "user_answer_label": "",
            }
        ]
        constraints, _ = build_pinned_constraints(invariants)
        assert constraints == []

    def test_none_answer_falls_back_to_user_answer(self):
        invariants = [
            {
                "id": "TEST",
                "user_answer": "some value",
            }
        ]
        constraints, _ = build_pinned_constraints(invariants)
        assert len(constraints) == 1
        assert constraints[0]["text"] == "some value"

    def test_multiple_invariants(self):
        invariants = [
            {"id": "A", "user_answer_label": "Alpha"},
            {"id": "B", "user_answer_label": "Bravo"},
        ]
        constraints, _ = build_pinned_constraints(invariants)
        assert len(constraints) == 2


# ---------------------------------------------------------------------------
# is_duplicate_of_pinned
# ---------------------------------------------------------------------------


class TestIsDuplicateOfPinned:
    """Tests for is_duplicate_of_pinned."""

    def test_string_constraint_with_enough_keywords(self):
        keywords = {"react", "application", "platform"}
        assert is_duplicate_of_pinned("Build a React application", keywords) is True

    def test_string_constraint_below_threshold(self):
        keywords = {"react", "application", "platform"}
        assert is_duplicate_of_pinned("Build a Django app", keywords) is False

    def test_dict_constraint_text_field(self):
        keywords = {"react", "application"}
        constraint = {"text": "React web application framework"}
        assert is_duplicate_of_pinned(constraint, keywords) is True

    def test_dict_constraint_description_field(self):
        keywords = {"react", "application"}
        constraint = {"description": "React application deployment"}
        assert is_duplicate_of_pinned(constraint, keywords) is True

    def test_dict_constraint_constraint_field(self):
        keywords = {"react", "application"}
        constraint = {"constraint": "Use React for the application"}
        assert is_duplicate_of_pinned(constraint, keywords) is True

    def test_non_string_non_dict_returns_false(self):
        keywords = {"react", "application"}
        assert is_duplicate_of_pinned(42, keywords) is False
        assert is_duplicate_of_pinned(None, keywords) is False

    def test_empty_keywords_no_match(self):
        assert is_duplicate_of_pinned("anything", set()) is False

    def test_single_keyword_not_enough(self):
        keywords = {"react"}
        assert is_duplicate_of_pinned("Use React", keywords) is False

    def test_case_insensitive(self):
        keywords = {"react", "application"}
        assert is_duplicate_of_pinned("REACT APPLICATION", keywords) is True


# ---------------------------------------------------------------------------
# filter_duplicate_constraints
# ---------------------------------------------------------------------------


class TestFilterDuplicateConstraints:
    """Tests for filter_duplicate_constraints."""

    def test_empty_list(self):
        filtered, count = filter_duplicate_constraints([], {"keyword"})
        assert filtered == []
        assert count == 0

    def test_no_duplicates(self):
        constraints = ["unique constraint about Django"]
        filtered, count = filter_duplicate_constraints(
            constraints, {"react", "application"}
        )
        assert filtered == constraints
        assert count == 0

    def test_all_duplicates(self):
        constraints = [
            "React application framework",
            {"text": "Build React application"},
        ]
        filtered, count = filter_duplicate_constraints(
            constraints, {"react", "application"}
        )
        assert filtered == []
        assert count == 2

    def test_mixed(self):
        constraints = [
            "React application setup",
            "Django REST framework",
            {"text": "Deploy React application"},
        ]
        filtered, count = filter_duplicate_constraints(
            constraints, {"react", "application"}
        )
        assert len(filtered) == 1
        assert filtered[0] == "Django REST framework"
        assert count == 2


# ---------------------------------------------------------------------------
# pin_invariants_to_constraints (integration of sub-functions)
# ---------------------------------------------------------------------------


class TestPinInvariantsToConstraints:
    """Tests for pin_invariants_to_constraints."""

    def test_empty_invariants_returns_document_unchanged(self):
        doc = {"known_constraints": ["existing"]}
        result = pin_invariants_to_constraints(doc, [])
        assert result is doc  # Same reference, no copy needed

    def test_does_not_mutate_original(self):
        doc = {"known_constraints": ["existing"]}
        invariants = [
            {"id": "PLATFORM", "user_answer_label": "Web app"},
        ]
        result = pin_invariants_to_constraints(doc, invariants)
        # Original unchanged
        assert doc["known_constraints"] == ["existing"]
        # Result has pinned + original
        assert len(result["known_constraints"]) > 1

    def test_pinned_first_then_llm(self):
        doc = {"known_constraints": ["LLM constraint"]}
        invariants = [
            {"id": "SCOPE", "user_answer_label": "Include testing"},
        ]
        result = pin_invariants_to_constraints(doc, invariants)
        constraints = result["known_constraints"]
        # First item should be the pinned one
        assert constraints[0]["source"] == "user_clarification"
        assert constraints[0]["binding"] is True
        # Second is the original LLM constraint
        assert constraints[1] == "LLM constraint"

    def test_duplicates_removed(self):
        doc = {
            "known_constraints": [
                {"text": "Deploy as web application on cloud platform"},
                "Unrelated constraint",
            ]
        }
        invariants = [
            {
                "id": "TARGET_PLATFORM",
                "user_answer_label": "Web application",
                "normalized_text": "Application must run on cloud platform",
            }
        ]
        result = pin_invariants_to_constraints(doc, invariants)
        constraints = result["known_constraints"]
        # Should have the pinned one + the unrelated one
        # The duplicate dict one should be removed
        assert len(constraints) == 2
        assert constraints[0]["source"] == "user_clarification"
        assert constraints[1] == "Unrelated constraint"

    def test_no_known_constraints_key(self):
        doc = {"title": "Test"}
        invariants = [
            {"id": "TEST", "user_answer_label": "Value here"},
        ]
        result = pin_invariants_to_constraints(doc, invariants)
        assert len(result["known_constraints"]) == 1

    def test_non_list_known_constraints_treated_as_empty(self):
        doc = {"known_constraints": "invalid"}
        invariants = [
            {"id": "TEST", "user_answer_label": "Value here"},
        ]
        result = pin_invariants_to_constraints(doc, invariants)
        assert len(result["known_constraints"]) == 1
        assert result["known_constraints"][0]["source"] == "user_clarification"

"""Tier-1 tests for WP evaluator semantic presence checks.

Tests classify_field_content() and semantic_presence_checks().
Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.wp_defect_evaluator import (
    classify_field_content,
    evaluate_wp,
)


# =========================================================================
# classify_field_content
# =========================================================================


class TestClassifyFieldContent:

    # --- ABSENT ---

    def test_none_is_absent(self):
        assert classify_field_content(None) == "ABSENT"

    # --- EMPTY ---

    def test_empty_string_is_empty(self):
        assert classify_field_content("") == "EMPTY"

    def test_whitespace_only_is_empty(self):
        assert classify_field_content("   ") == "EMPTY"

    def test_empty_list_is_empty(self):
        assert classify_field_content([]) == "EMPTY"

    # --- WEAK ---

    def test_placeholder_tbd_is_weak(self):
        assert classify_field_content("TBD") == "WEAK"

    def test_placeholder_na_is_weak(self):
        assert classify_field_content("N/A") == "WEAK"

    def test_placeholder_none_text_is_weak(self):
        assert classify_field_content("none") == "WEAK"

    def test_placeholder_todo_is_weak(self):
        assert classify_field_content("TODO") == "WEAK"

    def test_short_string_is_weak(self):
        assert classify_field_content("Do it", min_length=15) == "WEAK"

    def test_short_list_single_trivial_item(self):
        assert classify_field_content(["TBD"], min_length=10) == "WEAK"

    # --- MEANINGFUL ---

    def test_substantive_string_is_meaningful(self):
        assert classify_field_content(
            "Implement user authentication with bcrypt password hashing",
            min_length=15,
        ) == "MEANINGFUL"

    def test_substantive_list_is_meaningful(self):
        assert classify_field_content(
            ["Step 1: Write failing tests", "Step 2: Implement the fix"],
            min_length=10,
        ) == "MEANINGFUL"

    def test_list_with_enough_items(self):
        assert classify_field_content(
            ["First item", "Second item"],
            min_length=5,
        ) == "MEANINGFUL"


# =========================================================================
# Semantic checks in evaluate_wp
# =========================================================================


def _good_wp():
    return {
        "wp_id": "WP-001",
        "title": "Test Work Package",
        "rationale": "Critical authentication module required before any downstream features",
        "scope_in": ["Login form implementation", "Password hashing with bcrypt"],
        "scope_out": ["OAuth integration deferred to phase 2"],
        "definition_of_done": ["Users can log in with username and password", "Sessions persist across page refreshes"],
        "governance_pins": {
            "ta_version_id": "TA-v1.0",
            "policy_refs": ["POL-ADR-EXEC-001"],
            "adr_refs": [],
        },
    }


class TestSemanticChecksInEvaluator:

    def test_good_wp_no_semantic_failures(self):
        report = evaluate_wp(_good_wp())
        sem_checks = [c for c in report.checks if c["check_id"].startswith("semantic_")]
        failures = [c for c in sem_checks if c["status"] == "fail"]
        assert len(failures) == 0

    def test_weak_rationale_flagged(self):
        wp = _good_wp()
        wp["rationale"] = "TBD"
        report = evaluate_wp(wp)
        sem = [c for c in report.checks if c["check_id"] == "semantic_rationale"]
        assert len(sem) == 1
        assert sem[0]["status"] == "fail"
        assert "WEAK" in sem[0]["evidence"]

    def test_empty_rationale_flagged(self):
        wp = _good_wp()
        wp["rationale"] = ""
        report = evaluate_wp(wp)
        sem = [c for c in report.checks if c["check_id"] == "semantic_rationale"]
        assert sem[0]["status"] == "fail"
        assert "EMPTY" in sem[0]["evidence"]

    def test_absent_rationale_flagged(self):
        wp = _good_wp()
        del wp["rationale"]
        report = evaluate_wp(wp)
        sem = [c for c in report.checks if c["check_id"] == "semantic_rationale"]
        assert sem[0]["status"] == "fail"
        assert "ABSENT" in sem[0]["evidence"]

    def test_weak_scope_flagged(self):
        wp = _good_wp()
        wp["scope_in"] = ["stuff"]
        wp["scope_out"] = ["nah"]
        report = evaluate_wp(wp)
        sem = [c for c in report.checks if c["check_id"] == "semantic_scope"]
        assert len(sem) == 1
        assert sem[0]["status"] == "fail"

    def test_good_scope_passes(self):
        report = evaluate_wp(_good_wp())
        sem = [c for c in report.checks if c["check_id"] == "semantic_scope"]
        assert sem[0]["status"] == "pass"


class TestEvaluatorVersionBump:

    def test_version_is_1_1(self):
        report = evaluate_wp(_good_wp())
        assert report.evaluator_version == "1.1"

"""Tier-1 tests for WS defect evaluator (WS-PI-0B Step 4).

Tests the structured evaluation of WS-generation LLM outputs against
defect categories. Pure unit tests — no DB, no LLM calls.
"""

import pytest

from app.domain.services.ws_defect_evaluator import evaluate_ws, EvaluationReport


# =========================================================================
# Fixtures — known-good and known-bad WS JSON
# =========================================================================

def _good_ws():
    """A well-formed WS with all sections and valid governance pins."""
    return {
        "objective": "Implement user authentication module",
        "scope": {
            "in_scope": ["OAuth2 integration", "Session management"],
            "out_of_scope": ["Social login", "MFA"],
        },
        "procedure": [
            {"step": 1, "action": "Write failing tests for auth service (from WP-AUTH-001)"},
            {"step": 2, "action": "Write failing tests for session repository (from TA section 4.2)"},
            {"step": 3, "action": "Implement auth service per TA specification"},
            {"step": 4, "action": "Implement session repository per WP-AUTH-001 design"},
            {"step": 5, "action": "Verify all tests pass"},
        ],
        "verification_criteria": [
            "All tier-1 tests pass",
            "OAuth2 flow completes end-to-end",
        ],
        "allowed_paths": ["app/auth/", "tests/tier1/auth/"],
        "prohibited_actions": ["Do not modify database schema"],
        "governance_pins": {
            "ta_version_id": "ta-v2.1.0",
            "policy_refs": ["POL-WS-001", "POL-QA-001"],
        },
    }


def _bad_ws_empty_pins():
    """WS with empty governance pins."""
    ws = _good_ws()
    ws["governance_pins"] = {"ta_version_id": "", "policy_refs": []}
    return ws


def _bad_ws_missing_sections():
    """WS missing several required sections."""
    return {
        "objective": "Do something",
        "scope": {"in_scope": ["stuff"]},
        "procedure": [{"step": 1, "action": "Do it"}],
    }


def _bad_ws_tests_after_impl():
    """WS with implementation steps before test steps."""
    ws = _good_ws()
    ws["procedure"] = [
        {"step": 1, "action": "Implement the auth service per TA spec"},
        {"step": 2, "action": "Implement session management per WP design"},
        {"step": 3, "action": "Write tests for auth service"},
        {"step": 4, "action": "Verify all tests pass"},
    ]
    return ws


def _ws_with_ungrounded_steps():
    """WS with steps that lack grounding cues (no WP/TA/policy references)."""
    ws = _good_ws()
    ws["procedure"] = [
        {"step": 1, "action": "Write failing tests for auth service (from WP-AUTH-001)"},
        {"step": 2, "action": "Add some nice logging"},
        {"step": 3, "action": "Implement auth service per TA specification"},
        {"step": 4, "action": "Clean up the code and make it pretty"},
        {"step": 5, "action": "Verify all tests pass"},
    ]
    return ws


def _ws_with_contradiction_disclosure():
    """WS that explicitly discloses a contradiction."""
    ws = _good_ws()
    ws["contradiction_notes"] = [
        "WP-AUTH-001 specifies JWT but TA recommends session cookies. Using JWT per WP."
    ]
    return ws


def _ws_without_contradiction_disclosure():
    """WS with no contradiction notes field."""
    ws = _good_ws()
    # No contradiction_notes key at all
    return ws


# =========================================================================
# EvaluationReport structure
# =========================================================================


class TestEvaluationReportStructure:
    """Verify the report has the correct shape."""

    def test_report_has_required_fields(self):
        report = evaluate_ws(_good_ws())
        assert isinstance(report, EvaluationReport)
        assert report.artifact_type == "work_statement"
        assert report.evaluator_version == "1.1"
        assert isinstance(report.checks, list)
        assert len(report.checks) > 0
        assert hasattr(report, "summary")

    def test_summary_counts(self):
        report = evaluate_ws(_good_ws())
        s = report.summary
        assert "passed" in s
        assert "failed" in s
        assert "advisory" in s
        assert "not_evaluable" in s
        total = s["passed"] + s["failed"] + s["advisory"] + s["not_evaluable"]
        assert total == len(report.checks)

    def test_each_check_has_contract_fields(self):
        report = evaluate_ws(_good_ws())
        for check in report.checks:
            assert "check_id" in check
            assert "status" in check
            assert check["status"] in ("pass", "fail", "advisory", "not_evaluable")
            assert "evidence" in check
            assert "notes" in check


# =========================================================================
# governance_pins_populated
# =========================================================================


class TestGovernancePinsPopulated:
    """Tests for the governance_pins_populated check."""

    def test_pass_when_pins_populated(self):
        report = evaluate_ws(_good_ws())
        check = _find_check(report, "governance_pins_populated")
        assert check["status"] == "pass"

    def test_fail_when_pins_empty(self):
        report = evaluate_ws(_bad_ws_empty_pins())
        check = _find_check(report, "governance_pins_populated")
        assert check["status"] == "fail"
        assert "ta_version_id" in check["evidence"] or "policy_refs" in check["evidence"]

    def test_fail_when_pins_missing(self):
        ws = _good_ws()
        del ws["governance_pins"]
        report = evaluate_ws(ws)
        check = _find_check(report, "governance_pins_populated")
        assert check["status"] == "fail"

    def test_fail_when_ta_version_id_missing(self):
        ws = _good_ws()
        ws["governance_pins"] = {"policy_refs": ["POL-WS-001"]}
        report = evaluate_ws(ws)
        check = _find_check(report, "governance_pins_populated")
        assert check["status"] == "fail"

    def test_fail_when_policy_refs_missing(self):
        ws = _good_ws()
        ws["governance_pins"] = {"ta_version_id": "ta-v2.1.0"}
        report = evaluate_ws(ws)
        check = _find_check(report, "governance_pins_populated")
        assert check["status"] == "fail"


# =========================================================================
# required_sections_present
# =========================================================================


class TestRequiredSectionsPresent:
    """Tests for the required_sections_present check."""

    def test_pass_when_all_sections_present(self):
        report = evaluate_ws(_good_ws())
        check = _find_check(report, "required_sections_present")
        assert check["status"] == "pass"

    def test_fail_when_sections_missing(self):
        report = evaluate_ws(_bad_ws_missing_sections())
        check = _find_check(report, "required_sections_present")
        assert check["status"] == "fail"
        # Evidence should mention what's missing
        assert "missing" in check["evidence"].lower() or "verification" in check["evidence"].lower()

    def test_pass_with_scope_in_scope_out(self):
        """Accept scope_in/scope_out as equivalent to nested scope."""
        ws = _good_ws()
        del ws["scope"]
        ws["scope_in"] = ["OAuth2 integration"]
        ws["scope_out"] = ["Social login"]
        report = evaluate_ws(ws)
        check = _find_check(report, "required_sections_present")
        assert check["status"] == "pass"

    def test_pass_with_only_scope_in(self):
        """Accept scope_in alone as satisfying scope requirement."""
        ws = _good_ws()
        del ws["scope"]
        ws["scope_in"] = ["OAuth2 integration"]
        report = evaluate_ws(ws)
        check = _find_check(report, "required_sections_present")
        assert check["status"] == "pass"


# =========================================================================
# tests_before_implementation
# =========================================================================


class TestTestsBeforeImplementation:
    """Tests for the tests_before_implementation check."""

    def test_pass_when_tests_first(self):
        report = evaluate_ws(_good_ws())
        check = _find_check(report, "tests_before_implementation")
        assert check["status"] == "pass"

    def test_fail_when_implementation_first(self):
        report = evaluate_ws(_bad_ws_tests_after_impl())
        check = _find_check(report, "tests_before_implementation")
        assert check["status"] == "fail"


# =========================================================================
# step_grounding_heuristic
# =========================================================================


class TestStepGroundingHeuristic:
    """Tests for the step_grounding_heuristic check (advisory only)."""

    def test_advisory_status_always(self):
        """This check must always return advisory, never pass or fail."""
        report = evaluate_ws(_good_ws())
        check = _find_check(report, "step_grounding_heuristic")
        assert check["status"] == "advisory"

    def test_flags_ungrounded_steps(self):
        report = evaluate_ws(_ws_with_ungrounded_steps())
        check = _find_check(report, "step_grounding_heuristic")
        assert check["status"] == "advisory"
        # Evidence should mention the ungrounded steps
        assert "logging" in check["evidence"].lower() or "clean up" in check["evidence"].lower()

    def test_fewer_flags_when_mostly_grounded(self):
        """Good WS has mostly grounded steps; only 'Verify all tests pass' lacks cues."""
        report = evaluate_ws(_good_ws())
        check = _find_check(report, "step_grounding_heuristic")
        assert check["status"] == "advisory"
        # Should flag at most 1 step (the generic verify step)
        assert "1 steps lack" in check["evidence"] or "0 ungrounded" in check["evidence"]


# =========================================================================
# contradiction_disclosure_present
# =========================================================================


class TestContradictionDisclosurePresent:
    """Tests for the contradiction_disclosure_present check."""

    def test_pass_when_disclosure_present(self):
        report = evaluate_ws(_ws_with_contradiction_disclosure())
        check = _find_check(report, "contradiction_disclosure_present")
        assert check["status"] == "pass"

    def test_not_evaluable_when_no_disclosure_field(self):
        report = evaluate_ws(_ws_without_contradiction_disclosure())
        check = _find_check(report, "contradiction_disclosure_present")
        assert check["status"] == "not_evaluable"

    def test_never_returns_fail(self):
        """This check must never return 'fail' — it's a disclosure check."""
        for ws_fn in [_good_ws, _bad_ws_empty_pins, _bad_ws_missing_sections,
                       _ws_with_contradiction_disclosure, _ws_without_contradiction_disclosure]:
            report = evaluate_ws(ws_fn())
            check = _find_check(report, "contradiction_disclosure_present")
            assert check["status"] != "fail", f"Got 'fail' for {ws_fn.__name__}"


# =========================================================================
# Helpers
# =========================================================================


def _find_check(report: EvaluationReport, check_id: str) -> dict:
    """Find a check by ID in a report, or fail the test."""
    for check in report.checks:
        if check["check_id"] == check_id:
            return check
    pytest.fail(f"Check '{check_id}' not found in report. Found: {[c['check_id'] for c in report.checks]}")

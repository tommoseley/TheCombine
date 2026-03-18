"""Tier-1 tests for WP defect evaluator.

Pure unit tests — no DB, no LLM calls.
Tests the 5 structural checks for Work Package quality measurement.
"""

from app.domain.services.wp_defect_evaluator import (
    WPEvaluationReport,
    evaluate_wp,
)


def _good_wp():
    return {
        "wp_id": "WP-001",
        "title": "Test Work Package",
        "rationale": "Critical authentication module required before downstream features can proceed",
        "scope_in": ["Login form implementation with validation", "Password hashing using bcrypt"],
        "scope_out": ["OAuth integration deferred to phase 2"],
        "definition_of_done": ["Users can log in with username and password", "Sessions persist across refreshes"],
        "governance_pins": {
            "ta_version_id": "TA-v1.0-baseline",
            "policy_refs": ["POL-ADR-EXEC-001"],
            "adr_refs": ["ADR-052"],
        },
        "contradiction_notes": ["TA specifies REST but WP scope includes GraphQL"],
        "ws_index": [
            {"ws_id": "WS-001", "order_key": "a0"},
            {"ws_id": "WS-002", "order_key": "a1"},
        ],
    }


def _bad_wp_empty_pins():
    wp = _good_wp()
    wp["governance_pins"] = {
        "ta_version_id": "",
        "policy_refs": [],
        "adr_refs": [],
    }
    return wp


def _bad_wp_missing_sections():
    return {
        "wp_id": "WP-001",
    }


# =========================================================================
# Governance pins check
# =========================================================================


class TestGovernancePins:

    def test_good_wp_passes(self):
        report = evaluate_wp(_good_wp())
        pins_check = [c for c in report.checks if c["check_id"] == "governance_pins_populated"]
        assert pins_check[0]["status"] == "pass"

    def test_empty_pins_fails(self):
        report = evaluate_wp(_bad_wp_empty_pins())
        pins_check = [c for c in report.checks if c["check_id"] == "governance_pins_populated"]
        assert pins_check[0]["status"] == "fail"

    def test_missing_pins_fails(self):
        wp = _good_wp()
        del wp["governance_pins"]
        report = evaluate_wp(wp)
        pins_check = [c for c in report.checks if c["check_id"] == "governance_pins_populated"]
        assert pins_check[0]["status"] == "fail"


# =========================================================================
# Required sections check
# =========================================================================


class TestRequiredSections:

    def test_good_wp_passes(self):
        report = evaluate_wp(_good_wp())
        sec_check = [c for c in report.checks if c["check_id"] == "required_sections_present"]
        assert sec_check[0]["status"] == "pass"

    def test_missing_sections_fails(self):
        report = evaluate_wp(_bad_wp_missing_sections())
        sec_check = [c for c in report.checks if c["check_id"] == "required_sections_present"]
        assert sec_check[0]["status"] == "fail"
        assert "rationale" in sec_check[0]["evidence"]

    def test_scope_in_out_accepted(self):
        """scope_in/scope_out counts as having scope."""
        wp = _good_wp()
        # Already has scope_in/scope_out, no "scope" key
        assert "scope" not in wp
        report = evaluate_wp(wp)
        sec_check = [c for c in report.checks if c["check_id"] == "required_sections_present"]
        assert sec_check[0]["status"] == "pass"

    def test_nested_scope_accepted(self):
        """Nested scope dict also counts."""
        wp = _good_wp()
        del wp["scope_in"]
        del wp["scope_out"]
        wp["scope"] = {"in_scope": ["A"], "out_of_scope": ["B"]}
        report = evaluate_wp(wp)
        sec_check = [c for c in report.checks if c["check_id"] == "required_sections_present"]
        assert sec_check[0]["status"] == "pass"


# =========================================================================
# Policy floor check
# =========================================================================


class TestPolicyFloor:

    def test_good_wp_passes(self):
        report = evaluate_wp(_good_wp())
        floor_check = [c for c in report.checks if c["check_id"] == "policy_floor_present"]
        assert floor_check[0]["status"] == "pass"

    def test_missing_floor_fails(self):
        wp = _good_wp()
        wp["governance_pins"]["policy_refs"] = ["POL-QA-001"]
        report = evaluate_wp(wp)
        floor_check = [c for c in report.checks if c["check_id"] == "policy_floor_present"]
        assert floor_check[0]["status"] == "fail"
        assert "POL-ADR-EXEC-001" in floor_check[0]["evidence"]

    def test_empty_policy_refs_fails(self):
        report = evaluate_wp(_bad_wp_empty_pins())
        floor_check = [c for c in report.checks if c["check_id"] == "policy_floor_present"]
        assert floor_check[0]["status"] == "fail"


# =========================================================================
# Contradiction disclosure check
# =========================================================================


class TestContradictionDisclosure:

    def test_present_passes(self):
        report = evaluate_wp(_good_wp())
        cd_check = [c for c in report.checks if c["check_id"] == "contradiction_disclosure_present"]
        assert cd_check[0]["status"] == "pass"

    def test_absent_not_evaluable(self):
        wp = _good_wp()
        del wp["contradiction_notes"]
        report = evaluate_wp(wp)
        cd_check = [c for c in report.checks if c["check_id"] == "contradiction_disclosure_present"]
        assert cd_check[0]["status"] == "not_evaluable"


# =========================================================================
# ws_index check
# =========================================================================


class TestWSIndex:

    def test_populated_passes(self):
        report = evaluate_wp(_good_wp())
        idx_check = [c for c in report.checks if c["check_id"] == "ws_index_present"]
        assert idx_check[0]["status"] == "pass"

    def test_empty_advisory(self):
        wp = _good_wp()
        wp["ws_index"] = []
        report = evaluate_wp(wp)
        idx_check = [c for c in report.checks if c["check_id"] == "ws_index_present"]
        assert idx_check[0]["status"] == "advisory"

    def test_missing_advisory(self):
        wp = _good_wp()
        del wp["ws_index"]
        report = evaluate_wp(wp)
        idx_check = [c for c in report.checks if c["check_id"] == "ws_index_present"]
        assert idx_check[0]["status"] == "advisory"


# =========================================================================
# Report structure
# =========================================================================


class TestReportStructure:

    def test_good_wp_report(self):
        report = evaluate_wp(_good_wp())
        assert isinstance(report, WPEvaluationReport)
        assert report.artifact_type == "work_package"
        assert len(report.checks) == 8  # 5 structural + 3 semantic
        assert report.summary["failed"] == 0

    def test_bad_wp_report_counts(self):
        report = evaluate_wp(_bad_wp_empty_pins())
        assert report.summary["failed"] >= 2  # pins + floor at minimum

    def test_summary_keys(self):
        report = evaluate_wp(_good_wp())
        assert "passed" in report.summary
        assert "failed" in report.summary
        assert "advisory" in report.summary
        assert "not_evaluable" in report.summary

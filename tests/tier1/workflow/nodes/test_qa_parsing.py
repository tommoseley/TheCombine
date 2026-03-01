"""Tests for QA parsing and validation pure functions -- WS-CRAP-001 Targets 2+4.

Tests extracted pure functions: strip_code_fences, try_parse_json_qa,
detect_pass_fail, extract_issues_from_text, parse_qa_response,
validate_semantic_qa_contract, convert_semantic_findings_to_feedback,
build_qa_success_metadata.
"""

import json
import os
import sys
import types

# Stub the workflow package to avoid circular import through __init__.py
# (pre-existing circular: workflow.__init__ -> plan_executor -> api routers -> plan_executor)
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.qa_parsing import (  # noqa: E402
    strip_code_fences,
    try_parse_json_qa,
    detect_pass_fail,
    extract_issues_from_text,
    parse_qa_response,
    validate_semantic_qa_contract,
    convert_semantic_findings_to_feedback,
    build_qa_success_metadata,
)


# =========================================================================
# strip_code_fences
# =========================================================================


class TestStripCodeFences:
    """Tests for strip_code_fences pure function."""

    def test_json_fence(self):
        text = '```json\n{"passed": true}\n```'
        assert strip_code_fences(text) == '{"passed": true}'

    def test_plain_fence(self):
        text = "```\nsome content\n```"
        assert strip_code_fences(text) == "some content"

    def test_no_fences(self):
        text = '{"passed": true}'
        assert strip_code_fences(text) == '{"passed": true}'

    def test_whitespace_stripping(self):
        text = "  ```json\n  content  \n```  "
        assert strip_code_fences(text) == "content"

    def test_empty_string(self):
        assert strip_code_fences("") == ""

    def test_only_fences(self):
        assert strip_code_fences("```json\n```") == ""

    def test_nested_backticks_preserved(self):
        text = '```json\n{"code": "```"}\n```'
        # Inner backticks are part of the JSON value
        result = strip_code_fences(text)
        assert '"code": "' in result


# =========================================================================
# try_parse_json_qa
# =========================================================================


class TestTryParseJsonQa:
    """Tests for try_parse_json_qa pure function."""

    def test_valid_json_passed(self):
        text = json.dumps({"passed": True, "issues": [], "summary": "All good"})
        result = try_parse_json_qa(text)
        assert result is not None
        assert result["passed"] is True
        assert result["issues"] == []
        assert result["feedback"] == "All good"

    def test_valid_json_failed(self):
        text = json.dumps({
            "passed": False,
            "issues": ["Missing field X"],
            "summary": "Needs work",
        })
        result = try_parse_json_qa(text)
        assert result is not None
        assert result["passed"] is False
        assert result["issues"] == ["Missing field X"]

    def test_json_with_code_fences(self):
        inner = json.dumps({"passed": True, "issues": []})
        text = f"```json\n{inner}\n```"
        result = try_parse_json_qa(text)
        assert result is not None
        assert result["passed"] is True

    def test_dict_issues_normalized(self):
        text = json.dumps({
            "passed": False,
            "issues": [
                {"message": "Issue 1", "severity": "error"},
                {"message": "Issue 2", "severity": "warning"},
            ],
        })
        result = try_parse_json_qa(text)
        assert result["issues"] == ["Issue 1", "Issue 2"]

    def test_dict_issues_without_message_key(self):
        text = json.dumps({
            "passed": False,
            "issues": [{"severity": "error", "detail": "bad"}],
        })
        result = try_parse_json_qa(text)
        # Falls back to str(issue)
        assert len(result["issues"]) == 1
        assert "severity" in result["issues"][0]

    def test_missing_passed_key(self):
        text = json.dumps({"result": "pass", "issues": []})
        assert try_parse_json_qa(text) is None

    def test_not_a_dict(self):
        text = json.dumps([1, 2, 3])
        assert try_parse_json_qa(text) is None

    def test_invalid_json(self):
        assert try_parse_json_qa("not json at all") is None

    def test_empty_string(self):
        assert try_parse_json_qa("") is None

    def test_passed_truthy_values(self):
        text = json.dumps({"passed": 1})
        result = try_parse_json_qa(text)
        assert result["passed"] is True

    def test_passed_falsy_values(self):
        text = json.dumps({"passed": 0})
        result = try_parse_json_qa(text)
        assert result["passed"] is False

    def test_no_summary_uses_original(self):
        original = json.dumps({"passed": True, "issues": []})
        result = try_parse_json_qa(original)
        assert result["feedback"] == original

    def test_empty_summary_uses_original(self):
        original = json.dumps({"passed": True, "issues": [], "summary": ""})
        result = try_parse_json_qa(original)
        assert result["feedback"] == original


# =========================================================================
# detect_pass_fail
# =========================================================================


class TestDetectPassFail:
    """Tests for detect_pass_fail pure function."""

    def test_explicit_result_pass_no_bold(self):
        assert detect_pass_fail("Result: pass") is True

    def test_explicit_result_fail_no_bold(self):
        assert detect_pass_fail("Result: fail") is False

    def test_result_colon_outside_bold(self):
        # **Result**: PASS (colon outside bold markers) -> regex matches
        assert detect_pass_fail("**Result**: PASS") is True
        assert detect_pass_fail("**Result**: FAIL") is False

    def test_result_colon_inside_bold_falls_through(self):
        # **Result:** PASS (colon inside bold markers) -> regex doesn't match,
        # falls through to keyword heuristics or ambiguous default.
        # This is preserved behavior from the original code.
        assert detect_pass_fail("**Result:** PASS\nAll good.") is True  # ambiguous default
        assert detect_pass_fail("**Result:** FAIL\nNeeds work.") is True  # ambiguous default

    def test_keyword_passes_all(self):
        assert detect_pass_fail("The document passes all quality checks.") is True

    def test_keyword_meets_requirements(self):
        assert detect_pass_fail("This meets requirements for delivery.") is True

    def test_keyword_approved(self):
        assert detect_pass_fail("Document approved for next stage.") is True

    def test_keyword_no_issues_found(self):
        assert detect_pass_fail("No issues found in review.") is True

    def test_keyword_quality_pass(self):
        assert detect_pass_fail("Quality: pass") is True

    def test_keyword_fails(self):
        assert detect_pass_fail("The document fails quality standards.") is False

    def test_keyword_issues_found(self):
        assert detect_pass_fail("Several issues found in the document.") is False

    def test_keyword_rejected(self):
        assert detect_pass_fail("Document rejected due to errors.") is False

    def test_keyword_needs_revision(self):
        assert detect_pass_fail("This needs revision before approval.") is False

    def test_keyword_quality_fail(self):
        assert detect_pass_fail("Quality: fail") is False

    def test_ambiguous_defaults_to_pass(self):
        assert detect_pass_fail("The document looks reasonable overall.") is True

    def test_empty_string_defaults_to_pass(self):
        assert detect_pass_fail("") is True

    def test_case_insensitive(self):
        assert detect_pass_fail("Result: PASS") is True
        assert detect_pass_fail("Result: FAIL") is False

    def test_result_takes_priority_over_keywords(self):
        # Even though "issues found" is present, explicit Result: PASS wins
        assert detect_pass_fail("Result: pass\nSome issues found but minor.") is True


# =========================================================================
# extract_issues_from_text
# =========================================================================


class TestExtractIssuesFromText:
    """Tests for extract_issues_from_text pure function."""

    def test_issues_section_with_bullets(self):
        text = "### Issues\n- Missing required field\n- Incomplete description\n"
        result = extract_issues_from_text(text)
        assert len(result) == 2
        assert "Missing required field" in result[0]

    def test_issues_found_section(self):
        text = "issues found:\n- First issue here\n- Second issue here\n"
        result = extract_issues_from_text(text)
        assert len(result) == 2

    def test_asterisk_bullets(self):
        text = "### Issues\n* Missing data model\n* No API spec\n"
        result = extract_issues_from_text(text)
        assert len(result) == 2

    def test_short_lines_skipped(self):
        text = "### Issues\n- OK\n- This is a real issue with details\n"
        result = extract_issues_from_text(text)
        assert len(result) == 1
        assert "real issue" in result[0]

    def test_no_issues_section(self):
        text = "Everything looks good. No problems detected."
        assert extract_issues_from_text(text) == []

    def test_empty_string(self):
        assert extract_issues_from_text("") == []

    def test_max_10_lines(self):
        lines = "\n".join([f"- Issue number {i} with enough detail" for i in range(20)])
        text = f"### Issues\n{lines}"
        result = extract_issues_from_text(text)
        assert len(result) <= 9  # Lines [1:10] = 9 max

    def test_bracket_bullets(self):
        text = "### Issues\n[1] Missing required field name\n[2] Invalid format here\n"
        result = extract_issues_from_text(text)
        assert len(result) == 2

    def test_non_bullet_lines_skipped(self):
        text = "### Issues\nSome preamble text\n- Real issue with details\nAnother line\n"
        result = extract_issues_from_text(text)
        assert len(result) == 1


# =========================================================================
# parse_qa_response (integration of all above)
# =========================================================================


class TestParseQaResponse:
    """Tests for parse_qa_response top-level function."""

    def test_json_response_passed(self):
        response = json.dumps({"passed": True, "issues": [], "summary": "OK"})
        result = parse_qa_response(response)
        assert result["passed"] is True
        assert result["issues"] == []

    def test_json_response_failed(self):
        response = json.dumps({
            "passed": False,
            "issues": ["Bad field"],
            "summary": "Needs work",
        })
        result = parse_qa_response(response)
        assert result["passed"] is False
        assert result["issues"] == ["Bad field"]

    def test_json_with_fences(self):
        inner = json.dumps({"passed": True, "issues": []})
        response = f"```json\n{inner}\n```"
        result = parse_qa_response(response)
        assert result["passed"] is True

    def test_text_response_pass(self):
        response = "The document passes all quality checks.\nNo issues found."
        result = parse_qa_response(response)
        assert result["passed"] is True
        assert result["issues"] == []

    def test_text_response_fail_with_issues(self):
        # Use "Result: FAIL" (colon outside bold) for reliable regex match
        response = (
            "Result: FAIL\n\n"
            "### Issues\n"
            "- Missing required field 'project_name'\n"
            "- Incomplete risk assessment section\n"
        )
        result = parse_qa_response(response)
        assert result["passed"] is False
        assert len(result["issues"]) == 2

    def test_text_response_fail_via_keyword(self):
        response = "The document fails quality checks.\nNeeds revision."
        result = parse_qa_response(response)
        assert result["passed"] is False

    def test_text_response_fail_no_issues_section(self):
        response = "Result: FAIL\nThe document needs work."
        result = parse_qa_response(response)
        assert result["passed"] is False
        assert result["issues"] == []

    def test_ambiguous_text_defaults_pass(self):
        response = "The document has some interesting points."
        result = parse_qa_response(response)
        assert result["passed"] is True

    def test_feedback_preserved(self):
        response = "**Result:** PASS\nGood work overall."
        result = parse_qa_response(response)
        assert result["feedback"] == response

    def test_json_takes_priority_over_text(self):
        # JSON says pass even though text contains fail keywords
        response = json.dumps({
            "passed": True,
            "issues": [],
            "summary": "fails to disappoint",
        })
        result = parse_qa_response(response)
        assert result["passed"] is True


# =========================================================================
# validate_semantic_qa_contract (Target 2)
# =========================================================================


class TestValidateSemanticQaContract:
    """Tests for validate_semantic_qa_contract pure function."""

    def _make_report(self, **overrides):
        base = {
            "gate": "pass",
            "coverage": {
                "expected_count": 2,
                "evaluated_count": 2,
                "items": [
                    {"constraint_id": "C1", "status": "compliant"},
                    {"constraint_id": "C2", "status": "compliant"},
                ],
            },
            "findings": [],
            "summary": {"errors": 0, "warnings": 0, "infos": 0},
        }
        base.update(overrides)
        return base

    def test_valid_report_no_warnings(self):
        report = self._make_report()
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert warnings == []

    def test_coverage_count_mismatch(self):
        report = self._make_report()
        warnings = validate_semantic_qa_contract(report, 3, ["C1", "C2", "C3"])
        assert any("expected_count mismatch" in w for w in warnings)

    def test_unknown_constraint_id_in_coverage(self):
        report = self._make_report()
        report["coverage"]["items"].append({"constraint_id": "UNKNOWN", "status": "compliant"})
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert any("Unknown constraint_id in coverage" in w for w in warnings)

    def test_unknown_constraint_id_in_findings(self):
        report = self._make_report()
        report["findings"] = [{"constraint_id": "BOGUS", "severity": "error", "message": "bad"}]
        report["summary"]["errors"] = 1
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert any("Unknown constraint_id in findings" in w for w in warnings)

    def test_system_id_allowed(self):
        report = self._make_report()
        report["coverage"]["items"].append({"constraint_id": "SYSTEM", "status": "compliant"})
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert not any("SYSTEM" in w for w in warnings)

    def test_gate_should_be_fail_for_contradicted(self):
        report = self._make_report()
        report["coverage"]["items"][0]["status"] = "contradicted"
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert any("Gate should be 'fail'" in w for w in warnings)

    def test_gate_should_be_fail_for_reopened(self):
        report = self._make_report()
        report["coverage"]["items"][0]["status"] = "reopened"
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert any("Gate should be 'fail'" in w for w in warnings)

    def test_gate_fail_with_contradicted_no_warning(self):
        report = self._make_report(gate="fail")
        report["coverage"]["items"][0]["status"] = "contradicted"
        report["findings"] = [{"constraint_id": "C1", "severity": "error", "message": "bad"}]
        report["summary"]["errors"] = 1
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert not any("Gate should be" in w for w in warnings)

    def test_summary_errors_mismatch(self):
        report = self._make_report()
        report["findings"] = [{"constraint_id": "C1", "severity": "error", "message": "bad"}]
        # summary says 0 errors but there's 1
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert any("Summary errors mismatch" in w for w in warnings)

    def test_summary_warnings_mismatch(self):
        report = self._make_report()
        report["findings"] = [{"constraint_id": "C1", "severity": "warning", "message": "eh"}]
        # summary says 0 warnings but there's 1
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert any("Summary warnings mismatch" in w for w in warnings)

    def test_case_insensitive_constraint_ids(self):
        report = self._make_report()
        report["coverage"]["items"] = [
            {"constraint_id": "c1", "status": "compliant"},
            {"constraint_id": "c2", "status": "compliant"},
        ]
        warnings = validate_semantic_qa_contract(report, 2, ["C1", "C2"])
        assert not any("Unknown constraint_id" in w for w in warnings)

    def test_empty_report_has_structural_warnings(self):
        # Empty dict has None for coverage.expected_count, which != 0
        warnings = validate_semantic_qa_contract({}, 0, [])
        assert any("expected_count mismatch" in w for w in warnings)


# =========================================================================
# convert_semantic_findings_to_feedback (Target 2)
# =========================================================================


class TestConvertSemanticFindingsToFeedback:
    """Tests for convert_semantic_findings_to_feedback pure function."""

    def test_converts_findings(self):
        report = {
            "findings": [
                {
                    "code": "CONTRADICTION",
                    "severity": "error",
                    "message": "Violated constraint",
                    "constraint_id": "C1",
                    "evidence_pointers": ["$.field"],
                    "suggested_fix": "Remove the violation",
                },
            ]
        }
        result = convert_semantic_findings_to_feedback(report)
        assert len(result) == 1
        assert result[0]["type"] == "semantic_qa"
        assert result[0]["check_id"] == "CONTRADICTION"
        assert result[0]["severity"] == "error"
        assert result[0]["message"] == "Violated constraint"
        assert result[0]["constraint_id"] == "C1"
        assert result[0]["evidence_pointers"] == ["$.field"]
        assert result[0]["remediation"] == "Remove the violation"

    def test_multiple_findings(self):
        report = {
            "findings": [
                {"code": "A", "severity": "error", "message": "err1"},
                {"code": "B", "severity": "warning", "message": "warn1"},
            ]
        }
        result = convert_semantic_findings_to_feedback(report)
        assert len(result) == 2

    def test_empty_findings(self):
        result = convert_semantic_findings_to_feedback({"findings": []})
        assert result == []

    def test_no_findings_key(self):
        result = convert_semantic_findings_to_feedback({})
        assert result == []

    def test_missing_optional_fields(self):
        report = {
            "findings": [
                {"code": "X", "severity": "error", "message": "msg"},
            ]
        }
        result = convert_semantic_findings_to_feedback(report)
        assert result[0]["constraint_id"] is None
        assert result[0]["evidence_pointers"] == []
        assert result[0]["remediation"] is None


# =========================================================================
# build_qa_success_metadata (Target 2)
# =========================================================================


class TestBuildQaSuccessMetadata:
    """Tests for build_qa_success_metadata pure function."""

    def test_minimal(self):
        result = build_qa_success_metadata("qa_1", [], [], [], None)
        assert result == {"node_id": "qa_1", "qa_passed": True}

    def test_with_drift_warnings(self):
        result = build_qa_success_metadata("qa_1", [{"w": 1}], [], [], None)
        assert result["drift_warnings"] == [{"w": 1}]

    def test_with_code_warnings(self):
        result = build_qa_success_metadata("qa_1", [], [{"w": 2}], [], None)
        assert result["code_validation_warnings"] == [{"w": 2}]

    def test_with_semantic_warnings(self):
        result = build_qa_success_metadata("qa_1", [], [], [{"w": 3}], None)
        assert result["semantic_qa_warnings"] == [{"w": 3}]

    def test_with_semantic_report(self):
        report = {"gate": "pass", "findings": []}
        result = build_qa_success_metadata("qa_1", [], [], [], report)
        assert result["semantic_qa_report"] == report

    def test_all_populated(self):
        result = build_qa_success_metadata(
            "qa_1",
            [{"d": 1}],
            [{"c": 2}],
            [{"s": 3}],
            {"gate": "pass"},
        )
        assert "drift_warnings" in result
        assert "code_validation_warnings" in result
        assert "semantic_qa_warnings" in result
        assert "semantic_qa_report" in result
        assert result["qa_passed"] is True

    def test_empty_lists_not_included(self):
        result = build_qa_success_metadata("qa_1", [], [], [], None)
        assert "drift_warnings" not in result
        assert "code_validation_warnings" not in result
        assert "semantic_qa_warnings" not in result
        assert "semantic_qa_report" not in result

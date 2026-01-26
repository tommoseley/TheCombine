"""Tests for Layer 2 semantic QA validation.

Per WS-SEMANTIC-QA-001.
"""

import json
import logging
import pytest

from app.domain.workflow.nodes.qa import QANodeExecutor


class TestParseSemanticQAResponse:
    """Tests for _parse_semantic_qa_response method."""

    @pytest.fixture
    def executor(self):
        return QANodeExecutor()

    @pytest.fixture
    def valid_report(self):
        """A valid semantic QA report that passes all checks."""
        return {
            "schema_version": "qa_semantic_compliance_output.v1",
            "correlation_id": "test-correlation-123",
            "gate": "pass",
            "summary": {
                "errors": 0,
                "warnings": 0,
                "infos": 0,
                "expected_constraints": 2,
                "evaluated_constraints": 2,
                "blocked_reasons": [],
            },
            "coverage": {
                "expected_count": 2,
                "evaluated_count": 2,
                "items": [
                    {
                        "constraint_id": "PLATFORM_TARGET",
                        "status": "satisfied",
                        "evidence_pointers": ["$.known_constraints[0].constraint"],
                    },
                    {
                        "constraint_id": "OFFLINE_MODE",
                        "status": "satisfied",
                        "evidence_pointers": ["$.known_constraints[1].constraint"],
                    },
                ],
            },
            "findings": [],
        }

    @pytest.fixture
    def failing_report(self):
        """A semantic QA report with a contradiction."""
        return {
            "schema_version": "qa_semantic_compliance_output.v1",
            "correlation_id": "test-correlation-456",
            "gate": "fail",
            "summary": {
                "errors": 1,
                "warnings": 0,
                "infos": 0,
                "expected_constraints": 2,
                "evaluated_constraints": 2,
                "blocked_reasons": ["PLATFORM_TARGET constraint contradicted"],
            },
            "coverage": {
                "expected_count": 2,
                "evaluated_count": 2,
                "items": [
                    {
                        "constraint_id": "PLATFORM_TARGET",
                        "status": "contradicted",
                        "evidence_pointers": ["$.summary"],
                    },
                    {
                        "constraint_id": "OFFLINE_MODE",
                        "status": "satisfied",
                        "evidence_pointers": ["$.known_constraints[0].constraint"],
                    },
                ],
            },
            "findings": [
                {
                    "severity": "error",
                    "code": "BOUND_CONTRADICTION",
                    "constraint_id": "PLATFORM_TARGET",
                    "message": "Document states mobile but user selected web",
                    "evidence_pointers": ["$.summary"],
                    "suggested_fix": "Change platform to web browser",
                }
            ],
        }

    def test_parse_valid_json_response(self, executor, valid_report):
        """Valid JSON response should parse successfully."""
        response = json.dumps(valid_report)

        result = executor._parse_semantic_qa_response(
            response=response,
            expected_constraint_count=2,
            provided_constraint_ids=["PLATFORM_TARGET", "OFFLINE_MODE"],
        )

        assert result["gate"] == "pass"
        assert result["summary"]["errors"] == 0
        assert len(result["coverage"]["items"]) == 2

    def test_parse_json_with_markdown_fences(self, executor, valid_report):
        """JSON wrapped in markdown code fences should parse."""
        response = f"```json\n{json.dumps(valid_report)}\n```"

        result = executor._parse_semantic_qa_response(
            response=response,
            expected_constraint_count=2,
            provided_constraint_ids=["PLATFORM_TARGET", "OFFLINE_MODE"],
        )

        assert result["gate"] == "pass"

    def test_parse_invalid_json_raises(self, executor):
        """Invalid JSON should raise ValueError."""
        response = "This is not valid JSON"

        with pytest.raises(ValueError) as excinfo:
            executor._parse_semantic_qa_response(
                response=response,
                expected_constraint_count=1,
                provided_constraint_ids=["TEST"],
            )

        assert "Invalid JSON" in str(excinfo.value)

    def test_parse_missing_required_fields_raises(self, executor):
        """JSON missing required schema fields should raise ValueError."""
        # Missing 'gate' field
        incomplete = {
            "schema_version": "qa_semantic_compliance_output.v1",
            "correlation_id": "test",
            "summary": {"errors": 0, "warnings": 0, "infos": 0},
        }
        response = json.dumps(incomplete)

        with pytest.raises(ValueError) as excinfo:
            executor._parse_semantic_qa_response(
                response=response,
                expected_constraint_count=0,
                provided_constraint_ids=[],
            )

        assert "Schema validation failed" in str(excinfo.value)

    def test_parse_wrong_schema_version_raises(self, executor, valid_report):
        """Wrong schema version should raise ValueError."""
        valid_report["schema_version"] = "wrong_version"
        response = json.dumps(valid_report)

        with pytest.raises(ValueError) as excinfo:
            executor._parse_semantic_qa_response(
                response=response,
                expected_constraint_count=2,
                provided_constraint_ids=["PLATFORM_TARGET", "OFFLINE_MODE"],
            )

        assert "Schema validation failed" in str(excinfo.value)


class TestValidateSemanticQAContract:
    """Tests for _validate_semantic_qa_contract method."""

    @pytest.fixture
    def executor(self):
        return QANodeExecutor()

    def test_valid_contract_passes(self, executor):
        """Valid report should pass contract validation."""
        report = {
            "gate": "pass",
            "summary": {"errors": 0, "warnings": 1},
            "coverage": {
                "expected_count": 2,
                "evaluated_count": 2,
                "items": [
                    {"constraint_id": "C1", "status": "satisfied"},
                    {"constraint_id": "C2", "status": "satisfied"},
                ],
            },
            "findings": [
                {"severity": "warning", "constraint_id": "C1", "code": "TRACEABILITY_GAP"}
            ],
        }

        # Should not raise
        executor._validate_semantic_qa_contract(
            report=report,
            expected_constraint_count=2,
            provided_constraint_ids=["C1", "C2"],
        )

    def test_contradicted_status_requires_fail_gate(self, executor, caplog):
        """Contradicted status should log warning if gate is not 'fail'."""
        caplog.set_level(logging.WARNING)
        report = {
            "gate": "pass",  # Incorrect - should be fail
            "summary": {"errors": 1, "warnings": 0},
            "coverage": {
                "expected_count": 1,
                "evaluated_count": 1,
                "items": [
                    {"constraint_id": "C1", "status": "contradicted"},
                ],
            },
            "findings": [{"severity": "error", "constraint_id": "C1", "code": "BOUND_CONTRADICTION"}],
        }

        executor._validate_semantic_qa_contract(
            report=report,
            expected_constraint_count=1,
            provided_constraint_ids=["C1"],
        )

        assert "Gate should be 'fail'" in caplog.text

    def test_reopened_status_requires_fail_gate(self, executor, caplog):
        """Reopened status should log warning if gate is not 'fail'."""
        caplog.set_level(logging.WARNING)
        report = {
            "gate": "pass",  # Incorrect - should be fail
            "summary": {"errors": 1, "warnings": 0},
            "coverage": {
                "expected_count": 1,
                "evaluated_count": 1,
                "items": [
                    {"constraint_id": "C1", "status": "reopened"},
                ],
            },
            "findings": [{"severity": "error", "constraint_id": "C1", "code": "BOUND_REOPENED"}],
        }

        executor._validate_semantic_qa_contract(
            report=report,
            expected_constraint_count=1,
            provided_constraint_ids=["C1"],
        )

        assert "Gate should be 'fail'" in caplog.text

    def test_unknown_constraint_id_logs_warning(self, executor, caplog):
        """Unknown constraint IDs should log warnings."""
        caplog.set_level(logging.WARNING)
        report = {
            "gate": "pass",
            "summary": {"errors": 0, "warnings": 0},
            "coverage": {
                "expected_count": 1,
                "evaluated_count": 1,
                "items": [
                    {"constraint_id": "UNKNOWN_ID", "status": "satisfied"},
                ],
            },
            "findings": [],
        }

        executor._validate_semantic_qa_contract(
            report=report,
            expected_constraint_count=1,
            provided_constraint_ids=["C1"],  # UNKNOWN_ID not in this list
        )

        assert "Unknown constraint_id in coverage" in caplog.text

    def test_summary_count_mismatch_logs_warning(self, executor, caplog):
        """Mismatched summary counts should log warnings."""
        caplog.set_level(logging.WARNING)
        report = {
            "gate": "pass",
            "summary": {"errors": 5, "warnings": 3},  # Doesn't match findings
            "coverage": {
                "expected_count": 1,
                "evaluated_count": 1,
                "items": [{"constraint_id": "C1", "status": "satisfied"}],
            },
            "findings": [],  # 0 errors, not 5
        }

        executor._validate_semantic_qa_contract(
            report=report,
            expected_constraint_count=1,
            provided_constraint_ids=["C1"],
        )

        assert "Summary errors mismatch" in caplog.text


class TestConvertSemanticFindingsToFeedback:
    """Tests for _convert_semantic_findings_to_feedback method."""

    @pytest.fixture
    def executor(self):
        return QANodeExecutor()

    def test_convert_findings_to_feedback(self, executor):
        """Findings should be converted to feedback format."""
        report = {
            "findings": [
                {
                    "severity": "error",
                    "code": "BOUND_CONTRADICTION",
                    "constraint_id": "PLATFORM_TARGET",
                    "message": "Document states mobile but user selected web",
                    "evidence_pointers": ["$.summary", "$.assumptions[0]"],
                    "suggested_fix": "Change platform to web",
                },
                {
                    "severity": "warning",
                    "code": "TRACEABILITY_GAP",
                    "constraint_id": "OFFLINE_MODE",
                    "message": "Cannot verify offline mode constraint",
                    "evidence_pointers": ["$.known_constraints"],
                },
            ]
        }

        feedback = executor._convert_semantic_findings_to_feedback(report)

        assert len(feedback) == 2

        # First finding
        assert feedback[0]["type"] == "semantic_qa"
        assert feedback[0]["check_id"] == "BOUND_CONTRADICTION"
        assert feedback[0]["severity"] == "error"
        assert feedback[0]["constraint_id"] == "PLATFORM_TARGET"
        assert feedback[0]["message"] == "Document states mobile but user selected web"
        assert feedback[0]["evidence_pointers"] == ["$.summary", "$.assumptions[0]"]
        assert feedback[0]["remediation"] == "Change platform to web"

        # Second finding
        assert feedback[1]["type"] == "semantic_qa"
        assert feedback[1]["check_id"] == "TRACEABILITY_GAP"
        assert feedback[1]["severity"] == "warning"

    def test_empty_findings_returns_empty_list(self, executor):
        """Empty findings should return empty list."""
        report = {"findings": []}

        feedback = executor._convert_semantic_findings_to_feedback(report)

        assert feedback == []

    def test_missing_optional_fields_handled(self, executor):
        """Missing optional fields should be handled gracefully."""
        report = {
            "findings": [
                {
                    "severity": "error",
                    "code": "OTHER",
                    "constraint_id": "C1",
                    "message": "Issue found",
                    "evidence_pointers": ["$.summary"],
                    # No suggested_fix
                }
            ]
        }

        feedback = executor._convert_semantic_findings_to_feedback(report)

        assert len(feedback) == 1
        assert feedback[0]["remediation"] is None


class TestBuildSemanticQAContext:
    """Tests for _build_semantic_qa_context method."""

    @pytest.fixture
    def executor(self):
        return QANodeExecutor()

    def test_builds_context_with_all_inputs(self, executor, tmp_path, monkeypatch):
        """Context should include all inputs properly formatted."""
        # Mock the policy prompt file
        policy_path = tmp_path / "seed" / "prompts" / "tasks"
        policy_path.mkdir(parents=True)
        (policy_path / "qa_semantic_compliance_v1.0.txt").write_text("# Test Policy")

        # Monkeypatch Path to use our temp path
        import app.domain.workflow.nodes.qa as qa_module
        original_path = qa_module.Path

        def mock_path_init(*args, **kwargs):
            if args and "qa_semantic_compliance_v1.0.txt" in str(args[0]):
                return policy_path / "qa_semantic_compliance_v1.0.txt"
            return original_path(*args, **kwargs)

        # Build context
        pgc_questions = [
            {"id": "Q1", "text": "Platform?", "priority": "must"},
        ]
        pgc_answers = {"Q1": {"label": "Web browser"}}
        invariants = [
            {"id": "C1", "invariant_kind": "requirement", "normalized_text": "Web platform"},
        ]
        document = {"summary": "Test document"}

        context = executor._build_semantic_qa_context(
            pgc_questions=pgc_questions,
            pgc_answers=pgc_answers,
            invariants=invariants,
            document=document,
            correlation_id="test-123",
        )

        # Check all sections are present
        assert "PGC Questions and Answers" in context
        assert "Q1 (priority=must): Web browser" in context
        assert "Bound Constraints (MUST evaluate each)" in context
        assert "C1 [requirement]: Web platform" in context
        assert "Generated Document" in context
        assert '"summary": "Test document"' in context
        assert "correlation_id for output: test-123" in context


class TestSemanticQAIntegration:
    """Integration tests for semantic QA flow."""

    @pytest.fixture
    def executor(self):
        return QANodeExecutor()

    def test_gate_pass_all_satisfied(self, executor):
        """Gate pass when all constraints satisfied."""
        report_json = json.dumps({
            "schema_version": "qa_semantic_compliance_output.v1",
            "correlation_id": "test-123",
            "gate": "pass",
            "summary": {
                "errors": 0,
                "warnings": 0,
                "infos": 0,
                "expected_constraints": 2,
                "evaluated_constraints": 2,
                "blocked_reasons": [],
            },
            "coverage": {
                "expected_count": 2,
                "evaluated_count": 2,
                "items": [
                    {"constraint_id": "C1", "status": "satisfied", "evidence_pointers": ["$.summary"]},
                    {"constraint_id": "C2", "status": "satisfied", "evidence_pointers": ["$.summary"]},
                ],
            },
            "findings": [],
        })

        result = executor._parse_semantic_qa_response(
            response=report_json,
            expected_constraint_count=2,
            provided_constraint_ids=["C1", "C2"],
        )

        assert result["gate"] == "pass"
        assert result["summary"]["errors"] == 0

    def test_gate_fail_on_contradiction(self, executor):
        """Gate should fail when constraint is contradicted."""
        report_json = json.dumps({
            "schema_version": "qa_semantic_compliance_output.v1",
            "correlation_id": "test-456",
            "gate": "fail",
            "summary": {
                "errors": 1,
                "warnings": 0,
                "infos": 0,
                "expected_constraints": 1,
                "evaluated_constraints": 1,
                "blocked_reasons": ["Constraint C1 contradicted"],
            },
            "coverage": {
                "expected_count": 1,
                "evaluated_count": 1,
                "items": [
                    {"constraint_id": "C1", "status": "contradicted", "evidence_pointers": ["$.summary"]},
                ],
            },
            "findings": [
                {
                    "severity": "error",
                    "code": "BOUND_CONTRADICTION",
                    "constraint_id": "C1",
                    "message": "Constraint violated",
                    "evidence_pointers": ["$.summary"],
                }
            ],
        })

        result = executor._parse_semantic_qa_response(
            response=report_json,
            expected_constraint_count=1,
            provided_constraint_ids=["C1"],
        )

        assert result["gate"] == "fail"
        assert result["summary"]["errors"] == 1
        assert result["coverage"]["items"][0]["status"] == "contradicted"

    def test_coverage_count_validation(self, executor, caplog):
        """Coverage count mismatch should log warning."""
        caplog.set_level(logging.WARNING)
        report_json = json.dumps({
            "schema_version": "qa_semantic_compliance_output.v1",
            "correlation_id": "test-789",
            "gate": "pass",
            "summary": {
                "errors": 0,
                "warnings": 0,
                "infos": 0,
                "expected_constraints": 3,  # Says 3, but only 2 provided
                "evaluated_constraints": 2,
                "blocked_reasons": [],
            },
            "coverage": {
                "expected_count": 3,  # Mismatch with actual provided count
                "evaluated_count": 2,
                "items": [
                    {"constraint_id": "C1", "status": "satisfied", "evidence_pointers": []},
                    {"constraint_id": "C2", "status": "satisfied", "evidence_pointers": []},
                ],
            },
            "findings": [],
        })

        result = executor._parse_semantic_qa_response(
            response=report_json,
            expected_constraint_count=2,  # Actual count is 2
            provided_constraint_ids=["C1", "C2"],
        )

        # Should still parse, but log warning
        assert result is not None
        assert "Coverage expected_count mismatch" in caplog.text

"""Tests for QANodeExecutor.execute decomposition -- WS-CRAP-010.

Tests the 5 extracted check methods:
  _check_drift_validation (4 tests)
  _check_code_validation (4 tests)
  _check_schema_validation (3 tests)
  _check_semantic_qa (5 tests)
  _check_llm_qa (4 tests)
"""

import os
import sys
import types
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub the workflow package to avoid circular import through __init__.py
# (pre-existing circular: workflow.__init__ -> plan_executor -> api routers -> plan_executor)
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.base import (  # noqa: E402
    DocumentWorkflowContext,
    NodeResult,
)
from app.domain.workflow.nodes.qa import QANodeExecutor  # noqa: E402
from app.domain.workflow.validation.validation_result import (  # noqa: E402
    DriftValidationResult,
    DriftViolation,
    PromotionValidationResult,
    ValidationIssue,
)


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def executor():
    """QANodeExecutor with no dependencies (for non-LLM checks)."""
    return QANodeExecutor()


@pytest.fixture
def executor_with_schema():
    """QANodeExecutor with a mock schema validator."""
    mock_validator = MagicMock()
    return QANodeExecutor(schema_validator=mock_validator)


@pytest.fixture
def executor_with_llm():
    """QANodeExecutor with mock LLM service and prompt loader."""
    mock_llm = AsyncMock()
    mock_prompt = MagicMock()
    return QANodeExecutor(llm_service=mock_llm, prompt_loader=mock_prompt)


@pytest.fixture
def base_context():
    """Minimal DocumentWorkflowContext for testing."""
    return DocumentWorkflowContext(
        project_id="proj-1",
        document_type="test_doc",
    )


@pytest.fixture
def sample_document():
    return {"title": "Test Document", "constraints": ["C1", "C2"]}


# =========================================================================
# _check_drift_validation (4 tests)
# =========================================================================


class TestCheckDriftValidation:
    """Tests for _check_drift_validation extracted method."""

    def test_no_drift_data_returns_none_empty(self, executor, sample_document, base_context):
        """When _run_drift_validation returns None, check returns (None, [])."""
        with patch.object(executor, "_run_drift_validation", return_value=None):
            result, warnings = executor._check_drift_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is None
        assert warnings == []

    def test_drift_passed_no_warnings(self, executor, sample_document, base_context):
        """When drift passes with no warnings, returns (None, [])."""
        drift_result = DriftValidationResult(passed=True, violations=[])
        with patch.object(executor, "_run_drift_validation", return_value=drift_result):
            result, warnings = executor._check_drift_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is None
        assert warnings == []

    def test_drift_passed_with_warnings(self, executor, sample_document, base_context):
        """When drift passes with warnings, returns (None, [warning_dicts])."""
        warn_violation = DriftViolation(
            check_id="QA-PGC-003",
            severity="WARNING",
            clarification_id="c1",
            message="Omitted constraint",
        )
        drift_result = DriftValidationResult(passed=True, violations=[warn_violation])
        with patch.object(executor, "_run_drift_validation", return_value=drift_result):
            result, warnings = executor._check_drift_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is None
        assert len(warnings) == 1
        assert warnings[0]["check_id"] == "QA-PGC-003"

    def test_drift_failed_returns_node_result(self, executor, sample_document, base_context):
        """When drift fails, returns (NodeResult(failed), [])."""
        error_violation = DriftViolation(
            check_id="QA-PGC-001",
            severity="ERROR",
            clarification_id="c1",
            message="Contradicted constraint",
        )
        drift_result = DriftValidationResult(passed=False, violations=[error_violation])
        with patch.object(executor, "_run_drift_validation", return_value=drift_result):
            result, warnings = executor._check_drift_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is not None
        assert result.outcome == "failed"
        assert result.metadata["validation_source"] == "constraint_drift"
        assert len(result.metadata["drift_errors"]) == 1
        assert warnings == []


# =========================================================================
# _check_code_validation (4 tests)
# =========================================================================


class TestCheckCodeValidation:
    """Tests for _check_code_validation extracted method."""

    def test_no_pgc_data_returns_none_empty(self, executor, sample_document, base_context):
        """When _run_code_based_validation returns None, check returns (None, [])."""
        with patch.object(executor, "_run_code_based_validation", return_value=None):
            result, warnings = executor._check_code_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is None
        assert warnings == []

    def test_validation_passed_no_warnings(self, executor, sample_document, base_context):
        """When validation passes with no warnings, returns (None, [])."""
        val_result = PromotionValidationResult(passed=True, issues=[])
        with patch.object(executor, "_run_code_based_validation", return_value=val_result):
            result, warnings = executor._check_code_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is None
        assert warnings == []

    def test_validation_passed_with_warnings(self, executor, sample_document, base_context):
        """When validation passes with warnings, returns (None, [warning_dicts])."""
        warn_issue = ValidationIssue(
            severity="warning",
            check_type="grounding",
            section="guardrails",
            message="Not fully traceable",
            evidence={"source": "test"},
        )
        val_result = PromotionValidationResult(passed=True, issues=[warn_issue])
        with patch.object(executor, "_run_code_based_validation", return_value=val_result):
            result, warnings = executor._check_code_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is None
        assert len(warnings) == 1
        assert warnings[0]["message"] == "Not fully traceable"

    def test_validation_failed_returns_node_result(self, executor, sample_document, base_context):
        """When validation fails, returns (NodeResult(failed), [])."""
        error_issue = ValidationIssue(
            severity="error",
            check_type="promotion",
            section="constraints",
            message="Should-answer promoted",
            evidence={"question": "q1"},
        )
        val_result = PromotionValidationResult(passed=False, issues=[error_issue])
        with patch.object(executor, "_run_code_based_validation", return_value=val_result):
            result, warnings = executor._check_code_validation(
                document=sample_document, context=base_context, node_id="qa-1",
            )
        assert result is not None
        assert result.outcome == "failed"
        assert result.metadata["validation_source"] == "code_based"
        assert len(result.metadata["validation_errors"]) == 1
        assert warnings == []


# =========================================================================
# _check_schema_validation (3 tests)
# =========================================================================


class TestCheckSchemaValidation:
    """Tests for _check_schema_validation extracted method."""

    def test_no_schema_ref_no_action(self, executor, sample_document):
        """When schema_ref is None, no errors are appended."""
        errors = []
        feedback = {}
        executor._check_schema_validation(
            document=sample_document, schema_ref=None, errors=errors, feedback=feedback,
        )
        assert errors == []
        assert feedback == {}

    def test_schema_valid_no_errors(self, executor_with_schema, sample_document):
        """When schema validates, no errors are appended."""
        executor_with_schema.schema_validator.validate.return_value = (True, [])
        errors = []
        feedback = {}
        executor_with_schema._check_schema_validation(
            document=sample_document, schema_ref="test.schema.json",
            errors=errors, feedback=feedback,
        )
        assert errors == []
        assert "schema_errors" not in feedback

    def test_schema_invalid_extends_errors(self, executor_with_schema, sample_document):
        """When schema fails, errors and feedback are populated."""
        schema_errs = ["Missing required field 'title'", "Invalid type for 'count'"]
        executor_with_schema.schema_validator.validate.return_value = (False, schema_errs)
        errors = []
        feedback = {}
        executor_with_schema._check_schema_validation(
            document=sample_document, schema_ref="test.schema.json",
            errors=errors, feedback=feedback,
        )
        assert len(errors) == 2
        assert feedback["schema_errors"] == schema_errs


# =========================================================================
# _check_semantic_qa (5 tests)
# =========================================================================


class TestCheckSemanticQA:
    """Tests for _check_semantic_qa extracted method."""

    @pytest.mark.asyncio
    async def test_no_semantic_data_returns_none(self, executor, sample_document, base_context):
        """When _run_semantic_qa returns None, check returns (None, [], None)."""
        with patch.object(executor, "_run_semantic_qa", new_callable=AsyncMock, return_value=None):
            result, warnings, report = await executor._check_semantic_qa(
                node_id="qa-1", document=sample_document, context=base_context, errors=[],
            )
        assert result is None
        assert warnings == []
        assert report is None

    @pytest.mark.asyncio
    async def test_semantic_passed_no_warnings(self, executor, sample_document, base_context):
        """When semantic QA passes with no warning-level findings, returns (None, [], report)."""
        report_data = {"gate": "pass", "findings": []}
        with patch.object(executor, "_run_semantic_qa", new_callable=AsyncMock, return_value=report_data):
            result, warnings, report = await executor._check_semantic_qa(
                node_id="qa-1", document=sample_document, context=base_context, errors=[],
            )
        assert result is None
        assert warnings == []
        assert report == report_data

    @pytest.mark.asyncio
    async def test_semantic_passed_with_warnings(self, executor, sample_document, base_context):
        """When semantic QA passes with warning findings, returns (None, [findings], report)."""
        report_data = {
            "gate": "pass",
            "findings": [
                {"severity": "warning", "message": "Minor issue"},
                {"severity": "info", "message": "FYI note"},
                {"severity": "error", "message": "Should not appear in pass"},
            ],
        }
        with patch.object(executor, "_run_semantic_qa", new_callable=AsyncMock, return_value=report_data):
            result, warnings, report = await executor._check_semantic_qa(
                node_id="qa-1", document=sample_document, context=base_context, errors=[],
            )
        assert result is None
        # Only warning and info findings are collected
        assert len(warnings) == 2
        assert report == report_data

    @pytest.mark.asyncio
    async def test_semantic_failed_returns_node_result(self, executor, sample_document, base_context):
        """When semantic QA gate is 'fail', returns (NodeResult(failed), [], report)."""
        report_data = {
            "gate": "fail",
            "findings": [
                {"severity": "error", "message": "Contradicted constraint C1"},
            ],
        }
        # _convert_semantic_findings_to_feedback returns feedback items
        with patch.object(executor, "_run_semantic_qa", new_callable=AsyncMock, return_value=report_data):
            with patch.object(
                executor,
                "_convert_semantic_findings_to_feedback",
                return_value=[{"severity": "error", "message": "Contradicted constraint C1"}],
            ):
                result, warnings, report = await executor._check_semantic_qa(
                    node_id="qa-1", document=sample_document, context=base_context, errors=[],
                )
        assert result is not None
        assert result.outcome == "failed"
        assert result.metadata["validation_source"] == "semantic_qa"
        assert "semantic_qa_report" in result.metadata
        assert warnings == []

    @pytest.mark.asyncio
    async def test_semantic_value_error_appends_to_errors(self, executor, sample_document, base_context):
        """When _run_semantic_qa raises ValueError, error is appended to errors list."""
        with patch.object(
            executor, "_run_semantic_qa", new_callable=AsyncMock,
            side_effect=ValueError("Schema validation failed"),
        ):
            errors = []
            result, warnings, report = await executor._check_semantic_qa(
                node_id="qa-1", document=sample_document, context=base_context, errors=errors,
            )
        assert result is None
        assert warnings == []
        assert report is None
        assert len(errors) == 1
        assert "Semantic QA validation error" in errors[0]


# =========================================================================
# _check_llm_qa (4 tests)
# =========================================================================


class TestCheckLLMQA:
    """Tests for _check_llm_qa extracted method."""

    @pytest.mark.asyncio
    async def test_no_task_ref_no_action(self, executor, sample_document, base_context):
        """When task_ref is missing, no LLM QA runs."""
        errors = []
        feedback = {}
        node_config = {"qa_mode": "structural"}  # no task_ref
        await executor._check_llm_qa(
            node_id="qa-1", node_config=node_config,
            document=sample_document, context=base_context,
            errors=errors, feedback=feedback,
        )
        assert errors == []
        assert feedback == {}

    @pytest.mark.asyncio
    async def test_llm_qa_passed(self, executor_with_llm, sample_document, base_context):
        """When LLM QA passes, no errors appended."""
        node_config = {"task_ref": "qa_task_v1", "qa_mode": "structural"}
        with patch.object(
            executor_with_llm, "_run_llm_qa", new_callable=AsyncMock,
            return_value={"passed": True, "issues": [], "feedback": "Looks good"},
        ):
            errors = []
            feedback = {}
            await executor_with_llm._check_llm_qa(
                node_id="qa-1", node_config=node_config,
                document=sample_document, context=base_context,
                errors=errors, feedback=feedback,
            )
        assert errors == []

    @pytest.mark.asyncio
    async def test_llm_qa_failed_with_issues(self, executor_with_llm, sample_document, base_context):
        """When LLM QA fails with specific issues, they are appended to errors."""
        node_config = {"task_ref": "qa_task_v1", "qa_mode": "structural"}
        with patch.object(
            executor_with_llm, "_run_llm_qa", new_callable=AsyncMock,
            return_value={
                "passed": False,
                "issues": ["Missing section X", "Invalid format in Y"],
                "feedback": "Multiple issues found",
            },
        ):
            errors = []
            feedback = {}
            await executor_with_llm._check_llm_qa(
                node_id="qa-1", node_config=node_config,
                document=sample_document, context=base_context,
                errors=errors, feedback=feedback,
            )
        assert len(errors) == 2
        assert "Missing section X" in errors
        assert feedback["llm_feedback"] == "Multiple issues found"

    @pytest.mark.asyncio
    async def test_llm_qa_failed_no_issues_generic_error(self, executor_with_llm, sample_document, base_context):
        """When LLM QA fails with no specific issues, a generic error is appended."""
        node_config = {"task_ref": "qa_task_v1", "qa_mode": "structural"}
        with patch.object(
            executor_with_llm, "_run_llm_qa", new_callable=AsyncMock,
            return_value={"passed": False, "issues": [], "feedback": ""},
        ):
            errors = []
            feedback = {}
            await executor_with_llm._check_llm_qa(
                node_id="qa-1", node_config=node_config,
                document=sample_document, context=base_context,
                errors=errors, feedback=feedback,
            )
        assert len(errors) == 1
        assert errors[0] == "QA check failed"

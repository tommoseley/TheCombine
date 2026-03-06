"""CRAP score remediation tests for QANodeExecutor.

Targets:
1. _run_semantic_qa (CC=12, 29.4% cov -> need ~58%)
2. _run_code_based_validation (CC=12, 45.8% cov -> need ~58%)

Tests focus on UNCOVERED branches to push coverage above CRAP-30 threshold.
"""

import json
import os
import sys
import types

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the workflow package to avoid circular import through __init__.py
# (pre-existing circular: workflow.__init__ -> plan_executor -> api routers -> plan_executor)
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.qa import QANodeExecutor  # noqa: E402
from app.domain.workflow.nodes.base import DocumentWorkflowContext, NodeResult  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / Fakes
# ---------------------------------------------------------------------------

def _make_context(
    context_state=None,
    extra=None,
    document_type="test_doc",
    project_id="proj-1",
    **overrides,
):
    ctx = DocumentWorkflowContext(
        project_id=project_id,
        document_type=document_type,
        context_state=context_state or {},
        extra=extra or {},
    )
    for k, v in overrides.items():
        setattr(ctx, k, v)
    return ctx


class FakeLLMService:
    """Fake LLM service that returns a canned response."""

    def __init__(self, response="{}"):
        self.response = response
        self.called_with = None

    async def complete(self, messages, **kwargs):
        self.called_with = {"messages": messages, **kwargs}
        return self.response


# ====================================================================
# _run_semantic_qa tests
# ====================================================================


class TestRunSemanticQa:
    """Tests for QANodeExecutor._run_semantic_qa uncovered branches."""

    @pytest.mark.asyncio
    async def test_disabled_via_env_var(self):
        """Branch: SEMANTIC_QA_ENABLED=false -> returns None."""
        executor = QANodeExecutor(llm_service=FakeLLMService())
        ctx = _make_context(
            context_state={"pgc_invariants": [{"id": "C1"}]},
        )
        with patch.dict(os.environ, {"SEMANTIC_QA_ENABLED": "false"}):
            result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_llm_service_returns_none(self):
        """Branch: llm_service is None -> returns None."""
        executor = QANodeExecutor(llm_service=None)
        ctx = _make_context(
            context_state={"pgc_invariants": [{"id": "C1"}]},
        )
        result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_invariants_returns_none(self):
        """Branch: context_state has no pgc_invariants -> returns None."""
        executor = QANodeExecutor(llm_service=FakeLLMService())
        ctx = _make_context(context_state={})
        result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_invariants_returns_none(self):
        """Branch: pgc_invariants is empty list -> returns None."""
        executor = QANodeExecutor(llm_service=FakeLLMService())
        ctx = _make_context(context_state={"pgc_invariants": []})
        result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_context_state_returns_none(self):
        """Branch: context has empty context_state -> returns None."""
        executor = QANodeExecutor(llm_service=FakeLLMService())
        ctx = _make_context()
        ctx.context_state = {}
        result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_context_without_extra_gets_empty_correlation_id(self):
        """Branch: context.extra is missing/empty -> correlation_id = ''."""
        qa_report = {
            "gate": "pass",
            "summary": {"errors": 0, "warnings": 0},
            "coverage": {"expected_count": 1, "items": [
                {"constraint_id": "C1", "status": "evaluated"}
            ]},
            "constraint_results": [
                {"constraint_id": "C1", "verdict": "compliant", "confidence": "high",
                 "evidence": "found", "findings": []}
            ],
            "findings": [],
        }
        llm = FakeLLMService(response=json.dumps(qa_report))
        executor = QANodeExecutor(llm_service=llm)
        ctx = _make_context(
            context_state={
                "pgc_invariants": [{"id": "C1", "text": "Must do X"}],
                "pgc_questions": [],
                "pgc_answers": {},
            },
            extra={},  # no execution_id
        )

        with patch("app.config.package_loader.get_package_loader") as mock_pl:
            mock_task = MagicMock()
            mock_task.content = "Policy prompt text"
            mock_pl.return_value.get_task.return_value = mock_task

            mock_schema = MagicMock()
            mock_schema.content = {}
            mock_pl.return_value.get_schema.return_value = mock_schema

            with patch("jsonschema.validate"):
                result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)

        assert result is not None
        assert result.get("gate") == "pass"

    @pytest.mark.asyncio
    async def test_correlation_id_from_extra(self):
        """Branch: context.extra has execution_id -> used as correlation_id."""
        qa_report = {
            "gate": "pass",
            "summary": {"errors": 0, "warnings": 0},
            "coverage": {"expected_count": 1, "items": [
                {"constraint_id": "C1", "status": "evaluated"}
            ]},
            "constraint_results": [
                {"constraint_id": "C1", "verdict": "compliant", "confidence": "high",
                 "evidence": "found", "findings": []}
            ],
            "findings": [],
        }
        llm = FakeLLMService(response=json.dumps(qa_report))
        executor = QANodeExecutor(llm_service=llm)
        ctx = _make_context(
            context_state={
                "pgc_invariants": [{"id": "C1", "text": "Must do X"}],
                "pgc_questions": [],
                "pgc_answers": {},
            },
            extra={"execution_id": "exec-abc123"},
        )

        with patch("app.config.package_loader.get_package_loader") as mock_pl:
            mock_task = MagicMock()
            mock_task.content = "Policy prompt text"
            mock_pl.return_value.get_task.return_value = mock_task

            mock_schema = MagicMock()
            mock_schema.content = {}
            mock_pl.return_value.get_schema.return_value = mock_schema

            with patch("jsonschema.validate"):
                result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)

        assert result is not None
        # Verify execution_id was passed to LLM
        assert llm.called_with["workflow_execution_id"] == "exec-abc123"

    @pytest.mark.asyncio
    async def test_policy_prompt_fallback_on_exception(self):
        """Branch: PackageLoader raises -> uses fallback policy prompt."""
        qa_report = {
            "gate": "pass",
            "summary": {"errors": 0, "warnings": 0},
            "coverage": {"expected_count": 1, "items": [
                {"constraint_id": "C1", "status": "evaluated"}
            ]},
            "constraint_results": [
                {"constraint_id": "C1", "verdict": "compliant", "confidence": "high",
                 "evidence": "found", "findings": []}
            ],
            "findings": [],
        }
        llm = FakeLLMService(response=json.dumps(qa_report))
        executor = QANodeExecutor(llm_service=llm)
        ctx = _make_context(
            context_state={
                "pgc_invariants": [{"id": "C1", "text": "Must do X"}],
            },
            extra={"execution_id": "exec-abc"},
        )

        with patch("app.config.package_loader.get_package_loader") as mock_pl:
            # First call (get_task) raises
            mock_pl.return_value.get_task.side_effect = FileNotFoundError("not found")

            # get_schema for _parse_semantic_qa_response
            mock_schema = MagicMock()
            mock_schema.content = {}
            mock_pl.return_value.get_schema.return_value = mock_schema

            with patch("jsonschema.validate"):
                result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)

        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_exception_returns_error_report(self):
        """Branch: LLM call raises exception -> returns error report dict."""

        class FailingLLM:
            async def complete(self, messages, **kwargs):
                raise RuntimeError("LLM provider down")

        executor = QANodeExecutor(llm_service=FailingLLM())
        ctx = _make_context(
            context_state={
                "pgc_invariants": [{"id": "C1", "text": "constraint"}],
            },
            extra={"execution_id": "exec-err"},
        )

        with patch("app.config.package_loader.get_package_loader") as mock_pl:
            mock_task = MagicMock()
            mock_task.content = "Policy"
            mock_pl.return_value.get_task.return_value = mock_task

            result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)

        # Should return an error report, not raise
        assert result is not None
        assert result.get("gate") == "fail"

    @pytest.mark.asyncio
    async def test_enabled_env_var_true(self):
        """Branch: SEMANTIC_QA_ENABLED=true (explicit) -> proceeds."""
        executor = QANodeExecutor(llm_service=FakeLLMService())
        # No invariants -> returns None, but verifies env check passes
        ctx = _make_context(context_state={"pgc_invariants": []})
        with patch.dict(os.environ, {"SEMANTIC_QA_ENABLED": "true"}):
            result = await executor._run_semantic_qa("qa-1", {"doc": True}, ctx)
        assert result is None  # Stopped at no-invariants, not env check


# ====================================================================
# _run_code_based_validation tests
# ====================================================================


class TestRunCodeBasedValidation:
    """Tests for QANodeExecutor._run_code_based_validation uncovered branches."""

    def test_no_context_state_at_all(self):
        """Branch: context lacks context_state -> returns None."""
        executor = QANodeExecutor()
        ctx = _make_context()
        ctx.context_state = {}
        result = executor._run_code_based_validation({"doc": True}, ctx)
        assert result is None

    def test_no_pgc_questions_and_no_answers(self):
        """Branch: empty pgc_questions AND empty pgc_answers -> skip."""
        executor = QANodeExecutor()
        ctx = _make_context(
            context_state={"pgc_questions": [], "pgc_answers": {}},
        )
        result = executor._run_code_based_validation({"doc": True}, ctx)
        assert result is None

    def test_pgc_questions_as_dict_with_questions_key(self):
        """Branch: pgc_questions is a dict with 'questions' key."""
        executor = QANodeExecutor()
        ctx = _make_context(
            context_state={
                "pgc_questions": {
                    "questions": [
                        {"id": "Q1", "text": "What?", "priority": "must",
                         "answer_type": "yes_no"},
                    ],
                },
                "pgc_answers": {"Q1": {"answer": "yes", "answer_label": "Yes"}},
            },
        )

        with patch("app.domain.workflow.nodes.qa.PromotionValidator") as MockValidator:
            mock_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.warnings = []
            mock_result.errors = []
            mock_instance.validate.return_value = mock_result

            result = executor._run_code_based_validation({"constraints": []}, ctx)

        assert result is not None
        assert result.passed is True

    def test_pgc_questions_as_list(self):
        """Branch: pgc_questions is a plain list."""
        executor = QANodeExecutor()
        ctx = _make_context(
            context_state={
                "pgc_questions": [
                    {"id": "Q1", "text": "What?", "priority": "must",
                     "answer_type": "yes_no"},
                ],
                "pgc_answers": {"Q1": {"answer": "yes", "answer_label": "Yes"}},
            },
        )

        with patch("app.domain.workflow.nodes.qa.PromotionValidator") as MockValidator:
            mock_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.warnings = []
            mock_result.errors = []
            mock_instance.validate.return_value = mock_result

            result = executor._run_code_based_validation({"constraints": []}, ctx)

        assert result is not None
        assert result.passed is True

    def test_direct_context_attributes_override(self):
        """Branch: context has direct pgc_questions/pgc_answers attrs."""
        executor = QANodeExecutor()
        ctx = _make_context(context_state={})
        # Set direct attributes
        ctx.pgc_questions = [
            {"id": "Q1", "text": "Direct?", "priority": "must",
             "answer_type": "free_text"},
        ]
        ctx.pgc_answers = {"Q1": {"answer": "direct answer"}}
        ctx.intake = {"summary": "test intake"}

        with patch("app.domain.workflow.nodes.qa.PromotionValidator") as MockValidator:
            mock_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.warnings = []
            mock_result.errors = []
            mock_instance.validate.return_value = mock_result

            result = executor._run_code_based_validation({"constraints": []}, ctx)

        assert result is not None
        # Verify the validator was called with direct attrs
        call_args = mock_instance.validate.call_args
        validation_input = call_args[0][0]
        assert validation_input.intake == {"summary": "test intake"}

    def test_intake_from_context_state(self):
        """Branch: intake comes from context_state.concierge_intake."""
        executor = QANodeExecutor()
        ctx = _make_context(
            context_state={
                "pgc_questions": [{"id": "Q1", "text": "Q?", "priority": "must",
                                   "answer_type": "yes_no"}],
                "pgc_answers": {"Q1": {"answer": "yes"}},
                "concierge_intake": {"summary": "intake data"},
            },
        )

        with patch("app.domain.workflow.nodes.qa.PromotionValidator") as MockValidator:
            mock_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.warnings = []
            mock_result.errors = []
            mock_instance.validate.return_value = mock_result

            result = executor._run_code_based_validation({"doc": True}, ctx)

        assert result is not None
        call_args = mock_instance.validate.call_args
        validation_input = call_args[0][0]
        assert validation_input.intake == {"summary": "intake data"}

    def test_only_pgc_answers_no_questions(self):
        """Branch: pgc_answers present but pgc_questions empty -> runs validation."""
        executor = QANodeExecutor()
        ctx = _make_context(
            context_state={
                "pgc_questions": [],
                "pgc_answers": {"Q1": {"answer": "yes"}},
            },
        )

        with patch("app.domain.workflow.nodes.qa.PromotionValidator") as MockValidator:
            mock_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.warnings = []
            mock_result.errors = []
            mock_instance.validate.return_value = mock_result

            result = executor._run_code_based_validation({"doc": True}, ctx)

        assert result is not None

    def test_validation_failure_returns_result(self):
        """Branch: validator returns passed=False."""
        executor = QANodeExecutor()
        ctx = _make_context(
            context_state={
                "pgc_questions": [{"id": "Q1", "text": "Q?", "priority": "must",
                                   "answer_type": "yes_no"}],
                "pgc_answers": {"Q1": {"answer": "yes"}},
            },
        )

        with patch("app.domain.workflow.nodes.qa.PromotionValidator") as MockValidator:
            mock_instance = MockValidator.return_value
            mock_result = MagicMock()
            mock_result.passed = False
            mock_result.errors = [MagicMock(field="constraints", message="Promoted answer")]
            mock_result.warnings = []
            mock_instance.validate.return_value = mock_result

            result = executor._run_code_based_validation({"constraints": []}, ctx)

        assert result is not None
        assert result.passed is False

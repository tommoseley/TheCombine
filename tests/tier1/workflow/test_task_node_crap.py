"""CRAP score remediation tests for TaskNodeExecutor._build_messages.

Target: TaskNodeExecutor._build_messages (CC=14, 51.7% cov -> need ~65%)

Tests focus on UNCOVERED branches: bound constraints summary, QA feedback,
input documents, document_content, and various context_state edge cases.
"""

import json
import os
import sys
import types

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Stub the workflow package to avoid circular import through __init__.py
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.nodes.task import TaskNodeExecutor  # noqa: E402
from app.domain.workflow.nodes.base import DocumentWorkflowContext  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(
    context_state: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    input_documents: Optional[Dict[str, Dict[str, Any]]] = None,
    document_content: Optional[Dict[str, Any]] = None,
    intent_capsule: Optional[str] = None,
) -> DocumentWorkflowContext:
    return DocumentWorkflowContext(
        project_id="proj-1",
        document_type="test_doc",
        context_state=context_state or {},
        extra=extra or {},
        input_documents=input_documents or {},
        document_content=document_content or {},
        intent_capsule=intent_capsule,
    )


class FakeLLMService:
    async def complete(self, messages, **kwargs):
        return "{}"


class FakePromptLoader:
    def load_task_prompt(self, task_ref):
        return f"Task prompt for {task_ref}"

    def load_role_prompt(self, role_ref):
        return f"Role prompt for {role_ref}"


def _make_executor() -> TaskNodeExecutor:
    return TaskNodeExecutor(
        llm_service=FakeLLMService(),
        prompt_loader=FakePromptLoader(),
    )


# ====================================================================
# _build_messages tests
# ====================================================================


class TestBuildMessages:
    """Tests for TaskNodeExecutor._build_messages uncovered branches."""

    def test_minimal_no_context(self):
        """Branch: no context data at all -> only task prompt message."""
        executor = _make_executor()
        ctx = _make_context()
        messages = executor._build_messages("Do the thing", ctx)

        # Should have just the task prompt
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Do the thing"

    def test_user_input_from_extra(self):
        """Branch: user_input in context.extra -> User Request section."""
        executor = _make_executor()
        ctx = _make_context(extra={"user_input": "Build me a document"})
        messages = executor._build_messages("Do the thing", ctx)

        assert len(messages) == 2
        assert "## User Request" in messages[0]["content"]
        assert "Build me a document" in messages[0]["content"]

    def test_user_input_from_context_state(self):
        """Branch: user_input in context_state (fallback) -> User Request section."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={"user_input": "Build via context_state"},
            extra={},  # No user_input in extra
        )
        messages = executor._build_messages("Do the thing", ctx)

        assert len(messages) == 2
        assert "Build via context_state" in messages[0]["content"]

    def test_bound_constraints_invariants(self):
        """Branch: pgc_invariants in context_state -> Bound Constraints section."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "pgc_invariants": [
                    {"id": "C1", "user_answer_label": "Yes", "binding_source": "selection"},
                    {"id": "C2", "user_answer_label": "Python", "binding_source": "selection"},
                ],
            },
        )
        messages = executor._build_messages("Generate", ctx)

        assert len(messages) == 2
        content = messages[0]["content"]
        assert "Bound Constraints" in content
        assert "C1: Yes" in content
        assert "C2: Python" in content

    def test_bound_constraints_exclusion_source(self):
        """Branch: invariant with binding_source='exclusion' -> EXCLUDED annotation."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "pgc_invariants": [
                    {"id": "C1", "user_answer_label": "No", "binding_source": "exclusion"},
                ],
            },
        )
        messages = executor._build_messages("Generate", ctx)

        content = messages[0]["content"]
        assert "EXCLUDED" in content

    def test_bound_constraints_fallback_user_answer(self):
        """Branch: invariant without user_answer_label -> falls back to user_answer."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "pgc_invariants": [
                    {"id": "C1", "user_answer": 42},
                ],
            },
        )
        messages = executor._build_messages("Generate", ctx)

        content = messages[0]["content"]
        assert "C1: 42" in content

    def test_no_invariants_no_bound_constraints_section(self):
        """Branch: pgc_invariants is empty -> no Bound Constraints section added."""
        executor = _make_executor()
        ctx = _make_context(context_state={"pgc_invariants": []})
        messages = executor._build_messages("Generate", ctx)

        # Context message may exist (for Extracted Context) but no Bound Constraints
        for msg in messages:
            assert "Bound Constraints" not in msg["content"]

    def test_qa_feedback_present(self):
        """Branch: qa_feedback in context_state -> Previous QA Feedback section."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "qa_feedback": {
                    "issues": [
                        {"type": "error", "message": "Missing constraints section",
                         "check_id": "CHK-001", "section": "constraints",
                         "remediation": "Add constraints"},
                    ],
                    "summary": "Failed QA with 1 issue that needs fixing",
                },
            },
        )
        messages = executor._build_messages("Generate", ctx)

        assert len(messages) == 2
        content = messages[0]["content"]
        assert "Previous QA Feedback" in content
        assert "Missing constraints section" in content
        assert "CHK-001" in content
        assert "constraints" in content
        assert "Add constraints" in content

    def test_qa_feedback_empty_issues(self):
        """Branch: qa_feedback exists but issues list empty -> no QA Feedback section."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "qa_feedback": {"issues": [], "summary": ""},
            },
        )
        messages = executor._build_messages("Generate", ctx)

        # No QA Feedback section (even though Extracted Context may appear)
        for msg in messages:
            assert "Previous QA Feedback" not in msg["content"]

    def test_qa_feedback_with_summary(self):
        """Branch: qa_feedback has long summary -> rendered."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "qa_feedback": {
                    "issues": [
                        {"type": "warning", "message": "Consider adding more detail"},
                    ],
                    "summary": "The document needs improvement in detail coverage " * 5,
                },
            },
        )
        messages = executor._build_messages("Generate", ctx)
        content = messages[0]["content"]
        assert "Summary:" in content

    def test_qa_feedback_issue_without_optional_fields(self):
        """Branch: qa_feedback issue missing check_id, section, remediation."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "qa_feedback": {
                    "issues": [
                        {"type": "error", "message": "Generic issue"},
                    ],
                },
            },
        )
        messages = executor._build_messages("Generate", ctx)
        content = messages[0]["content"]
        assert "Generic issue" in content

    def test_context_state_included_as_extracted_context(self):
        """Branch: context_state has relevant keys -> Extracted Context section."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "project_type": "SaaS",
                "intake_summary": "User wants a dashboard",
            },
        )
        messages = executor._build_messages("Generate", ctx)

        assert len(messages) == 2
        content = messages[0]["content"]
        assert "Extracted Context" in content
        assert "project_type" in content

    def test_context_state_excludes_document_keys(self):
        """Branch: keys starting with 'document_' and 'last_produced_document' are excluded."""
        executor = _make_executor()
        ctx = _make_context(
            context_state={
                "document_draft": {"some": "data"},
                "last_produced_document": {"other": "data"},
                "project_type": "SaaS",
            },
        )
        messages = executor._build_messages("Generate", ctx)
        content = messages[0]["content"]
        assert "document_draft" not in content
        assert "last_produced_document" not in content
        assert "project_type" in content

    def test_input_documents_present(self):
        """Branch: input_documents non-empty -> Input Documents section."""
        executor = _make_executor()
        ctx = _make_context(
            input_documents={
                "concierge_intake": {"summary": "User needs X", "project_type": "API"},
            },
        )
        messages = executor._build_messages("Generate", ctx)

        assert len(messages) == 2
        content = messages[0]["content"]
        assert "Input Documents" in content
        assert "concierge_intake" in content

    def test_document_content_from_prior_nodes(self):
        """Branch: document_content non-empty -> Previous Documents section."""
        executor = _make_executor()
        ctx = _make_context(
            document_content={
                "draft": {"title": "My Document", "sections": ["a", "b"]},
            },
        )
        messages = executor._build_messages("Generate", ctx)

        assert len(messages) == 2
        content = messages[0]["content"]
        assert "Previous Documents" in content
        assert "draft" in content

    def test_all_context_parts_combined(self):
        """Branch: all context parts present -> single context message + task prompt."""
        executor = _make_executor()
        ctx = _make_context(
            extra={"user_input": "Build it"},
            context_state={
                "pgc_invariants": [{"id": "C1", "user_answer_label": "Yes"}],
                "qa_feedback": {
                    "issues": [{"message": "Fix it", "type": "error"}],
                    "summary": "x" * 20,
                },
                "project_type": "SaaS",
            },
            input_documents={"intake": {"data": "yes"}},
            document_content={"draft": {"title": "Doc"}},
        )
        messages = executor._build_messages("Generate doc", ctx)

        assert len(messages) == 2
        content = messages[0]["content"]
        assert "User Request" in content
        assert "Bound Constraints" in content
        assert "Previous QA Feedback" in content
        assert "Extracted Context" in content
        assert "Input Documents" in content
        assert "Previous Documents" in content

    def test_task_prompt_always_last_message(self):
        """Task prompt is always the last message regardless of context."""
        executor = _make_executor()
        ctx = _make_context(
            extra={"user_input": "test"},
            context_state={"project_type": "API"},
        )
        messages = executor._build_messages("TASK_PROMPT_HERE", ctx)

        assert messages[-1]["content"] == "TASK_PROMPT_HERE"
        assert messages[-1]["role"] == "user"

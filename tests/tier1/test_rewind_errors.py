"""Tests for Rewind Error Model (WS-REWIND-015)."""

from uuid import uuid4

from app.domain.models.rewind_errors import (
    RewindBlockedError,
    STALE_ARTIFACT,
    STALE_INPUT,
    stale_artifact_error,
    stale_input_error,
)


class TestRewindBlockedError:
    """Structured error model."""

    def test_all_fields_present(self):
        err = RewindBlockedError(
            error_code="TEST",
            document_id=uuid4(),
            document_type="work_package",
            current_status="stale",
            message="test message",
            required_action="do something",
            rewind_stage="TA",
        )
        assert err.error_code == "TEST"
        assert err.document_type == "work_package"
        assert err.rewind_stage == "TA"

    def test_rewind_stage_optional(self):
        err = RewindBlockedError(
            error_code="TEST",
            document_id=uuid4(),
            document_type="work_package",
            current_status="stale",
            message="test",
            required_action="test",
        )
        assert err.rewind_stage is None


class TestStaleArtifactError:
    """Factory for stale artifact errors."""

    def test_creates_with_rewind_stage(self):
        doc_id = uuid4()
        err = stale_artifact_error(doc_id, "technical_architecture", "TA")
        assert err.error_code == STALE_ARTIFACT
        assert err.document_id == doc_id
        assert err.rewind_stage == "TA"
        assert "TA" in err.required_action

    def test_creates_without_rewind_stage(self):
        err = stale_artifact_error(uuid4(), "work_package")
        assert err.rewind_stage is None
        assert "upstream" in err.required_action.lower()


class TestStaleInputError:
    """Factory for stale input errors."""

    def test_includes_operation(self):
        err = stale_input_error(uuid4(), "work_statement", "generate downstream")
        assert err.error_code == STALE_INPUT
        assert "generate downstream" in err.message

    def test_includes_document_type(self):
        err = stale_input_error(uuid4(), "implementation_plan", "evaluate")
        assert "implementation_plan" in err.message

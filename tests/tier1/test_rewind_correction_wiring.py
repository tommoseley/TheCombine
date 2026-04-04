"""Tests for rewind + correction wiring (ADR-069).

Verifies:
- RewindRequestBody: reason is the correction brief, applies_to_stages optional
- RewindResponseBody: correction_record_id is always present
- No separate CorrectionInput model — single-field design
"""

import pytest
from pydantic import ValidationError


class TestRewindRequestBody:
    """RewindRequestBody with merged reason/correction."""

    def test_reason_is_required(self):
        from app.api.v1.routers.rewind import RewindRequestBody
        with pytest.raises(ValidationError):
            RewindRequestBody(rewind_to_stage="TA")

    def test_basic_rewind(self):
        from app.api.v1.routers.rewind import RewindRequestBody
        body = RewindRequestBody(
            rewind_to_stage="TA",
            reason="Architecture must be server-side. No direct API calls from iOS.",
        )
        assert body.reason == "Architecture must be server-side. No direct API calls from iOS."
        assert body.applies_to_stages is None

    def test_with_applies_to_stages(self):
        from app.api.v1.routers.rewind import RewindRequestBody
        body = RewindRequestBody(
            rewind_to_stage="TA",
            reason="Cloud AI must be server-side",
            applies_to_stages=["TA", "IP"],
        )
        assert body.applies_to_stages == ["TA", "IP"]

    def test_applies_to_defaults_to_none(self):
        from app.api.v1.routers.rewind import RewindRequestBody
        body = RewindRequestBody(
            rewind_to_stage="TA",
            reason="Regenerate",
        )
        assert body.applies_to_stages is None

    def test_no_correction_input_model(self):
        """CorrectionInput should no longer exist — single-field design."""
        with pytest.raises(ImportError):
            from app.api.v1.routers.rewind import CorrectionInput  # noqa: F401


class TestRewindResponseBody:
    """RewindResponseBody always includes correction_record_id."""

    def test_response_with_correction_id(self):
        from app.api.v1.routers.rewind import RewindResponseBody
        resp = RewindResponseBody(
            success=True,
            rewind_to_stage="TA",
            affected_stages=["TA", "WP", "WS"],
            affected_document_count=3,
            stale_document_ids=["abc"],
            lineage_event_id="def",
            correction_record_id="ghi",
        )
        assert resp.correction_record_id == "ghi"

    def test_response_requires_correction_id(self):
        """correction_record_id is now required (always dual-written)."""
        from app.api.v1.routers.rewind import RewindResponseBody
        with pytest.raises(ValidationError):
            RewindResponseBody(
                success=True,
                rewind_to_stage="TA",
                affected_stages=["TA"],
                affected_document_count=1,
                stale_document_ids=[],
                lineage_event_id="abc",
                # missing correction_record_id
            )

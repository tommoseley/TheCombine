"""Tests for correction pre-population endpoint models (ADR-069, WS-CORRECT-003).

Verifies CorrectionResponse model structure.
Endpoint integration tested via rewind router imports.
"""

import pytest


class TestCorrectionResponseModel:
    """CorrectionResponse Pydantic model."""

    def test_valid_response(self):
        from app.api.v1.routers.rewind import CorrectionResponse
        resp = CorrectionResponse(
            stage="TA",
            text="AI must be server-side",
            applies_to_stages=["TA", "IP"],
            authority_record_id="abc-123",
            created_at="2026-04-02T12:00:00+00:00",
        )
        assert resp.stage == "TA"
        assert resp.text == "AI must be server-side"
        assert resp.applies_to_stages == ["TA", "IP"]

    def test_required_fields(self):
        from app.api.v1.routers.rewind import CorrectionResponse
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CorrectionResponse(stage="TA")  # missing required fields

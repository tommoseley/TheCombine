"""Tier-1 tests for ta_version_id promotion gate.

Verifies that:
- build_promoted_wp uses ta_version_id when provided
- build_promoted_wp falls back to "pending" when not provided (backward compat)
- validate_ta_for_promotion blocks when TA is missing

Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.wp_promotion_service import (
    build_promoted_wp,
    validate_ta_for_promotion,
)


def _candidate():
    return {
        "wpc_id": "WPC-001",
        "title": "Test Candidate",
        "rationale": "Test rationale",
        "scope_summary": ["Feature A"],
    }


# =========================================================================
# build_promoted_wp ta_version_id
# =========================================================================


class TestBuildPromotedWPTAVersion:

    def test_ta_version_id_set_when_provided(self):
        wp = build_promoted_wp(
            _candidate(), "kept", "notes", wp_id="WP-001",
            ta_version_id="TA-001",
        )
        assert wp["governance_pins"]["ta_version_id"] == "TA-001"

    def test_ta_version_id_pending_when_not_provided(self):
        wp = build_promoted_wp(
            _candidate(), "kept", "notes", wp_id="WP-001",
        )
        assert wp["governance_pins"]["ta_version_id"] == "pending"

    def test_ta_version_id_pending_when_none(self):
        wp = build_promoted_wp(
            _candidate(), "kept", "notes", wp_id="WP-001",
            ta_version_id=None,
        )
        assert wp["governance_pins"]["ta_version_id"] == "pending"


# =========================================================================
# validate_ta_for_promotion
# =========================================================================


class TestValidateTAForPromotion:

    def test_valid_ta_returns_version(self):
        ta_doc = {"display_id": "TA-001", "content": {"architecture_summary": "..."}}
        result = validate_ta_for_promotion(ta_doc)
        assert result == "TA-001"

    def test_none_ta_returns_error(self):
        result = validate_ta_for_promotion(None)
        assert result is None

    def test_ta_without_display_id_returns_error(self):
        ta_doc = {"content": {"architecture_summary": "..."}}
        result = validate_ta_for_promotion(ta_doc)
        assert result is None

    def test_ta_with_empty_display_id_returns_error(self):
        ta_doc = {"display_id": "", "content": {}}
        result = validate_ta_for_promotion(ta_doc)
        assert result is None

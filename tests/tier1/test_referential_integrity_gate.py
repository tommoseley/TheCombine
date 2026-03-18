"""Tier-1 tests for WP→WS referential integrity gate at stabilization.

Verifies that every ws_id referenced in WP ws_index has a corresponding
persisted WS document. Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_crud_service import check_ws_referential_integrity


def _wp(ws_index_ids=None):
    """Build a WP content dict with ws_index."""
    index = [{"ws_id": wid, "order_key": f"a{i}"} for i, wid in enumerate(ws_index_ids or [])]
    return {
        "wp_id": "WP-001",
        "title": "Test WP",
        "ws_index": index,
    }


# =========================================================================
# Referential integrity checks
# =========================================================================


class TestReferentialIntegrity:
    """Every ws_index entry must resolve to a persisted WS."""

    def test_all_present_passes(self):
        errors = check_ws_referential_integrity(
            _wp(["WS-001", "WS-002"]),
            ["WS-001", "WS-002"],
        )
        assert errors == []

    def test_missing_one_ws_fails(self):
        errors = check_ws_referential_integrity(
            _wp(["WS-001", "WS-002", "WS-003"]),
            ["WS-001", "WS-003"],
        )
        assert len(errors) == 1
        assert "WS-002" in errors[0]

    def test_missing_multiple_ws_fails(self):
        errors = check_ws_referential_integrity(
            _wp(["WS-001", "WS-002", "WS-003"]),
            ["WS-001"],
        )
        assert len(errors) == 1  # single error listing all missing
        assert "WS-002" in errors[0]
        assert "WS-003" in errors[0]

    def test_empty_ws_index_passes(self):
        """No references means nothing to check (completeness gate handles this)."""
        errors = check_ws_referential_integrity(
            _wp([]),
            [],
        )
        assert errors == []

    def test_extra_ws_not_in_index_ignored(self):
        """WS docs that exist but aren't in ws_index are fine (orphan, not corruption)."""
        errors = check_ws_referential_integrity(
            _wp(["WS-001"]),
            ["WS-001", "WS-002", "WS-003"],
        )
        assert errors == []

    def test_no_ws_index_key_passes(self):
        """WP with no ws_index key at all is fine."""
        wp = {"wp_id": "WP-001", "title": "Test"}
        errors = check_ws_referential_integrity(wp, [])
        assert errors == []

    def test_returns_list(self):
        result = check_ws_referential_integrity(_wp([]), [])
        assert isinstance(result, list)

"""Tier-1 tests for parent_wp_id invariant at stabilization.

Every WS under a WP must have parent_wp_id matching the WP's wp_id.
Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_crud_service import check_parent_wp_invariant


# =========================================================================
# Parent WP invariant checks
# =========================================================================


class TestParentWPInvariant:

    def test_all_match_passes(self):
        errors = check_parent_wp_invariant(
            "WP-001",
            [
                {"ws_id": "WS-001", "parent_wp_id": "WP-001"},
                {"ws_id": "WS-002", "parent_wp_id": "WP-001"},
            ],
        )
        assert errors == []

    def test_one_mismatch_fails(self):
        errors = check_parent_wp_invariant(
            "WP-001",
            [
                {"ws_id": "WS-001", "parent_wp_id": "WP-001"},
                {"ws_id": "WS-002", "parent_wp_id": "WP-999"},
            ],
        )
        assert len(errors) == 1
        assert "WS-002" in errors[0]
        assert "WP-999" in errors[0]

    def test_multiple_mismatches_fails(self):
        errors = check_parent_wp_invariant(
            "WP-001",
            [
                {"ws_id": "WS-001", "parent_wp_id": "WP-002"},
                {"ws_id": "WS-002", "parent_wp_id": "WP-003"},
            ],
        )
        assert len(errors) == 2

    def test_missing_parent_wp_id_fails(self):
        errors = check_parent_wp_invariant(
            "WP-001",
            [{"ws_id": "WS-001", "title": "No parent field"}],
        )
        assert len(errors) == 1
        assert "WS-001" in errors[0]

    def test_empty_ws_list_passes(self):
        errors = check_parent_wp_invariant("WP-001", [])
        assert errors == []

    def test_returns_list(self):
        result = check_parent_wp_invariant("WP-001", [])
        assert isinstance(result, list)

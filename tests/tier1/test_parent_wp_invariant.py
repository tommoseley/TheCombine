"""Tier-1 tests for parent_wp_id invariant at stabilization.

Every WS under a WP must have parent_wp_id matching the WP's wp_id.
Returns structured StabilizationFinding objects.
Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_crud_service import (
    StabilizationFinding,
    check_parent_wp_invariant,
)


# =========================================================================
# Parent WP invariant checks
# =========================================================================


class TestParentWPInvariant:

    def test_all_match_passes(self):
        findings = check_parent_wp_invariant(
            "WP-001",
            [
                {"ws_id": "WS-001", "parent_wp_id": "WP-001"},
                {"ws_id": "WS-002", "parent_wp_id": "WP-001"},
            ],
        )
        assert findings == []

    def test_one_mismatch_fails(self):
        findings = check_parent_wp_invariant(
            "WP-001",
            [
                {"ws_id": "WS-001", "parent_wp_id": "WP-001"},
                {"ws_id": "WS-002", "parent_wp_id": "WP-999"},
            ],
        )
        assert len(findings) == 1
        assert findings[0].rule_id == "PARENT-002"
        assert findings[0].artifact_id == "WS-002"
        assert "WP-999" in findings[0].message

    def test_multiple_mismatches_fails(self):
        findings = check_parent_wp_invariant(
            "WP-001",
            [
                {"ws_id": "WS-001", "parent_wp_id": "WP-002"},
                {"ws_id": "WS-002", "parent_wp_id": "WP-003"},
            ],
        )
        assert len(findings) == 2

    def test_missing_parent_wp_id_fails(self):
        findings = check_parent_wp_invariant(
            "WP-001",
            [{"ws_id": "WS-001", "title": "No parent field"}],
        )
        assert len(findings) == 1
        assert findings[0].rule_id == "PARENT-001"
        assert findings[0].artifact_id == "WS-001"

    def test_empty_ws_list_passes(self):
        findings = check_parent_wp_invariant("WP-001", [])
        assert findings == []

    def test_finding_is_structured(self):
        findings = check_parent_wp_invariant(
            "WP-001",
            [{"ws_id": "WS-001", "parent_wp_id": "WP-999"}],
        )
        f = findings[0]
        assert isinstance(f, StabilizationFinding)
        assert f.field_path == "parent_wp_id"
        assert f.remediation_hint is not None

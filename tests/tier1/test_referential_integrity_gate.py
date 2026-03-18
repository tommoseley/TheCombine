"""Tier-1 tests for WP→WS referential integrity gate at stabilization.

Verifies that every ws_id referenced in WP ws_index has a corresponding
persisted WS document. Returns structured StabilizationFinding objects.
Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_crud_service import (
    StabilizationFinding,
    check_ws_referential_integrity,
)


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
        findings = check_ws_referential_integrity(
            _wp(["WS-001", "WS-002"]),
            ["WS-001", "WS-002"],
        )
        assert findings == []

    def test_missing_one_ws_fails(self):
        findings = check_ws_referential_integrity(
            _wp(["WS-001", "WS-002", "WS-003"]),
            ["WS-001", "WS-003"],
        )
        assert len(findings) == 1
        assert findings[0].rule_id == "REF-001"
        assert "WS-002" in findings[0].message

    def test_missing_multiple_ws_fails(self):
        findings = check_ws_referential_integrity(
            _wp(["WS-001", "WS-002", "WS-003"]),
            ["WS-001"],
        )
        assert len(findings) == 1
        assert "WS-002" in findings[0].message
        assert "WS-003" in findings[0].message

    def test_empty_ws_index_passes(self):
        findings = check_ws_referential_integrity(_wp([]), [])
        assert findings == []

    def test_extra_ws_not_in_index_ignored(self):
        findings = check_ws_referential_integrity(
            _wp(["WS-001"]),
            ["WS-001", "WS-002", "WS-003"],
        )
        assert findings == []

    def test_no_ws_index_key_passes(self):
        wp = {"wp_id": "WP-001", "title": "Test"}
        findings = check_ws_referential_integrity(wp, [])
        assert findings == []

    def test_finding_is_structured(self):
        findings = check_ws_referential_integrity(
            _wp(["WS-001"]), []
        )
        assert len(findings) == 1
        f = findings[0]
        assert isinstance(f, StabilizationFinding)
        assert f.field_path == "ws_index"
        assert f.remediation_hint is not None

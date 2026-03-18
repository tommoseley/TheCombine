"""Tier-1 tests for WP stabilization certification gate.

Verifies that WP stabilization is blocked when:
- No WSs exist
- WP governance floor is missing
- Any WS governance floor is missing

Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_crud_service import certify_wp_for_stabilization


def _wp(policy_refs=None):
    """Build a minimal WP content dict."""
    return {
        "wp_id": "WP-001",
        "title": "Test WP",
        "governance_pins": {
            "ta_version_id": "TA-v1.0",
            "policy_refs": policy_refs if policy_refs is not None else ["POL-ADR-EXEC-001"],
            "adr_refs": [],
        },
    }


def _ws(ws_id="WS-001", policy_refs=None):
    """Build a minimal WS content dict."""
    return {
        "ws_id": ws_id,
        "title": "Test WS",
        "objective": "Test",
        "governance_pins": {
            "ta_version_id": "TA-v1.0",
            "policy_refs": policy_refs if policy_refs is not None else ["POL-WS-001"],
            "adr_refs": [],
        },
    }


# =========================================================================
# Completeness checks
# =========================================================================


class TestCompleteness:
    """WP must have at least one WS to stabilize."""

    def test_no_ws_fails(self):
        errors = certify_wp_for_stabilization(_wp(), [])
        assert any("no Work Statements" in e for e in errors)

    def test_one_ws_passes_completeness(self):
        errors = certify_wp_for_stabilization(_wp(), [_ws()])
        assert not any("no Work Statements" in e for e in errors)

    def test_multiple_ws_passes(self):
        errors = certify_wp_for_stabilization(
            _wp(), [_ws("WS-001"), _ws("WS-002")]
        )
        assert not any("no Work Statements" in e for e in errors)


# =========================================================================
# WP governance checks
# =========================================================================


class TestWPGovernance:
    """WP must have POL-ADR-EXEC-001 in governance_pins."""

    def test_wp_missing_governance_pins_fails(self):
        wp = {"wp_id": "WP-001", "title": "Test"}
        errors = certify_wp_for_stabilization(wp, [_ws()])
        assert any("POL-ADR-EXEC-001" in e for e in errors)

    def test_wp_empty_policy_refs_fails(self):
        errors = certify_wp_for_stabilization(_wp(policy_refs=[]), [_ws()])
        assert any("POL-ADR-EXEC-001" in e for e in errors)

    def test_wp_wrong_policy_fails(self):
        errors = certify_wp_for_stabilization(_wp(policy_refs=["POL-QA-001"]), [_ws()])
        assert any("POL-ADR-EXEC-001" in e for e in errors)

    def test_wp_correct_policy_passes(self):
        errors = certify_wp_for_stabilization(_wp(), [_ws()])
        wp_errors = [e for e in errors if "WP" in e and "POL-ADR-EXEC-001" in e]
        assert len(wp_errors) == 0


# =========================================================================
# WS governance checks
# =========================================================================


class TestWSGovernance:
    """Each WS must have POL-WS-001 in governance_pins."""

    def test_ws_missing_governance_pins_fails(self):
        ws = {"ws_id": "WS-001", "title": "Test"}
        errors = certify_wp_for_stabilization(_wp(), [ws])
        assert any("WS-001" in e and "POL-WS-001" in e for e in errors)

    def test_ws_empty_policy_refs_fails(self):
        errors = certify_wp_for_stabilization(_wp(), [_ws(policy_refs=[])])
        assert any("POL-WS-001" in e for e in errors)

    def test_ws_correct_policy_passes(self):
        errors = certify_wp_for_stabilization(_wp(), [_ws()])
        ws_errors = [e for e in errors if "POL-WS-001" in e]
        assert len(ws_errors) == 0

    def test_one_bad_ws_among_good_fails(self):
        errors = certify_wp_for_stabilization(
            _wp(),
            [_ws("WS-001"), _ws("WS-002", policy_refs=[])],
        )
        assert any("WS-002" in e for e in errors)
        # WS-001 should not appear as a failing WS (only WS-002 fails)
        assert not any(e.startswith("WS WS-001") for e in errors)


# =========================================================================
# Full pass
# =========================================================================


class TestFullPass:
    """Valid WP + WSs pass all checks."""

    def test_valid_set_returns_no_errors(self):
        errors = certify_wp_for_stabilization(
            _wp(), [_ws("WS-001"), _ws("WS-002")]
        )
        assert errors == []

    def test_returns_list(self):
        result = certify_wp_for_stabilization(_wp(), [_ws()])
        assert isinstance(result, list)

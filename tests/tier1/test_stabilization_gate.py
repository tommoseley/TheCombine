"""Tier-1 tests for WP stabilization certification gate.

Verifies that WP stabilization is blocked when:
- No WSs exist
- WP governance floor is missing
- Any WS governance floor is missing

Returns structured StabilizationFinding objects.
Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_crud_service import (
    StabilizationFinding,
    certify_wp_for_stabilization,
)


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
        findings = certify_wp_for_stabilization(_wp(), [])
        assert any(f.rule_id == "CERT-001" for f in findings)

    def test_one_ws_passes_completeness(self):
        findings = certify_wp_for_stabilization(_wp(), [_ws()])
        assert not any(f.rule_id == "CERT-001" for f in findings)

    def test_multiple_ws_passes(self):
        findings = certify_wp_for_stabilization(
            _wp(), [_ws("WS-001"), _ws("WS-002")]
        )
        assert not any(f.rule_id == "CERT-001" for f in findings)


# =========================================================================
# WP governance checks
# =========================================================================


class TestWPGovernance:
    """WP must have POL-ADR-EXEC-001 in governance_pins."""

    def test_wp_missing_governance_pins_fails(self):
        wp = {"wp_id": "WP-001", "title": "Test"}
        findings = certify_wp_for_stabilization(wp, [_ws()])
        assert any(f.rule_id == "CERT-002" for f in findings)

    def test_wp_empty_policy_refs_fails(self):
        findings = certify_wp_for_stabilization(_wp(policy_refs=[]), [_ws()])
        assert any(f.rule_id == "CERT-002" for f in findings)

    def test_wp_wrong_policy_fails(self):
        findings = certify_wp_for_stabilization(_wp(policy_refs=["POL-QA-001"]), [_ws()])
        cert2 = [f for f in findings if f.rule_id == "CERT-002"]
        assert len(cert2) == 1
        assert "POL-ADR-EXEC-001" in cert2[0].message

    def test_wp_correct_policy_passes(self):
        findings = certify_wp_for_stabilization(_wp(), [_ws()])
        assert not any(f.rule_id == "CERT-002" for f in findings)


# =========================================================================
# WS governance checks
# =========================================================================


class TestWSGovernance:
    """Each WS must have POL-WS-001 in governance_pins."""

    def test_ws_missing_governance_pins_fails(self):
        ws = {"ws_id": "WS-001", "title": "Test"}
        findings = certify_wp_for_stabilization(_wp(), [ws])
        cert3 = [f for f in findings if f.rule_id == "CERT-003"]
        assert len(cert3) == 1
        assert cert3[0].artifact_id == "WS-001"

    def test_ws_empty_policy_refs_fails(self):
        findings = certify_wp_for_stabilization(_wp(), [_ws(policy_refs=[])])
        assert any(f.rule_id == "CERT-003" for f in findings)

    def test_ws_correct_policy_passes(self):
        findings = certify_wp_for_stabilization(_wp(), [_ws()])
        assert not any(f.rule_id == "CERT-003" for f in findings)

    def test_one_bad_ws_among_good_fails(self):
        findings = certify_wp_for_stabilization(
            _wp(),
            [_ws("WS-001"), _ws("WS-002", policy_refs=[])],
        )
        cert3 = [f for f in findings if f.rule_id == "CERT-003"]
        assert len(cert3) == 1
        assert cert3[0].artifact_id == "WS-002"


# =========================================================================
# Structured finding shape
# =========================================================================


class TestFindingShape:
    """Findings are StabilizationFinding with all required fields."""

    def test_finding_has_all_fields(self):
        findings = certify_wp_for_stabilization(_wp(policy_refs=[]), [_ws()])
        f = findings[0]
        assert isinstance(f, StabilizationFinding)
        assert f.rule_id is not None
        assert f.artifact_id is not None
        assert f.message is not None
        assert f.remediation_hint is not None

    def test_to_dict(self):
        findings = certify_wp_for_stabilization(_wp(policy_refs=[]), [_ws()])
        d = findings[0].to_dict()
        assert "rule_id" in d
        assert "artifact_id" in d
        assert "field_path" in d
        assert "message" in d
        assert "remediation_hint" in d

    def test_valid_set_returns_empty_list(self):
        findings = certify_wp_for_stabilization(
            _wp(), [_ws("WS-001"), _ws("WS-002")]
        )
        assert findings == []

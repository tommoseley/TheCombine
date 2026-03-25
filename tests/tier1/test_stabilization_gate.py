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
    check_blocking_unknowns,
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


# =========================================================================
# Blocking unknowns gate (WS-PI-UNK)
# =========================================================================


def _pd(unknowns=None):
    """Build a minimal PD content dict with unknowns."""
    return {
        "project_name": "Test Project",
        "unknowns": unknowns or [],
    }


def _unk(unk_id="UNK-1", blocking=False, resolved=False, question="Some question?"):
    """Build a single unknown entry."""
    entry = {
        "id": unk_id,
        "question": question,
        "why_it_matters": "Matters for testing",
        "impact_if_unresolved": "Tests may fail",
        "blocking": blocking,
    }
    if resolved:
        entry["resolved"] = True
    return entry


class TestBlockingUnknowns:
    """WP stabilization must be blocked by unresolved blocking unknowns in PD."""

    def test_no_pd_passes(self):
        """No PD document at all — no findings."""
        assert check_blocking_unknowns(None) == []

    def test_empty_unknowns_passes(self):
        findings = check_blocking_unknowns(_pd([]))
        assert findings == []

    def test_advisory_unknowns_pass(self):
        """Non-blocking unknowns do not block stabilization."""
        pd = _pd([_unk("UNK-1", blocking=False)])
        assert check_blocking_unknowns(pd) == []

    def test_blocking_unknown_fails(self):
        """Unresolved blocking unknown blocks stabilization."""
        pd = _pd([_unk("UNK-1", blocking=True)])
        findings = check_blocking_unknowns(pd)
        assert len(findings) == 1
        assert findings[0].rule_id == "UNK-BLOCK-001"
        assert findings[0].artifact_id == "UNK-1"

    def test_resolved_blocking_unknown_passes(self):
        """Blocking unknown that is resolved does not block."""
        pd = _pd([_unk("UNK-1", blocking=True, resolved=True)])
        assert check_blocking_unknowns(pd) == []

    def test_mixed_unknowns(self):
        """Only unresolved blocking unknowns produce findings."""
        pd = _pd([
            _unk("UNK-1", blocking=False),
            _unk("UNK-2", blocking=True),
            _unk("UNK-3", blocking=True, resolved=True),
            _unk("UNK-4", blocking=True),
        ])
        findings = check_blocking_unknowns(pd)
        assert len(findings) == 2
        ids = {f.artifact_id for f in findings}
        assert ids == {"UNK-2", "UNK-4"}

    def test_finding_includes_question(self):
        """Finding message includes the unknown's question text."""
        pd = _pd([_unk("UNK-1", blocking=True, question="What is the API version?")])
        findings = check_blocking_unknowns(pd)
        assert "What is the API version?" in findings[0].message

    def test_finding_shape(self):
        """Finding has all required StabilizationFinding fields."""
        pd = _pd([_unk("UNK-1", blocking=True)])
        f = check_blocking_unknowns(pd)[0]
        assert isinstance(f, StabilizationFinding)
        d = f.to_dict()
        assert "rule_id" in d
        assert "artifact_id" in d
        assert "field_path" in d
        assert "message" in d
        assert "remediation_hint" in d

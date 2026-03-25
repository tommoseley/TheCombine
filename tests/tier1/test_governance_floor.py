"""Tier-1 tests for ensure_governance_floor() — mechanical governance enforcement.

Pure unit tests — no DB, no LLM calls.
Tests the deterministic governance floor for WP and WS artifact types.
"""

from app.domain.services.work_statement_registration import ensure_governance_floor


# =========================================================================
# WP governance floor
# =========================================================================


class TestWPGovernanceFloor:
    """Work Package governance floor enforcement."""

    def test_empty_policy_refs_gets_floor(self):
        """WP with empty policy_refs gets POL-ADR-EXEC-001."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_package")
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]

    def test_missing_policy_refs_gets_floor(self):
        """WP with no policy_refs key gets POL-ADR-EXEC-001."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
            }
        }
        result = ensure_governance_floor(data, "work_package")
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]

    def test_existing_policy_refs_preserved(self):
        """WP with existing policy_refs keeps them and adds floor if missing."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": ["POL-QA-001"],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_package")
        assert "POL-QA-001" in result["governance_pins"]["policy_refs"]
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]

    def test_floor_already_present_no_duplicate(self):
        """WP already containing the floor policy does not get a duplicate."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": ["POL-ADR-EXEC-001", "POL-QA-001"],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_package")
        count = result["governance_pins"]["policy_refs"].count("POL-ADR-EXEC-001")
        assert count == 1

    def test_wp_does_not_get_ws_policy(self):
        """WP floor does NOT include POL-WS-001 (that's WS-specific)."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_package")
        assert "POL-WS-001" not in result["governance_pins"]["policy_refs"]

    def test_missing_governance_pins_creates_structure(self):
        """WP with no governance_pins at all gets the full structure."""
        data = {}
        result = ensure_governance_floor(data, "work_package")
        assert "governance_pins" in result
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]

    def test_does_not_touch_adr_refs(self):
        """Floor enforcement does not invent adr_refs — that's the LLM's job."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_package")
        assert result["governance_pins"]["adr_refs"] == []


# =========================================================================
# WS governance floor
# =========================================================================


class TestWSGovernanceFloor:
    """Work Statement governance floor enforcement."""

    def test_empty_policy_refs_gets_floor(self):
        """WS with empty policy_refs gets POL-WS-001."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_statement")
        assert "POL-WS-001" in result["governance_pins"]["policy_refs"]

    def test_ws_does_not_get_wp_floor_policy(self):
        """WS floor does NOT inject POL-ADR-EXEC-001 (that's WP-level)."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_statement")
        assert "POL-ADR-EXEC-001" not in result["governance_pins"]["policy_refs"]

    def test_inherited_wp_refs_preserved(self):
        """WS with inherited WP policy_refs keeps them and adds WS floor."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": ["POL-ADR-EXEC-001", "POL-QA-001"],
                "adr_refs": ["ADR-009"],
            }
        }
        result = ensure_governance_floor(data, "work_statement")
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]
        assert "POL-QA-001" in result["governance_pins"]["policy_refs"]
        assert "POL-WS-001" in result["governance_pins"]["policy_refs"]
        assert "ADR-009" in result["governance_pins"]["adr_refs"]


# =========================================================================
# Unknown artifact type
# =========================================================================


class TestUnknownArtifactType:
    """Unknown artifact types get no floor injection — data passes through."""

    def test_unknown_type_no_injection(self):
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "technical_architecture")
        assert result["governance_pins"]["policy_refs"] == []

    def test_returns_same_dict(self):
        """Function modifies in place and returns the same dict."""
        data = {
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = ensure_governance_floor(data, "work_package")
        assert result is data

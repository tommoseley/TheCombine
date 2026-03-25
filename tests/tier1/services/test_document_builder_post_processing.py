"""Tier-1 tests for apply_post_processing() — governance floor wiring.

Verifies that the DocumentBuilder post-processing step applies the
governance floor to WP and WS artifacts before persistence.

Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.document_builder_pure import apply_post_processing


# =========================================================================
# WP post-processing
# =========================================================================


class TestWPPostProcessing:
    """Work Package governance floor applied via post-processing."""

    def test_wp_empty_pins_gets_floor(self):
        """WP with empty policy_refs gets POL-ADR-EXEC-001 after post-processing."""
        data = {
            "wp_id": "test_wp",
            "title": "Test WP",
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            },
        }
        result = apply_post_processing(data, "work_package")
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]

    def test_wp_no_governance_pins_gets_structure(self):
        """WP with no governance_pins at all gets full structure after post-processing."""
        data = {"wp_id": "test_wp", "title": "Test WP"}
        result = apply_post_processing(data, "work_package")
        assert "governance_pins" in result
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]

    def test_wp_existing_refs_preserved(self):
        """WP with existing policy_refs keeps them and adds floor."""
        data = {
            "governance_pins": {
                "policy_refs": ["POL-QA-001"],
                "adr_refs": ["ADR-009"],
            }
        }
        result = apply_post_processing(data, "work_package")
        assert "POL-QA-001" in result["governance_pins"]["policy_refs"]
        assert "POL-ADR-EXEC-001" in result["governance_pins"]["policy_refs"]
        assert "ADR-009" in result["governance_pins"]["adr_refs"]


# =========================================================================
# WS post-processing
# =========================================================================


class TestWSPostProcessing:
    """Work Statement governance floor applied via post-processing."""

    def test_ws_empty_pins_gets_floor(self):
        """WS with empty policy_refs gets POL-WS-001 after post-processing."""
        data = {
            "objective": "Test",
            "governance_pins": {
                "ta_version_id": "TA-v1.0",
                "policy_refs": [],
                "adr_refs": [],
            },
        }
        result = apply_post_processing(data, "work_statement")
        assert "POL-WS-001" in result["governance_pins"]["policy_refs"]

    def test_ws_does_not_get_wp_floor(self):
        """WS floor is POL-WS-001, not POL-ADR-EXEC-001."""
        data = {
            "governance_pins": {
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = apply_post_processing(data, "work_statement")
        assert "POL-WS-001" in result["governance_pins"]["policy_refs"]
        assert "POL-ADR-EXEC-001" not in result["governance_pins"]["policy_refs"]


# =========================================================================
# Non-governed artifact types
# =========================================================================


class TestNonGovernedTypes:
    """Non-governed artifact types pass through unchanged."""

    def test_ta_no_floor_injection(self):
        """Technical architecture gets no governance floor injection."""
        data = {
            "governance_pins": {
                "policy_refs": [],
                "adr_refs": [],
            }
        }
        result = apply_post_processing(data, "technical_architecture")
        assert result["governance_pins"]["policy_refs"] == []

    def test_unknown_type_passthrough(self):
        """Unknown document types pass through unchanged."""
        data = {"title": "Test", "content": "stuff"}
        result = apply_post_processing(data, "intake_form")
        assert result == {"title": "Test", "content": "stuff"}

    def test_returns_same_dict(self):
        """Post-processing mutates in place and returns the same dict."""
        data = {"governance_pins": {"policy_refs": []}}
        result = apply_post_processing(data, "work_package")
        assert result is data

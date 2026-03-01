"""
Tests for Work Binder governance invariant enforcement — WS-WB-008.

Tests the pure governance validator functions that enforce hard rules:
- Cannot create WS when ta_version_id is "pending"
- Cannot promote without transformation metadata
- Cannot reorder on DONE WP
- All mutations require provenance (non-empty actor)
"""


from app.domain.services.wb_audit_service import (
    validate_can_create_ws,
    validate_can_promote,
    validate_can_reorder,
    validate_provenance,
)


# ===========================================================================
# validate_can_create_ws
# ===========================================================================


class TestValidateCanCreateWS:
    """Test: WS creation blocked when TA review is pending."""

    def test_rejects_when_ta_version_id_is_pending(self):
        wp_content = {
            "wp_id": "wp_wb_001",
            "governance_pins": {"ta_version_id": "pending"},
        }
        errors = validate_can_create_ws(wp_content)
        assert len(errors) == 1
        assert "pending" in errors[0]
        assert "Technical Architect" in errors[0]

    def test_allows_when_ta_version_id_is_set(self):
        wp_content = {
            "wp_id": "wp_wb_001",
            "governance_pins": {"ta_version_id": "v1.0"},
        }
        errors = validate_can_create_ws(wp_content)
        assert errors == []

    def test_allows_when_ta_version_id_is_none(self):
        """None is different from 'pending' — absent TA pin is allowed."""
        wp_content = {
            "wp_id": "wp_wb_001",
            "governance_pins": {"ta_version_id": None},
        }
        errors = validate_can_create_ws(wp_content)
        assert errors == []

    def test_allows_when_governance_pins_missing(self):
        """No governance_pins at all — no ta_version_id to check."""
        wp_content = {"wp_id": "wp_wb_001"}
        errors = validate_can_create_ws(wp_content)
        assert errors == []

    def test_allows_when_governance_pins_empty(self):
        wp_content = {
            "wp_id": "wp_wb_001",
            "governance_pins": {},
        }
        errors = validate_can_create_ws(wp_content)
        assert errors == []

    def test_allows_when_ta_version_id_is_uuid(self):
        wp_content = {
            "wp_id": "wp_wb_001",
            "governance_pins": {
                "ta_version_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            },
        }
        errors = validate_can_create_ws(wp_content)
        assert errors == []


# ===========================================================================
# validate_can_promote
# ===========================================================================


class TestValidateCanPromote:
    """Test: promotion requires transformation metadata."""

    def test_rejects_empty_transformation(self):
        errors = validate_can_promote("", "Some notes")
        assert any("transformation is required" in e for e in errors)

    def test_rejects_whitespace_transformation(self):
        errors = validate_can_promote("   ", "Some notes")
        assert any("transformation is required" in e for e in errors)

    def test_rejects_empty_transformation_notes(self):
        errors = validate_can_promote("kept", "")
        assert any("transformation_notes is required" in e for e in errors)

    def test_rejects_whitespace_transformation_notes(self):
        errors = validate_can_promote("kept", "   ")
        assert any("transformation_notes is required" in e for e in errors)

    def test_rejects_both_empty(self):
        errors = validate_can_promote("", "")
        assert len(errors) == 2

    def test_allows_valid_transformation_and_notes(self):
        errors = validate_can_promote("kept", "Kept as-is from IP")
        assert errors == []

    def test_allows_all_valid_transformations(self):
        for t in ("kept", "split", "merged", "added"):
            errors = validate_can_promote(t, f"Applied {t} transformation")
            assert errors == [], f"Failed for transformation '{t}'"


# ===========================================================================
# validate_can_reorder
# ===========================================================================


class TestValidateCanReorder:
    """Test: reordering blocked on DONE WPs."""

    def test_rejects_reorder_on_done_wp(self):
        wp_content = {"wp_id": "wp_wb_001", "state": "DONE"}
        errors = validate_can_reorder(wp_content)
        assert len(errors) == 1
        assert "DONE" in errors[0]

    def test_allows_reorder_on_planned_wp(self):
        wp_content = {"wp_id": "wp_wb_001", "state": "PLANNED"}
        errors = validate_can_reorder(wp_content)
        assert errors == []

    def test_allows_reorder_on_in_progress_wp(self):
        wp_content = {"wp_id": "wp_wb_001", "state": "IN_PROGRESS"}
        errors = validate_can_reorder(wp_content)
        assert errors == []

    def test_allows_reorder_when_state_missing(self):
        wp_content = {"wp_id": "wp_wb_001"}
        errors = validate_can_reorder(wp_content)
        assert errors == []

    def test_allows_reorder_on_empty_state(self):
        wp_content = {"wp_id": "wp_wb_001", "state": ""}
        errors = validate_can_reorder(wp_content)
        assert errors == []


# ===========================================================================
# validate_provenance
# ===========================================================================


class TestValidateProvenance:
    """Test: all mutations must have provenance (non-empty actor)."""

    def test_rejects_empty_actor(self):
        errors = validate_provenance("")
        assert len(errors) == 1
        assert "actor must be non-empty" in errors[0]

    def test_rejects_whitespace_actor(self):
        errors = validate_provenance("   ")
        assert len(errors) == 1
        assert "actor must be non-empty" in errors[0]

    def test_accepts_system_actor(self):
        errors = validate_provenance("system")
        assert errors == []

    def test_accepts_named_actor(self):
        errors = validate_provenance("tom")
        assert errors == []

    def test_accepts_service_actor(self):
        errors = validate_provenance("promotion-service")
        assert errors == []

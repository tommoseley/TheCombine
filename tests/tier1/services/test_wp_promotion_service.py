"""Tests for WP Promotion Service (WS-WB-004).

Tier-1 tests for wp_promotion_service:
- validate_promotion_request: transformation validation
- build_promoted_wp: WPC candidate -> governed WP transformation
- build_audit_event: audit event structure
- derive_wp_id: deterministic wp_id from wpc_id

Pure business logic -- no DB, no handlers, no external dependencies.
"""

import copy
from datetime import datetime

from app.domain.services.wp_promotion_service import (
    VALID_TRANSFORMATIONS,
    build_audit_event,
    build_promoted_wp,
    derive_wp_id,
    validate_promotion_request,
)


# ---------------------------------------------------------------------------
# Fixtures -- baseline WPC candidate content
# ---------------------------------------------------------------------------


def _wpc_candidate() -> dict:
    """A baseline WPC candidate document content (as stored in DB)."""
    return {
        "wpc_id": "WPC-001",
        "title": "Registry Service",
        "rationale": "Centralize handler registration",
        "scope_summary": ["handler registry", "config loading"],
        "source_ip_id": "ip-doc-abc",
        "source_ip_version": "1",
        "frozen_at": "2026-03-01T10:00:00+00:00",
        "frozen_by": "system",
    }


def _wpc_candidate_002() -> dict:
    """A second WPC candidate for testing different IDs."""
    return {
        "wpc_id": "WPC-002",
        "title": "Schema Validation",
        "rationale": "Enforce output schemas",
        "scope_summary": ["schema validation"],
        "source_ip_id": "ip-doc-abc",
        "source_ip_version": "1",
        "frozen_at": "2026-03-01T10:00:00+00:00",
        "frozen_by": "system",
    }


def _wpc_candidate_high_number() -> dict:
    """A WPC with a high-number ID for derivation edge case."""
    return {
        "wpc_id": "WPC-1234",
        "title": "Large Number Package",
        "rationale": "Test high numbering",
        "scope_summary": ["testing"],
        "source_ip_id": "ip-doc-xyz",
        "source_ip_version": "2",
        "frozen_at": "2026-03-01T12:00:00+00:00",
        "frozen_by": "tom",
    }


# ===========================================================================
# derive_wp_id tests
# ===========================================================================


class TestDeriveWpId:
    """Tests for derive_wp_id()."""

    def test_basic_derivation(self):
        """WPC-001 -> wp_wb_001."""
        assert derive_wp_id("WPC-001") == "wp_wb_001"

    def test_derivation_002(self):
        """WPC-002 -> wp_wb_002."""
        assert derive_wp_id("WPC-002") == "wp_wb_002"

    def test_derivation_high_number(self):
        """WPC-1234 -> wp_wb_1234."""
        assert derive_wp_id("WPC-1234") == "wp_wb_1234"

    def test_result_is_valid_snake_case(self):
        """Derived wp_id matches snake_case pattern ^[a-z][a-z0-9_]*$."""
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for wpc_id in ["WPC-001", "WPC-002", "WPC-100", "WPC-1234"]:
            wp_id = derive_wp_id(wpc_id)
            assert pattern.match(wp_id), f"{wp_id} is not valid snake_case"

    def test_derivation_is_deterministic(self):
        """Same wpc_id always produces same wp_id."""
        assert derive_wp_id("WPC-001") == derive_wp_id("WPC-001")

    def test_different_wpc_ids_produce_different_wp_ids(self):
        """Different wpc_ids produce different wp_ids."""
        assert derive_wp_id("WPC-001") != derive_wp_id("WPC-002")


# ===========================================================================
# validate_promotion_request tests
# ===========================================================================


class TestValidatePromotionRequest:
    """Tests for validate_promotion_request()."""

    def test_valid_kept(self):
        """'kept' is a valid transformation."""
        errors = validate_promotion_request("kept")
        assert errors == []

    def test_valid_split(self):
        """'split' is a valid transformation."""
        errors = validate_promotion_request("split")
        assert errors == []

    def test_valid_merged(self):
        """'merged' is a valid transformation."""
        errors = validate_promotion_request("merged")
        assert errors == []

    def test_valid_added(self):
        """'added' is a valid transformation."""
        errors = validate_promotion_request("added")
        assert errors == []

    def test_invalid_transformation(self):
        """Unknown transformation returns error."""
        errors = validate_promotion_request("deleted")
        assert len(errors) == 1
        assert "deleted" in errors[0]

    def test_empty_transformation(self):
        """Empty string transformation returns error."""
        errors = validate_promotion_request("")
        assert len(errors) >= 1

    def test_returns_list(self):
        """Return type is always a list."""
        assert isinstance(validate_promotion_request("kept"), list)
        assert isinstance(validate_promotion_request("invalid"), list)


# ===========================================================================
# build_promoted_wp tests
# ===========================================================================


class TestBuildPromotedWp:
    """Tests for build_promoted_wp()."""

    def test_wp_id_derived_from_wpc_id(self):
        """wp_id is derived from the candidate's wpc_id."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["wp_id"] == "wp_wb_001"

    def test_title_from_candidate(self):
        """Title comes from candidate by default."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["title"] == "Registry Service"

    def test_title_override(self):
        """title_override replaces the candidate title."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(
            candidate, "kept", "Kept as-is",
            title_override="New Title",
        )
        assert result["title"] == "New Title"

    def test_rationale_from_candidate(self):
        """Rationale comes from candidate by default."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["rationale"] == "Centralize handler registration"

    def test_rationale_override(self):
        """rationale_override replaces the candidate rationale."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(
            candidate, "kept", "Kept as-is",
            rationale_override="Better rationale",
        )
        assert result["rationale"] == "Better rationale"

    def test_state_is_planned(self):
        """Promoted WP state is always PLANNED."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["state"] == "PLANNED"

    def test_ws_index_is_empty_list(self):
        """Promoted WP ws_index starts empty."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["ws_index"] == []

    def test_revision_edition_is_1(self):
        """Promoted WP revision edition starts at 1."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["revision"]["edition"] == 1

    def test_source_candidate_ids_contains_wpc_id(self):
        """source_candidate_ids contains the source WPC ID."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["source_candidate_ids"] == ["WPC-001"]

    def test_transformation_is_set(self):
        """transformation field is set from argument."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "split", "Split into two")
        assert result["transformation"] == "split"

    def test_transformation_notes_is_set(self):
        """transformation_notes field is set from argument."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "No changes needed")
        assert result["transformation_notes"] == "No changes needed"

    def test_lineage_parent_document_type(self):
        """_lineage.parent_document_type is work_package_candidate."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["_lineage"]["parent_document_type"] == "work_package_candidate"

    def test_lineage_source_candidate_ids(self):
        """_lineage.source_candidate_ids contains the WPC ID."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["_lineage"]["source_candidate_ids"] == ["WPC-001"]

    def test_lineage_transformation(self):
        """_lineage.transformation matches the transformation argument."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "merged", "Merged with another")
        assert result["_lineage"]["transformation"] == "merged"

    def test_lineage_transformation_notes(self):
        """_lineage.transformation_notes matches the notes argument."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Some notes here")
        assert result["_lineage"]["transformation_notes"] == "Some notes here"

    def test_governance_pins_ta_version_pending(self):
        """governance_pins.ta_version_id is 'pending' at promotion time."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["governance_pins"]["ta_version_id"] == "pending"

    def test_scope_in_from_candidate_scope_summary(self):
        """scope_in is populated from the candidate's scope_summary."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["scope_in"] == ["handler registry", "config loading"]

    def test_scope_out_is_empty_list(self):
        """scope_out starts as empty list (refined later)."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["scope_out"] == []

    def test_dependencies_is_empty_list(self):
        """dependencies starts as empty list (populated during WS drafting)."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert result["dependencies"] == []

    def test_definition_of_done_has_default(self):
        """definition_of_done has at least one entry."""
        candidate = _wpc_candidate()
        result = build_promoted_wp(candidate, "kept", "Kept as-is")
        assert isinstance(result["definition_of_done"], list)
        assert len(result["definition_of_done"]) >= 1

    def test_does_not_mutate_candidate(self):
        """build_promoted_wp does not mutate the input candidate dict."""
        candidate = _wpc_candidate()
        original = copy.deepcopy(candidate)
        build_promoted_wp(candidate, "kept", "Kept as-is")
        assert candidate == original

    def test_different_candidates_produce_different_wp_ids(self):
        """Different WPC candidates produce different wp_ids."""
        result_1 = build_promoted_wp(_wpc_candidate(), "kept", "Notes")
        result_2 = build_promoted_wp(_wpc_candidate_002(), "kept", "Notes")
        assert result_1["wp_id"] != result_2["wp_id"]

    def test_each_transformation_type_accepted(self):
        """All four valid transformations work without error."""
        candidate = _wpc_candidate()
        for xform in VALID_TRANSFORMATIONS:
            result = build_promoted_wp(candidate, xform, f"Testing {xform}")
            assert result["transformation"] == xform


# ===========================================================================
# build_audit_event tests
# ===========================================================================


class TestBuildAuditEvent:
    """Tests for build_audit_event()."""

    def test_event_type(self):
        """Audit event type is 'wp_promotion'."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "tom")
        assert event["event_type"] == "wp_promotion"

    def test_wpc_id_in_event(self):
        """wpc_id is recorded in the audit event."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "tom")
        assert event["wpc_id"] == "WPC-001"

    def test_wp_id_in_event(self):
        """wp_id is recorded in the audit event."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "tom")
        assert event["wp_id"] == "wp_wb_001"

    def test_transformation_in_event(self):
        """transformation is recorded in the audit event."""
        event = build_audit_event("WPC-001", "wp_wb_001", "split", "tom")
        assert event["transformation"] == "split"

    def test_promoted_by_in_event(self):
        """promoted_by is recorded in the audit event."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "tom")
        assert event["promoted_by"] == "tom"

    def test_timestamp_present(self):
        """Audit event has a timestamp field."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "tom")
        assert "timestamp" in event

    def test_timestamp_is_iso_format(self):
        """Audit event timestamp is a parseable ISO datetime."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "tom")
        dt = datetime.fromisoformat(event["timestamp"])
        assert dt.tzinfo is not None

    def test_event_has_required_fields(self):
        """Audit event has all required fields."""
        event = build_audit_event("WPC-001", "wp_wb_001", "kept", "system")
        required = {"event_type", "wpc_id", "wp_id", "transformation", "promoted_by", "timestamp"}
        assert required.issubset(set(event.keys()))

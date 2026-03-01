"""Tests for WP Edition Tracking + Change Summary (WS-WB-005).

Tier-1 tests for wp_edition_service:
- compute_change_summary: mechanical diff of WP-level fields
- apply_edition_bump: edition increment + change_summary population
- get_edition_history: reverse chronological ordering

Pure business logic — no DB, no handlers, no external dependencies.
"""

import copy

from app.domain.services.wp_edition_service import (
    WP_LEVEL_FIELDS,
    compute_change_summary,
    apply_edition_bump,
    get_edition_history,
)


# ---------------------------------------------------------------------------
# Fixtures — baseline WP content
# ---------------------------------------------------------------------------

def _base_wp() -> dict:
    """Minimal valid WP content with all WP-level fields populated."""
    return {
        "wp_id": "wp_registry",
        "title": "Registry Service",
        "rationale": "Centralize handler registration",
        "scope_in": ["handler registry", "config loading"],
        "scope_out": ["UI components"],
        "dependencies": [
            {"wp_id": "wp_schema", "dependency_type": "must_complete_first"}
        ],
        "definition_of_done": ["All handlers registered", "Tier-1 tests pass"],
        "governance_pins": {
            "ta_version_id": "v2.1",
            "adr_refs": ["ADR-051"],
            "policy_refs": ["POL-WS-001"],
        },
        "ws_index": [
            {"ws_id": "WS-REG-001", "order_key": "a0"},
            {"ws_id": "WS-REG-002", "order_key": "a1"},
        ],
        "state": "PLANNED",
        "source_candidate_ids": ["WPC-001"],
        "transformation": "kept",
        "transformation_notes": "Direct promotion from IP candidate",
        # Revision metadata
        "revision": {"edition": 1, "updated_at": "2026-03-01T10:00:00Z", "updated_by": "tom"},
        "change_summary": [],
        # Excluded (non-WP-level) fields
        "ws_child_refs": ["WS-REG-001", "WS-REG-002"],
        "ws_total": 2,
        "ws_done": 0,
        "mode_b_count": 0,
    }


# ===========================================================================
# compute_change_summary tests
# ===========================================================================

class TestComputeChangeSummary:
    """Tests for compute_change_summary()."""

    def test_no_changes_returns_empty_list(self):
        """Identical WP-level fields produce no change entries."""
        old = _base_wp()
        new = copy.deepcopy(old)
        result = compute_change_summary(old, new)
        assert result == []

    def test_title_change(self):
        """Scalar string field change produces 'field: old -> new' entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "Handler Registry Service"
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "title:" in result[0]
        assert "'Registry Service'" in result[0]
        assert "'Handler Registry Service'" in result[0]

    def test_state_change(self):
        """State transition produces descriptive entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["state"] = "READY"
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "state:" in result[0]
        assert "PLANNED" in result[0]
        assert "READY" in result[0]

    def test_ws_index_added_ws(self):
        """Adding a WS to ws_index produces 'added' entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["ws_index"].append({"ws_id": "WS-REG-003", "order_key": "a2"})
        result = compute_change_summary(old, new)
        assert any("ws_index:" in entry and "added" in entry and "WS-REG-003" in entry for entry in result)

    def test_ws_index_removed_ws(self):
        """Removing a WS from ws_index produces 'removed' entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["ws_index"] = [{"ws_id": "WS-REG-001", "order_key": "a0"}]
        result = compute_change_summary(old, new)
        assert any("ws_index:" in entry and "removed" in entry and "WS-REG-002" in entry for entry in result)

    def test_dependencies_added(self):
        """Adding a dependency produces descriptive entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["dependencies"].append(
            {"wp_id": "wp_audit", "dependency_type": "can_start_after"}
        )
        result = compute_change_summary(old, new)
        assert any("dependencies:" in entry and "added" in entry and "wp_audit" in entry for entry in result)

    def test_dependencies_removed(self):
        """Removing a dependency produces descriptive entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["dependencies"] = []
        result = compute_change_summary(old, new)
        assert any("dependencies:" in entry and "removed" in entry and "wp_schema" in entry for entry in result)

    def test_scope_in_change(self):
        """Changing scope_in list produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["scope_in"] = ["handler registry", "config loading", "validation"]
        result = compute_change_summary(old, new)
        assert any("scope_in:" in entry and "added" in entry and "validation" in entry for entry in result)

    def test_scope_out_change(self):
        """Changing scope_out list produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["scope_out"] = []
        result = compute_change_summary(old, new)
        assert any("scope_out:" in entry and "removed" in entry and "UI components" in entry for entry in result)

    def test_excluded_fields_ignored(self):
        """Changes to ws_child_refs, ws_total, ws_done, mode_b_count produce no entries."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["ws_child_refs"] = ["WS-REG-001", "WS-REG-002", "WS-REG-003"]
        new["ws_total"] = 99
        new["ws_done"] = 50
        new["mode_b_count"] = 10
        result = compute_change_summary(old, new)
        assert result == []

    def test_multiple_changes_produce_multiple_entries(self):
        """Changing several WP-level fields produces one entry per changed field."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "New Title"
        new["state"] = "READY"
        new["rationale"] = "Updated rationale"
        result = compute_change_summary(old, new)
        assert len(result) == 3
        fields_mentioned = [entry.split(":")[0] for entry in result]
        assert "title" in fields_mentioned
        assert "state" in fields_mentioned
        assert "rationale" in fields_mentioned

    def test_governance_pins_change(self):
        """Changing governance_pins produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["governance_pins"]["ta_version_id"] = "v3.0"
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "governance_pins:" in result[0]

    def test_definition_of_done_change(self):
        """Changing definition_of_done produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["definition_of_done"].append("Integration tests pass")
        result = compute_change_summary(old, new)
        assert any("definition_of_done:" in entry for entry in result)

    def test_transformation_change(self):
        """Changing transformation produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["transformation"] = "split"
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "transformation:" in result[0]
        assert "'kept'" in result[0]
        assert "'split'" in result[0]

    def test_transformation_notes_change(self):
        """Changing transformation_notes produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["transformation_notes"] = "Split into two packages"
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "transformation_notes:" in result[0]

    def test_source_candidate_ids_change(self):
        """Changing source_candidate_ids produces change entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["source_candidate_ids"] = ["WPC-001", "WPC-002"]
        result = compute_change_summary(old, new)
        assert any("source_candidate_ids:" in entry and "added" in entry and "WPC-002" in entry for entry in result)

    def test_field_added_from_absent(self):
        """Adding a WP-level field that was previously absent produces entry."""
        old = _base_wp()
        del old["transformation_notes"]
        new = copy.deepcopy(old)
        new["transformation_notes"] = "New notes"
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "transformation_notes:" in result[0]

    def test_field_removed_to_absent(self):
        """Removing a WP-level field (set to None/absent) produces entry."""
        old = _base_wp()
        new = copy.deepcopy(old)
        del new["transformation_notes"]
        result = compute_change_summary(old, new)
        assert len(result) == 1
        assert "transformation_notes:" in result[0]

    def test_unknown_fields_ignored(self):
        """Fields not in WP_LEVEL_FIELDS are ignored even if they change."""
        old = _base_wp()
        new = copy.deepcopy(old)
        old["custom_field"] = "old_value"
        new["custom_field"] = "new_value"
        result = compute_change_summary(old, new)
        assert result == []


# ===========================================================================
# apply_edition_bump tests
# ===========================================================================

class TestApplyEditionBump:
    """Tests for apply_edition_bump()."""

    def test_no_wp_changes_returns_unchanged(self):
        """When only excluded fields change, content is returned unchanged."""
        content = _base_wp()
        old = copy.deepcopy(content)
        content["ws_total"] = 99  # excluded field
        result = apply_edition_bump(content, old, "claude")
        assert result["revision"]["edition"] == 1  # no bump
        assert result["change_summary"] == []

    def test_wp_change_increments_edition(self):
        """WP-level field change increments revision.edition."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "Updated Title"
        result = apply_edition_bump(new, old, "tom")
        assert result["revision"]["edition"] == 2

    def test_edition_bump_sets_updated_by(self):
        """Edition bump populates revision.updated_by."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["state"] = "READY"
        result = apply_edition_bump(new, old, "claude")
        assert result["revision"]["updated_by"] == "claude"

    def test_edition_bump_sets_updated_at(self):
        """Edition bump populates revision.updated_at with ISO timestamp."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["state"] = "READY"
        result = apply_edition_bump(new, old, "tom")
        assert result["revision"]["updated_at"] != old["revision"]["updated_at"]
        # Should be ISO format
        assert "T" in result["revision"]["updated_at"]

    def test_edition_bump_populates_change_summary(self):
        """Edition bump sets change_summary from computed diff."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "New Title"
        result = apply_edition_bump(new, old, "tom")
        assert len(result["change_summary"]) == 1
        assert "title:" in result["change_summary"][0]

    def test_multiple_changes_all_in_summary(self):
        """Multiple WP-level changes are all captured in change_summary."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "New Title"
        new["state"] = "READY"
        result = apply_edition_bump(new, old, "tom")
        assert result["revision"]["edition"] == 2
        assert len(result["change_summary"]) == 2

    def test_sequential_edition_bumps(self):
        """Multiple sequential bumps increment correctly."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "V2 Title"
        v2 = apply_edition_bump(new, old, "tom")
        assert v2["revision"]["edition"] == 2

        v3_content = copy.deepcopy(v2)
        v3_content["title"] = "V3 Title"
        v3 = apply_edition_bump(v3_content, v2, "claude")
        assert v3["revision"]["edition"] == 3

    def test_no_revision_in_old_defaults_to_edition_1(self):
        """If old content has no revision, treat as edition 0 so bump goes to 1."""
        old = _base_wp()
        del old["revision"]
        new = copy.deepcopy(old)
        new["title"] = "Updated"
        new["revision"] = {"edition": 1, "updated_at": "2026-03-01T10:00:00Z", "updated_by": "tom"}
        result = apply_edition_bump(new, old, "tom")
        assert result["revision"]["edition"] == 1

    def test_content_identity_preserved(self):
        """apply_edition_bump does not strip non-WP-level fields from content."""
        old = _base_wp()
        new = copy.deepcopy(old)
        new["title"] = "Updated"
        result = apply_edition_bump(new, old, "tom")
        # Excluded fields should still be present
        assert "ws_child_refs" in result
        assert "ws_total" in result


# ===========================================================================
# get_edition_history tests
# ===========================================================================

class TestGetEditionHistory:
    """Tests for get_edition_history()."""

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        assert get_edition_history([]) == []

    def test_single_edition_returned(self):
        """Single edition list returned as-is."""
        editions = [{"revision": {"edition": 1, "updated_at": "2026-03-01T10:00:00Z"}}]
        result = get_edition_history(editions)
        assert len(result) == 1
        assert result[0]["revision"]["edition"] == 1

    def test_reverse_chronological_order(self):
        """Editions returned newest-first (highest edition number first)."""
        editions = [
            {"revision": {"edition": 1, "updated_at": "2026-03-01T10:00:00Z"}},
            {"revision": {"edition": 2, "updated_at": "2026-03-01T11:00:00Z"}},
            {"revision": {"edition": 3, "updated_at": "2026-03-01T12:00:00Z"}},
        ]
        result = get_edition_history(editions)
        assert result[0]["revision"]["edition"] == 3
        assert result[1]["revision"]["edition"] == 2
        assert result[2]["revision"]["edition"] == 1

    def test_already_reversed_input_still_correct(self):
        """Already-reversed input is handled correctly (no double-reverse)."""
        editions = [
            {"revision": {"edition": 3, "updated_at": "2026-03-01T12:00:00Z"}},
            {"revision": {"edition": 1, "updated_at": "2026-03-01T10:00:00Z"}},
            {"revision": {"edition": 2, "updated_at": "2026-03-01T11:00:00Z"}},
        ]
        result = get_edition_history(editions)
        assert result[0]["revision"]["edition"] == 3
        assert result[1]["revision"]["edition"] == 2
        assert result[2]["revision"]["edition"] == 1

    def test_does_not_mutate_input(self):
        """get_edition_history does not mutate the input list."""
        editions = [
            {"revision": {"edition": 1, "updated_at": "2026-03-01T10:00:00Z"}},
            {"revision": {"edition": 2, "updated_at": "2026-03-01T11:00:00Z"}},
        ]
        original = copy.deepcopy(editions)
        get_edition_history(editions)
        assert editions == original


# ===========================================================================
# WP_LEVEL_FIELDS constant tests
# ===========================================================================

class TestWPLevelFieldsConstant:
    """Verify the WP_LEVEL_FIELDS constant matches the WS spec."""

    def test_contains_all_specified_fields(self):
        """WP_LEVEL_FIELDS contains exactly the fields from WS-WB-005."""
        expected = {
            "title", "rationale", "scope_in", "scope_out",
            "dependencies", "definition_of_done", "governance_pins",
            "ws_index", "state", "source_candidate_ids",
            "transformation", "transformation_notes",
        }
        assert WP_LEVEL_FIELDS == expected

    def test_excludes_legacy_fields(self):
        """Excluded fields are not in WP_LEVEL_FIELDS."""
        assert "ws_child_refs" not in WP_LEVEL_FIELDS
        assert "ws_total" not in WP_LEVEL_FIELDS
        assert "ws_done" not in WP_LEVEL_FIELDS
        assert "mode_b_count" not in WP_LEVEL_FIELDS

    def test_excludes_metadata_fields(self):
        """Metadata fields like wp_id, revision, change_summary not in WP_LEVEL_FIELDS."""
        assert "wp_id" not in WP_LEVEL_FIELDS
        assert "revision" not in WP_LEVEL_FIELDS
        assert "change_summary" not in WP_LEVEL_FIELDS

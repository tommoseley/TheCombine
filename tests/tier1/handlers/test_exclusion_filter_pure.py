"""
Tests for exclusion_filter pure functions -- WS-CRAP-004.

Tests extracted pure functions: build_exclusion_bindings,
filter_items_by_tags, filter_decision_points_by_tags,
apply_exclusion_filter.
"""

from app.api.services.mech_handlers.exclusion_filter import (
    build_exclusion_bindings,
    filter_items_by_tags,
    filter_decision_points_by_tags,
    apply_exclusion_filter,
)


# =========================================================================
# build_exclusion_bindings
# =========================================================================


class TestBuildExclusionBindings:
    """Tests for build_exclusion_bindings pure function."""

    def test_exclusion_invariant(self):
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["Blockchain", "NFT"],
                "invariant_kind": "exclusion",
            }
        ]
        exclusions, all_bindings = build_exclusion_bindings(invariants)
        assert len(exclusions) == 1
        assert exclusions[0]["id"] == "EXCL_1"
        assert exclusions[0]["tags"] == ["blockchain", "nft"]
        assert exclusions[0]["kind"] == "exclusion"
        assert len(all_bindings) == 1

    def test_requirement_invariant_not_in_exclusions(self):
        invariants = [
            {
                "id": "REQ_1",
                "canonical_tags": ["Python"],
                "invariant_kind": "requirement",
            }
        ]
        exclusions, all_bindings = build_exclusion_bindings(invariants)
        assert len(exclusions) == 0
        assert len(all_bindings) == 1

    def test_mixed_invariants(self):
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["Blockchain"],
                "invariant_kind": "exclusion",
            },
            {
                "id": "REQ_1",
                "canonical_tags": ["Python"],
                "invariant_kind": "requirement",
            },
        ]
        exclusions, all_bindings = build_exclusion_bindings(invariants)
        assert len(exclusions) == 1
        assert len(all_bindings) == 2

    def test_skip_empty_tags(self):
        invariants = [
            {"id": "EMPTY", "canonical_tags": [], "invariant_kind": "exclusion"},
        ]
        exclusions, all_bindings = build_exclusion_bindings(invariants)
        assert len(exclusions) == 0
        assert len(all_bindings) == 0

    def test_skip_missing_tags(self):
        invariants = [{"id": "NO_TAGS", "invariant_kind": "exclusion"}]
        exclusions, all_bindings = build_exclusion_bindings(invariants)
        assert len(exclusions) == 0

    def test_default_kind_is_requirement(self):
        invariants = [
            {"id": "DEFAULT", "canonical_tags": ["Python"]},
        ]
        _, all_bindings = build_exclusion_bindings(invariants)
        assert all_bindings[0]["kind"] == "requirement"

    def test_tags_lowercased(self):
        invariants = [
            {"id": "CASE", "canonical_tags": ["UPPER", "MiXeD"], "invariant_kind": "exclusion"},
        ]
        exclusions, _ = build_exclusion_bindings(invariants)
        assert exclusions[0]["tags"] == ["upper", "mixed"]


# =========================================================================
# filter_items_by_tags
# =========================================================================


class TestFilterItemsByTags:
    """Tests for filter_items_by_tags pure function."""

    def test_removes_matching_dict_items(self):
        items = [
            {"recommendation": "Use blockchain for storage"},
            {"recommendation": "Use PostgreSQL"},
        ]
        exclusions = [{"id": "E1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_items_by_tags(items, exclusions, "recommendation")
        assert len(result) == 1
        assert result[0]["recommendation"] == "Use PostgreSQL"

    def test_removes_matching_string_items(self):
        items = ["Use blockchain", "Use PostgreSQL"]
        exclusions = [{"id": "E1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_items_by_tags(items, exclusions, "text")
        assert len(result) == 1
        assert result[0] == "Use PostgreSQL"

    def test_case_insensitive_matching(self):
        items = [{"recommendation": "Use BLOCKCHAIN technology"}]
        exclusions = [{"id": "E1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_items_by_tags(items, exclusions, "recommendation")
        assert len(result) == 0

    def test_no_exclusions_keeps_all(self):
        items = [{"recommendation": "anything"}]
        result = filter_items_by_tags(items, [], "recommendation")
        assert len(result) == 1

    def test_empty_items_returns_empty(self):
        exclusions = [{"id": "E1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_items_by_tags([], exclusions, "recommendation")
        assert result == []

    def test_multiple_tags_any_match_removes(self):
        items = [{"recommendation": "NFT marketplace"}]
        exclusions = [{"id": "E1", "tags": ["blockchain", "nft"], "kind": "exclusion"}]
        result = filter_items_by_tags(items, exclusions, "recommendation")
        assert len(result) == 0

    def test_multiple_exclusions(self):
        items = [
            {"recommendation": "Use blockchain"},
            {"recommendation": "Add AI features"},
            {"recommendation": "Use PostgreSQL"},
        ]
        exclusions = [
            {"id": "E1", "tags": ["blockchain"], "kind": "exclusion"},
            {"id": "E2", "tags": ["ai features"], "kind": "exclusion"},
        ]
        result = filter_items_by_tags(items, exclusions, "recommendation")
        assert len(result) == 1


# =========================================================================
# filter_decision_points_by_tags
# =========================================================================


class TestFilterDecisionPointsByTags:
    """Tests for filter_decision_points_by_tags pure function."""

    def test_removes_matching_dict_decision_point(self):
        dps = [
            {"decision_area": "blockchain consensus mechanism"},
            {"decision_area": "database choice"},
        ]
        bindings = [{"id": "B1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_decision_points_by_tags(dps, bindings)
        assert len(result) == 1
        assert result[0]["decision_area"] == "database choice"

    def test_removes_matching_string_decision_point(self):
        dps = ["blockchain choice", "database choice"]
        bindings = [{"id": "B1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_decision_points_by_tags(dps, bindings)
        assert len(result) == 1

    def test_deep_json_matching(self):
        """Dict decision points are JSON-dumped, so nested fields match."""
        dps = [
            {"area": "storage", "options": [{"name": "blockchain"}]},
        ]
        bindings = [{"id": "B1", "tags": ["blockchain"], "kind": "exclusion"}]
        result = filter_decision_points_by_tags(dps, bindings)
        assert len(result) == 0

    def test_no_bindings_keeps_all(self):
        dps = [{"area": "anything"}]
        result = filter_decision_points_by_tags(dps, [])
        assert len(result) == 1

    def test_empty_dps_returns_empty(self):
        bindings = [{"id": "B1", "tags": ["test"], "kind": "exclusion"}]
        result = filter_decision_points_by_tags([], bindings)
        assert result == []


# =========================================================================
# apply_exclusion_filter
# =========================================================================


class TestApplyExclusionFilter:
    """Tests for apply_exclusion_filter pure function."""

    def test_filters_recommendations_and_decision_points(self):
        doc = {
            "recommendations_for_pm": [
                {"recommendation": "Use blockchain for tracking"},
                {"recommendation": "Use PostgreSQL for data"},
            ],
            "early_decision_points": [
                {"decision_area": "blockchain consensus"},
                {"decision_area": "API framework"},
            ],
        }
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["blockchain"],
                "invariant_kind": "exclusion",
            }
        ]
        result, removed = apply_exclusion_filter(doc, invariants)
        assert len(result["recommendations_for_pm"]) == 1
        assert len(result["early_decision_points"]) == 1
        assert removed == 2

    def test_no_exclusions_returns_copy(self):
        doc = {"recommendations_for_pm": ["a", "b"]}
        invariants = [
            {"id": "REQ_1", "canonical_tags": ["python"], "invariant_kind": "requirement"},
        ]
        result, removed = apply_exclusion_filter(doc, invariants)
        assert removed == 0
        assert result["recommendations_for_pm"] == ["a", "b"]
        assert result is not doc

    def test_does_not_mutate_original(self):
        doc = {
            "recommendations_for_pm": [
                {"recommendation": "Use blockchain"},
            ],
        }
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["blockchain"],
                "invariant_kind": "exclusion",
            }
        ]
        apply_exclusion_filter(doc, invariants)
        assert len(doc["recommendations_for_pm"]) == 1

    def test_filter_recommendations_disabled(self):
        doc = {
            "recommendations_for_pm": [
                {"recommendation": "Use blockchain"},
            ],
        }
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["blockchain"],
                "invariant_kind": "exclusion",
            }
        ]
        result, removed = apply_exclusion_filter(
            doc, invariants, filter_recommendations=False
        )
        assert len(result["recommendations_for_pm"]) == 1
        assert removed == 0

    def test_filter_decision_points_disabled(self):
        doc = {
            "early_decision_points": [
                {"decision_area": "blockchain consensus"},
            ],
        }
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["blockchain"],
                "invariant_kind": "exclusion",
            }
        ]
        result, removed = apply_exclusion_filter(
            doc, invariants, filter_decision_points_flag=False
        )
        assert len(result["early_decision_points"]) == 1
        assert removed == 0

    def test_empty_doc_sections(self):
        doc = {}
        invariants = [
            {
                "id": "EXCL_1",
                "canonical_tags": ["blockchain"],
                "invariant_kind": "exclusion",
            }
        ]
        result, removed = apply_exclusion_filter(doc, invariants)
        assert removed == 0

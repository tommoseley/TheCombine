"""
Tier-1 tests for prompt_assembler_pure.py — pure data transformation functions
extracted from PromptAssembler.

No I/O, no DB, no mocking of external services.
"""

import hashlib
import json

from app.domain.services.prompt_assembler_pure import (
    collect_ordered_component_ids,
    dedupe_bullets,
    compute_bundle_sha256,
    format_prompt_text,
)


# =========================================================================
# collect_ordered_component_ids
# =========================================================================

class TestCollectOrderedComponentIds:
    """Tests for component ID collection with order preservation."""

    def test_empty_sections(self):
        assert collect_ordered_component_ids([]) == []

    def test_single_section(self):
        sections = [{"component_id": "comp:A:1.0.0", "order": 1}]
        assert collect_ordered_component_ids(sections) == ["comp:A:1.0.0"]

    def test_preserves_section_order(self):
        sections = [
            {"component_id": "comp:C:1.0.0", "order": 3},
            {"component_id": "comp:A:1.0.0", "order": 1},
            {"component_id": "comp:B:1.0.0", "order": 2},
        ]
        result = collect_ordered_component_ids(sections)
        assert result == ["comp:A:1.0.0", "comp:B:1.0.0", "comp:C:1.0.0"]

    def test_dedup_first_occurrence_wins(self):
        sections = [
            {"component_id": "comp:A:1.0.0", "order": 1},
            {"component_id": "comp:B:1.0.0", "order": 2},
            {"component_id": "comp:A:1.0.0", "order": 3},
        ]
        result = collect_ordered_component_ids(sections)
        assert result == ["comp:A:1.0.0", "comp:B:1.0.0"]

    def test_skips_missing_component_id(self):
        sections = [
            {"component_id": "comp:A:1.0.0", "order": 1},
            {"order": 2},
            {"component_id": None, "order": 3},
        ]
        result = collect_ordered_component_ids(sections)
        assert result == ["comp:A:1.0.0"]

    def test_default_order_is_zero(self):
        sections = [
            {"component_id": "comp:B:1.0.0", "order": 1},
            {"component_id": "comp:A:1.0.0"},
        ]
        result = collect_ordered_component_ids(sections)
        assert result == ["comp:A:1.0.0", "comp:B:1.0.0"]


# =========================================================================
# dedupe_bullets
# =========================================================================

class TestDedupeBullets:
    """Tests for bullet deduplication from component guidance."""

    def test_empty_components(self):
        assert dedupe_bullets([]) == []

    def test_single_component_single_bullet(self):
        guidance = [{"bullets": ["Do the thing"]}]
        assert dedupe_bullets(guidance) == ["Do the thing"]

    def test_single_component_multiple_bullets(self):
        guidance = [{"bullets": ["A", "B", "C"]}]
        assert dedupe_bullets(guidance) == ["A", "B", "C"]

    def test_multiple_components_no_overlap(self):
        guidance = [
            {"bullets": ["A", "B"]},
            {"bullets": ["C", "D"]},
        ]
        assert dedupe_bullets(guidance) == ["A", "B", "C", "D"]

    def test_dedup_exact_duplicates(self):
        guidance = [
            {"bullets": ["A", "B"]},
            {"bullets": ["B", "C"]},
        ]
        assert dedupe_bullets(guidance) == ["A", "B", "C"]

    def test_first_occurrence_wins(self):
        guidance = [
            {"bullets": ["X"]},
            {"bullets": ["Y", "X"]},
        ]
        result = dedupe_bullets(guidance)
        assert result == ["X", "Y"]

    def test_missing_bullets_key(self):
        guidance = [{"no_bullets": True}, {"bullets": ["A"]}]
        assert dedupe_bullets(guidance) == ["A"]

    def test_empty_bullets_list(self):
        guidance = [{"bullets": []}, {"bullets": ["A"]}]
        assert dedupe_bullets(guidance) == ["A"]

    def test_preserves_component_order(self):
        guidance = [
            {"bullets": ["Z"]},
            {"bullets": ["A"]},
        ]
        assert dedupe_bullets(guidance) == ["Z", "A"]


# =========================================================================
# compute_bundle_sha256
# =========================================================================

class TestComputeBundleSha256:
    """Tests for schema bundle SHA256 computation."""

    def test_empty_bundle(self):
        result = compute_bundle_sha256({"schemas": {}})
        assert result.startswith("sha256:")
        assert len(result) == 7 + 64

    def test_deterministic(self):
        bundle = {"schemas": {"s1": {"type": "object"}}}
        h1 = compute_bundle_sha256(bundle)
        h2 = compute_bundle_sha256(bundle)
        assert h1 == h2

    def test_key_order_irrelevant(self):
        h1 = compute_bundle_sha256({"z": 1, "a": 2})
        h2 = compute_bundle_sha256({"a": 2, "z": 1})
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_bundle_sha256({"schemas": {"a": 1}})
        h2 = compute_bundle_sha256({"schemas": {"a": 2}})
        assert h1 != h2

    def test_matches_manual_computation(self):
        bundle = {"key": "value"}
        expected_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(expected_json.encode()).hexdigest()
        assert compute_bundle_sha256(bundle) == f"sha256:{expected_hash}"


# =========================================================================
# format_prompt_text
# =========================================================================

class TestFormatPromptText:
    """Tests for prompt text formatting."""

    def test_minimal_prompt(self):
        result = format_prompt_text(
            header={},
            component_bullets=[],
            component_ids=["comp:A"],
            bundle_sha256="sha256:abc",
        )
        assert "## Schema Bundle" in result
        assert "SHA256: sha256:abc" in result
        assert "Components: comp:A" in result

    def test_with_role(self):
        result = format_prompt_text(
            header={"role": "You are a senior architect."},
            component_bullets=[],
            component_ids=[],
            bundle_sha256="sha256:x",
        )
        assert result.startswith("You are a senior architect.")

    def test_with_constraints(self):
        result = format_prompt_text(
            header={"constraints": ["No speculation", "Be concise"]},
            component_bullets=[],
            component_ids=[],
            bundle_sha256="sha256:x",
        )
        assert "## Constraints" in result
        assert "- No speculation" in result
        assert "- Be concise" in result

    def test_with_bullets(self):
        result = format_prompt_text(
            header={},
            component_bullets=["Write clear titles", "Include risks"],
            component_ids=[],
            bundle_sha256="sha256:x",
        )
        assert "## Generation Guidelines" in result
        assert "- Write clear titles" in result
        assert "- Include risks" in result

    def test_full_prompt_ordering(self):
        result = format_prompt_text(
            header={
                "role": "Architect",
                "constraints": ["Constraint 1"],
            },
            component_bullets=["Bullet 1"],
            component_ids=["comp:A"],
            bundle_sha256="sha256:abc",
        )
        role_pos = result.index("Architect")
        constraint_pos = result.index("## Constraints")
        bullet_pos = result.index("## Generation Guidelines")
        schema_pos = result.index("## Schema Bundle")
        assert role_pos < constraint_pos < bullet_pos < schema_pos

    def test_multiple_component_ids(self):
        result = format_prompt_text(
            header={},
            component_bullets=[],
            component_ids=["comp:A", "comp:B", "comp:C"],
            bundle_sha256="sha256:x",
        )
        assert "Components: comp:A, comp:B, comp:C" in result

    def test_no_role_omits_role_line(self):
        result = format_prompt_text(
            header={"role": ""},
            component_bullets=[],
            component_ids=[],
            bundle_sha256="sha256:x",
        )
        # Should not have an empty line at the start from a blank role
        assert not result.startswith("\n")

    def test_no_constraints_omits_section(self):
        result = format_prompt_text(
            header={"constraints": []},
            component_bullets=[],
            component_ids=[],
            bundle_sha256="sha256:x",
        )
        assert "## Constraints" not in result

    def test_no_bullets_omits_section(self):
        result = format_prompt_text(
            header={},
            component_bullets=[],
            component_ids=[],
            bundle_sha256="sha256:x",
        )
        assert "## Generation Guidelines" not in result

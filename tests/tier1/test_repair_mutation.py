"""Tier-1 tests for repair mutation (WS-REPAIR-004, ADR-065).

Tests component replacement, finding verification, and lifecycle guards.
"""

import pytest

from app.domain.services.repair_mutation import (
    replace_component,
    verify_finding_cleared,
    MUTABLE_STATES,
)


class TestReplaceComponent:
    def test_replaces_target_component(self):
        content = {"components": [
            {"name": "API", "purpose": "routes", "owns": []},
            {"name": "Store", "purpose": "data"},
        ]}
        new_comp = {"name": "API", "purpose": "routes", "owns": ["src/api/"]}
        result = replace_component(content, "API", new_comp)

        assert len(result["components"]) == 2
        api = next(c for c in result["components"] if c["name"] == "API")
        assert api["owns"] == ["src/api/"]

    def test_preserves_other_components(self):
        content = {"components": [
            {"name": "API", "owns": []},
            {"name": "Store", "purpose": "data"},
        ]}
        new_comp = {"name": "API", "owns": ["src/api/"]}
        result = replace_component(content, "API", new_comp)

        store = next(c for c in result["components"] if c["name"] == "Store")
        assert store["purpose"] == "data"

    def test_does_not_mutate_input(self):
        content = {"components": [{"name": "API", "owns": []}]}
        new_comp = {"name": "API", "owns": ["src/api/"]}
        result = replace_component(content, "API", new_comp)

        assert content["components"][0]["owns"] == []
        assert result is not content

    def test_raises_on_missing_component(self):
        content = {"components": [{"name": "API"}]}
        with pytest.raises(ValueError, match="not found"):
            replace_component(content, "Missing", {"name": "Missing"})

    def test_empty_components_raises(self):
        content = {"components": []}
        with pytest.raises(ValueError, match="not found"):
            replace_component(content, "API", {"name": "API"})


class TestVerifyFindingCleared:
    def test_cleared_when_owns_present(self):
        content = {"components": [
            {"name": "API", "owns": ["src/api/"]},
        ]}
        assert verify_finding_cleared(content, "API") is True

    def test_not_cleared_when_owns_missing(self):
        content = {"components": [
            {"name": "API"},
        ]}
        assert verify_finding_cleared(content, "API") is False

    def test_not_cleared_when_owns_empty(self):
        content = {"components": [
            {"name": "API", "owns": []},
        ]}
        assert verify_finding_cleared(content, "API") is False

    def test_other_component_findings_dont_interfere(self):
        content = {"components": [
            {"name": "API", "owns": ["src/api/"]},
            {"name": "Store"},  # this one still has a finding
        ]}
        # API finding should be cleared even though Store still has one
        assert verify_finding_cleared(content, "API") is True
        assert verify_finding_cleared(content, "Store") is False


class TestMutableStates:
    def test_draft_is_mutable(self):
        assert "draft" in MUTABLE_STATES

    def test_qa_failed_is_mutable(self):
        assert "qa_failed" in MUTABLE_STATES

    def test_none_is_mutable(self):
        assert None in MUTABLE_STATES

    def test_stabilized_is_not_mutable(self):
        assert "stabilized" not in MUTABLE_STATES

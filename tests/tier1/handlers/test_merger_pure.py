"""
Tests for merger pure functions -- WS-CRAP-004.

Tests extracted pure functions: merge_values, deep_merge_collected,
shallow_merge_collected, concatenate_collected, merge_collected.
"""

import pytest

from app.api.services.mech_handlers.merger import (
    merge_values,
    deep_merge_collected,
    shallow_merge_collected,
    concatenate_collected,
    merge_collected,
    MERGE_STRATEGIES,
)


# =========================================================================
# merge_values
# =========================================================================


class TestMergeValues:
    """Tests for merge_values pure function."""

    def test_dict_dict_recursive_merge(self):
        base = {"a": 1, "b": {"x": 10}}
        override = {"b": {"y": 20}, "c": 3}
        result = merge_values(base, override)
        assert result == {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}

    def test_list_list_concatenation(self):
        result = merge_values([1, 2], [3, 4])
        assert result == [1, 2, 3, 4]

    def test_scalar_override_wins(self):
        assert merge_values("old", "new") == "new"
        assert merge_values(1, 2) == 2

    def test_dict_scalar_override_wins(self):
        result = merge_values({"a": 1}, "replaced")
        assert result == "replaced"

    def test_scalar_dict_override_wins(self):
        result = merge_values("old", {"a": 1})
        assert result == {"a": 1}

    def test_deep_copy_prevents_mutation(self):
        base = {"a": {"nested": [1]}}
        override = {"b": {"nested": [2]}}
        result = merge_values(base, override)
        result["a"]["nested"].append(99)
        result["b"]["nested"].append(99)
        assert base["a"]["nested"] == [1]
        assert override["b"]["nested"] == [2]

    def test_nested_dict_conflict_recursive(self):
        base = {"a": {"b": {"c": 1}}}
        override = {"a": {"b": {"d": 2}}}
        result = merge_values(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 2}}}

    def test_empty_dicts(self):
        assert merge_values({}, {}) == {}
        assert merge_values({"a": 1}, {}) == {"a": 1}
        assert merge_values({}, {"a": 1}) == {"a": 1}

    def test_empty_lists(self):
        assert merge_values([], []) == []
        assert merge_values([1], []) == [1]
        assert merge_values([], [1]) == [1]


# =========================================================================
# deep_merge_collected
# =========================================================================


class TestDeepMergeCollected:
    """Tests for deep_merge_collected pure function."""

    def test_merge_different_keys(self):
        collected = [
            {"key": "discovery", "value": {"summary": "hello"}},
            {"key": "architecture", "value": {"components": []}},
        ]
        result = deep_merge_collected(collected)
        assert result == {
            "discovery": {"summary": "hello"},
            "architecture": {"components": []},
        }

    def test_merge_same_key_deep(self):
        collected = [
            {"key": "config", "value": {"a": 1}},
            {"key": "config", "value": {"b": 2}},
        ]
        result = deep_merge_collected(collected)
        assert result == {"config": {"a": 1, "b": 2}}

    def test_empty_collected(self):
        assert deep_merge_collected([]) == {}

    def test_deep_copy_prevents_mutation(self):
        original = {"nested": [1]}
        collected = [{"key": "test", "value": original}]
        result = deep_merge_collected(collected)
        result["test"]["nested"].append(2)
        assert original["nested"] == [1]


# =========================================================================
# shallow_merge_collected
# =========================================================================


class TestShallowMergeCollected:
    """Tests for shallow_merge_collected pure function."""

    def test_later_value_overwrites(self):
        collected = [
            {"key": "config", "value": {"a": 1}},
            {"key": "config", "value": {"b": 2}},
        ]
        result = shallow_merge_collected(collected)
        # Second value overwrites first
        assert result == {"config": {"b": 2}}

    def test_different_keys(self):
        collected = [
            {"key": "a", "value": 1},
            {"key": "b", "value": 2},
        ]
        result = shallow_merge_collected(collected)
        assert result == {"a": 1, "b": 2}

    def test_empty_collected(self):
        assert shallow_merge_collected([]) == {}


# =========================================================================
# concatenate_collected
# =========================================================================


class TestConcatenateCollected:
    """Tests for concatenate_collected pure function."""

    def test_basic_concatenation(self):
        collected = [
            {"key": "a", "value": [1, 2]},
            {"key": "b", "value": [3, 4]},
        ]
        result = concatenate_collected(collected)
        assert result == {"a": [1, 2], "b": [3, 4]}

    def test_same_key_last_wins(self):
        collected = [
            {"key": "a", "value": "first"},
            {"key": "a", "value": "second"},
        ]
        result = concatenate_collected(collected)
        assert result == {"a": "second"}

    def test_empty_collected(self):
        assert concatenate_collected([]) == {}


# =========================================================================
# merge_collected
# =========================================================================


class TestMergeCollected:
    """Tests for merge_collected dispatch function."""

    def test_deep_merge_strategy(self):
        collected = [
            {"key": "a", "value": {"x": 1}},
            {"key": "a", "value": {"y": 2}},
        ]
        result = merge_collected(collected, "deep_merge")
        assert result == {"a": {"x": 1, "y": 2}}

    def test_shallow_merge_strategy(self):
        collected = [
            {"key": "a", "value": {"x": 1}},
            {"key": "a", "value": {"y": 2}},
        ]
        result = merge_collected(collected, "shallow_merge")
        assert result == {"a": {"y": 2}}

    def test_concatenate_strategy(self):
        collected = [{"key": "a", "value": 1}]
        result = merge_collected(collected, "concatenate")
        assert result == {"a": 1}

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown merge strategy"):
            merge_collected([], "invalid_strategy")

    def test_strategies_dict_has_all_three(self):
        assert set(MERGE_STRATEGIES.keys()) == {
            "deep_merge", "shallow_merge", "concatenate"
        }

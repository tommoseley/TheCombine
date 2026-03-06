"""Tier-1 CRAP score remediation tests for compare_runs in admin.py.

Covers the branching logic (CC=18):
- Token delta: identical input tokens vs different
- Cost delta: both zero, one non-zero, both non-zero
- Output comparison: both present + identical, both present + different
- Output comparison: one or both missing
- Metadata: time_delta present vs missing
- Full ReplayComparison construction
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from app.api.routers.admin import compare_runs, ReplayComparison


# =========================================================================
# Helpers
# =========================================================================


def _base_run(
    input_tokens=100,
    output_tokens=50,
    cost_usd=0.01,
    started_at=None,
    model_name="claude-3",
    artifact_type="project_discovery",
):
    return {
        "id": uuid4(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "started_at": started_at,
        "model_name": model_name,
        "artifact_type": artifact_type,
    }


# =========================================================================
# Token Delta
# =========================================================================


class TestTokenDelta:
    """Tests for token delta computation and notes."""

    def test_identical_input_tokens(self):
        """When input tokens are identical, note says so."""
        orig = _base_run(input_tokens=100, output_tokens=50)
        replay = _base_run(input_tokens=100, output_tokens=60)
        result = compare_runs(orig, replay, "output1", "output2")

        assert result.token_delta["input_tokens"] == 0
        assert result.token_delta["output_tokens"] == 10
        assert result.token_delta["total_tokens"] == 10
        assert any("identical" in n for n in result.notes)

    def test_different_input_tokens(self):
        """When input tokens differ, note reports the delta."""
        orig = _base_run(input_tokens=100, output_tokens=50)
        replay = _base_run(input_tokens=120, output_tokens=50)
        result = compare_runs(orig, replay, "output1", "output2")

        assert result.token_delta["input_tokens"] == 20
        assert any("differ by 20" in n for n in result.notes)

    def test_none_tokens_default_to_zero(self):
        """None token counts are treated as 0."""
        orig = _base_run()
        orig["input_tokens"] = None
        orig["output_tokens"] = None
        replay = _base_run(input_tokens=10, output_tokens=5)

        result = compare_runs(orig, replay, "a", "b")
        assert result.token_delta["input_tokens"] == 10
        assert result.token_delta["output_tokens"] == 5
        assert result.token_delta["total_tokens"] == 15


# =========================================================================
# Cost Delta
# =========================================================================


class TestCostDelta:
    """Tests for cost delta computation."""

    def test_both_costs_present(self):
        """When both runs have costs, delta is computed."""
        orig = _base_run(cost_usd=0.01)
        replay = _base_run(cost_usd=0.02)
        result = compare_runs(orig, replay, "a", "b")

        assert result.cost_delta_usd is not None
        assert abs(result.cost_delta_usd - 0.01) < 1e-9

    def test_both_costs_zero(self):
        """When both costs are zero, delta is None."""
        orig = _base_run(cost_usd=0)
        replay = _base_run(cost_usd=0)
        result = compare_runs(orig, replay, "a", "b")

        assert result.cost_delta_usd is None

    def test_one_cost_none(self):
        """When one cost is None, it's treated as 0."""
        orig = _base_run()
        orig["cost_usd"] = None
        replay = _base_run(cost_usd=0.05)

        result = compare_runs(orig, replay, "a", "b")
        assert result.cost_delta_usd is not None
        assert abs(result.cost_delta_usd - 0.05) < 1e-9


# =========================================================================
# Output Comparison
# =========================================================================


class TestOutputComparison:
    """Tests for output comparison logic."""

    def test_identical_outputs(self):
        """When outputs are identical, comparison says so."""
        text = "Hello world"
        orig = _base_run()
        replay = _base_run()
        result = compare_runs(orig, replay, text, text)

        assert result.outputs["identical"] is True
        assert result.outputs["length_delta"] == 0
        assert "sha256:" in result.outputs["original_hash"]
        assert result.outputs["original_hash"] == result.outputs["replay_hash"]
        assert any("identical" in n and "Output" in n for n in result.notes)

    def test_different_outputs(self):
        """When outputs differ, comparison reflects that."""
        orig = _base_run()
        replay = _base_run()
        result = compare_runs(orig, replay, "text A", "text B longer")

        assert result.outputs["identical"] is False
        assert result.outputs["original_hash"] != result.outputs["replay_hash"]
        assert result.outputs["original_length"] == 6
        assert result.outputs["replay_length"] == 13
        assert result.outputs["length_delta"] == 7
        assert any("differs" in n for n in result.notes)

    def test_original_output_missing(self):
        """When original_output is None, note says outputs missing."""
        result = compare_runs(_base_run(), _base_run(), None, "some output")

        assert result.outputs["identical"] is False
        assert result.outputs["original_hash"] is None
        assert "note" in result.outputs
        assert any("missing" in n for n in result.notes)

    def test_replay_output_missing(self):
        """When replay_output is None, note says outputs missing."""
        result = compare_runs(_base_run(), _base_run(), "some output", None)

        assert result.outputs["identical"] is False
        assert any("missing" in n for n in result.notes)

    def test_both_outputs_missing(self):
        """When both outputs are None, note says outputs missing."""
        result = compare_runs(_base_run(), _base_run(), None, None)

        assert result.outputs["identical"] is False
        assert any("missing" in n for n in result.notes)

    def test_empty_string_outputs(self):
        """Empty strings are falsy — treated as missing."""
        result = compare_runs(_base_run(), _base_run(), "", "")

        # Empty strings are falsy, so the branch `if original_output and replay_output`
        # will go to the else path
        assert result.outputs["identical"] is False
        assert any("missing" in n for n in result.notes)


# =========================================================================
# Metadata & Time Delta
# =========================================================================


class TestMetadata:
    """Tests for metadata and time delta computation."""

    def test_time_delta_computed(self):
        """When both started_at present, time_delta_days is computed."""
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 3, tzinfo=timezone.utc)
        orig = _base_run(started_at=t1)
        replay = _base_run(started_at=t2)

        result = compare_runs(orig, replay, "a", "b")
        assert result.metadata["time_delta_days"] == 2.0
        assert result.metadata["original_started_at"] == t1.isoformat()
        assert result.metadata["replay_started_at"] == t2.isoformat()

    def test_time_delta_none_when_missing_started_at(self):
        """When started_at is missing, time_delta_days is None."""
        orig = _base_run()
        orig["started_at"] = None
        replay = _base_run()
        replay["started_at"] = None

        result = compare_runs(orig, replay, "a", "b")
        assert result.metadata["time_delta_days"] is None

    def test_model_name_and_artifact_type_passed_through(self):
        """Model name and artifact type come from original run."""
        orig = _base_run(model_name="claude-opus", artifact_type="technical_architecture")
        replay = _base_run()

        result = compare_runs(orig, replay, "a", "b")
        assert result.metadata["model_name"] == "claude-opus"
        assert result.metadata["artifact_type"] == "technical_architecture"


# =========================================================================
# Full Integration
# =========================================================================


class TestCompareRunsFull:
    """End-to-end test of compare_runs return type."""

    def test_returns_replay_comparison_instance(self):
        """compare_runs returns a ReplayComparison instance."""
        orig = _base_run()
        replay = _base_run()
        result = compare_runs(orig, replay, "text", "text")

        assert isinstance(result, ReplayComparison)
        assert result.original_run_id == str(orig["id"])
        assert result.replay_run_id == str(replay["id"])
        assert isinstance(result.notes, list)
        assert isinstance(result.token_delta, dict)
        assert isinstance(result.outputs, dict)

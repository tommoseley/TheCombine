"""Tier-1 tests for replay override logic (WS-PI-0B Steps 1-2).

Tests the ReplayOverridesRequest model and override application logic.
Pure unit tests — no DB, no LLM calls.
"""

import hashlib

from app.api.routers.admin import (
    ReplayOverridesRequest,
    apply_overrides,
    build_overrides_metadata,
)


# =========================================================================
# ReplayOverridesRequest model
# =========================================================================


class TestReplayOverridesRequest:
    """Tests for the Pydantic request model."""

    def test_all_none_by_default(self):
        req = ReplayOverridesRequest()
        assert req.system_prompt_override is None
        assert req.temperature is None
        assert req.max_tokens is None

    def test_accepts_system_prompt_override(self):
        req = ReplayOverridesRequest(system_prompt_override="New prompt")
        assert req.system_prompt_override == "New prompt"

    def test_accepts_temperature(self):
        req = ReplayOverridesRequest(temperature=0.7)
        assert req.temperature == 0.7

    def test_accepts_max_tokens(self):
        req = ReplayOverridesRequest(max_tokens=8192)
        assert req.max_tokens == 8192

    def test_all_fields_together(self):
        req = ReplayOverridesRequest(
            system_prompt_override="New prompt",
            temperature=0.3,
            max_tokens=4096,
        )
        assert req.system_prompt_override == "New prompt"
        assert req.temperature == 0.3
        assert req.max_tokens == 4096


# =========================================================================
# apply_overrides
# =========================================================================


class TestApplyOverrides:
    """Tests for the apply_overrides helper."""

    def test_no_overrides_returns_original(self):
        """When no overrides provided, inputs are unchanged."""
        inputs = {"system_prompt": "original prompt", "user_prompt": "user msg"}
        result = apply_overrides(inputs, None)
        assert result["system_prompt"] == "original prompt"
        assert result["user_prompt"] == "user msg"

    def test_no_overrides_with_empty_request(self):
        """When all override fields are None, inputs are unchanged."""
        inputs = {"system_prompt": "original prompt", "user_prompt": "user msg"}
        overrides = ReplayOverridesRequest()
        result = apply_overrides(inputs, overrides)
        assert result["system_prompt"] == "original prompt"

    def test_system_prompt_override_applied(self):
        """System prompt is replaced when override provided."""
        inputs = {"system_prompt": "original prompt", "user_prompt": "user msg"}
        overrides = ReplayOverridesRequest(system_prompt_override="new prompt v2")
        result = apply_overrides(inputs, overrides)
        assert result["system_prompt"] == "new prompt v2"
        assert result["user_prompt"] == "user msg"  # unchanged

    def test_does_not_mutate_original_inputs(self):
        """apply_overrides must not mutate the original dict."""
        inputs = {"system_prompt": "original", "user_prompt": "user"}
        overrides = ReplayOverridesRequest(system_prompt_override="new")
        result = apply_overrides(inputs, overrides)
        assert inputs["system_prompt"] == "original"  # original unchanged
        assert result["system_prompt"] == "new"


# =========================================================================
# build_overrides_metadata
# =========================================================================


class TestBuildOverridesMetadata:
    """Tests for the overrides_applied metadata builder."""

    def test_no_overrides_returns_empty(self):
        meta = build_overrides_metadata(
            original_inputs={"system_prompt": "orig"},
            overrides=None,
        )
        assert meta == {}

    def test_no_overrides_with_empty_request(self):
        meta = build_overrides_metadata(
            original_inputs={"system_prompt": "orig"},
            overrides=ReplayOverridesRequest(),
        )
        assert meta == {}

    def test_system_prompt_override_records_hashes(self):
        original_prompt = "original system prompt"
        new_prompt = "new system prompt v2"
        overrides = ReplayOverridesRequest(system_prompt_override=new_prompt)

        meta = build_overrides_metadata(
            original_inputs={"system_prompt": original_prompt},
            overrides=overrides,
        )

        assert "system_prompt" in meta
        orig_hash = hashlib.sha256(original_prompt.encode()).hexdigest()[:16]
        new_hash = hashlib.sha256(new_prompt.encode()).hexdigest()[:16]
        assert orig_hash in meta["system_prompt"]
        assert new_hash in meta["system_prompt"]

    def test_temperature_override_recorded(self):
        overrides = ReplayOverridesRequest(temperature=0.8)
        meta = build_overrides_metadata(
            original_inputs={"system_prompt": "x"},
            overrides=overrides,
        )
        assert "temperature" in meta

    def test_max_tokens_override_recorded(self):
        overrides = ReplayOverridesRequest(max_tokens=4096)
        meta = build_overrides_metadata(
            original_inputs={"system_prompt": "x"},
            overrides=overrides,
        )
        assert "max_tokens" in meta

"""Tier-1 tests for replay override logic (WS-PI-0B Steps 1-2).

Tests the ReplayOverridesRequest model and override application logic.
Pure unit tests — no DB, no LLM calls.
"""

import hashlib

from app.api.routers.admin import (
    ReplayOverridesRequest,
    apply_overrides,
    build_overrides_metadata,
    extract_api_params,
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


# =========================================================================
# extract_api_params
# =========================================================================


class TestExtractApiParams:
    """Tests for input key normalization."""

    def test_replay_shape_system_and_user(self):
        """Replay-originated runs use system_prompt/user_prompt keys."""
        inputs = {"system_prompt": "You are a PM", "user_prompt": "Generate WS"}
        params = extract_api_params(inputs)
        assert params["system_prompt"] == "You are a PM"
        assert params["user_messages"] == ["Generate WS"]

    def test_production_shape_message_keys(self):
        """Production runs use message_N_user / message_N_system keys."""
        inputs = {
            "message_0_user": "Context data here",
            "message_1_user": "Role prompt + template",
        }
        params = extract_api_params(inputs)
        assert params["system_prompt"] == ""
        assert len(params["user_messages"]) == 2
        assert params["user_messages"][0] == "Context data here"
        assert params["user_messages"][1] == "Role prompt + template"

    def test_production_shape_with_system(self):
        """Production runs with explicit system message."""
        inputs = {
            "message_0_system": "System instructions",
            "message_0_user": "User context",
        }
        params = extract_api_params(inputs)
        assert params["system_prompt"] == "System instructions"
        assert params["user_messages"] == ["User context"]

    def test_fallback_unknown_keys(self):
        """Unknown key shapes fall back to single user message."""
        inputs = {"some_unknown_key": "content here"}
        params = extract_api_params(inputs)
        assert params["user_messages"] == ["content here"]


# =========================================================================
# apply_overrides with production input keys
# =========================================================================


class TestApplyOverridesProductionKeys:
    """Tests for apply_overrides with message_N_system keys."""

    def test_override_targets_system_key_in_production_data(self):
        """Override replaces message_N_system when present."""
        inputs = {
            "message_0_system": "Original system",
            "message_0_user": "User context",
        }
        overrides = ReplayOverridesRequest(system_prompt_override="New system")
        result = apply_overrides(inputs, overrides)
        assert result["message_0_system"] == "New system"
        assert result["message_0_user"] == "User context"

    def test_override_falls_back_to_system_prompt_key(self):
        """When no _system key exists, override creates system_prompt key."""
        inputs = {
            "message_0_user": "Context",
            "message_1_user": "Role prompt",
        }
        overrides = ReplayOverridesRequest(system_prompt_override="New system")
        result = apply_overrides(inputs, overrides)
        assert result["system_prompt"] == "New system"


# =========================================================================
# End-to-end: apply_overrides -> extract_api_params with production data
# =========================================================================


class TestOverridesThenExtractRoundTrip:
    """Verify that overrides applied to production data produce correct API params."""

    def test_system_override_preserves_user_messages(self):
        """CRITICAL: system_prompt_override must not lose message_N_user content."""
        inputs = {
            "message_0_user": "Context data (35k chars)",
            "message_1_user": "PM role + document generator template",
        }
        overrides = ReplayOverridesRequest(system_prompt_override="New governance system prompt")
        overridden = apply_overrides(inputs, overrides)
        params = extract_api_params(overridden)

        assert params["system_prompt"] == "New governance system prompt"
        assert len(params["user_messages"]) == 2
        assert params["user_messages"][0] == "Context data (35k chars)"
        assert params["user_messages"][1] == "PM role + document generator template"

    def test_prompt_append_preserves_all_messages(self):
        """prompt_append should append to last user key without losing others."""
        inputs = {
            "message_0_user": "Context data",
            "message_1_user": "Role prompt",
        }
        overrides = ReplayOverridesRequest(prompt_append="## Extra governance rules")
        overridden = apply_overrides(inputs, overrides)
        params = extract_api_params(overridden)

        assert len(params["user_messages"]) == 2
        assert params["user_messages"][0] == "Context data"
        assert "Extra governance rules" in params["user_messages"][1]

    def test_both_overrides_on_production_data(self):
        """System override + prompt_append on production data preserves all content."""
        inputs = {
            "message_0_user": "Context data",
            "message_1_user": "Role prompt",
        }
        overrides = ReplayOverridesRequest(
            system_prompt_override="New system",
            prompt_append="## Extra rules",
        )
        overridden = apply_overrides(inputs, overrides)
        params = extract_api_params(overridden)

        assert params["system_prompt"] == "New system"
        assert len(params["user_messages"]) == 2
        assert params["user_messages"][0] == "Context data"
        assert "Extra rules" in params["user_messages"][1]

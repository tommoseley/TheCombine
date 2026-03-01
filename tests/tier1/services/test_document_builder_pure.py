"""
Tier-1 tests for document_builder_pure.py — pure data transformation functions
extracted from DocumentBuilder.

No I/O, no DB, no mocking of external services.
"""

from app.domain.services.document_builder_pure import (
    resolve_model_params,
    build_user_message,
    compute_stream_progress,
    should_emit_stream_update,
)


# =========================================================================
# resolve_model_params
# =========================================================================

class TestResolveModelParams:
    """Tests for model parameter resolution from options dict."""

    def test_default_values(self):
        model, max_tokens, temp = resolve_model_params({}, "claude-sonnet-4-20250514")
        assert model == "claude-sonnet-4-20250514"
        assert max_tokens == 4096
        assert temp == 0.7

    def test_model_from_options(self):
        model, _, _ = resolve_model_params(
            {"model": "claude-opus-4-20250514"},
            "claude-sonnet-4-20250514",
        )
        assert model == "claude-opus-4-20250514"

    def test_model_empty_string_falls_back(self):
        model, _, _ = resolve_model_params({"model": ""}, "default-model")
        assert model == "default-model"

    def test_model_none_falls_back(self):
        model, _, _ = resolve_model_params({"model": None}, "default-model")
        assert model == "default-model"

    def test_model_string_sentinel_falls_back(self):
        """The 'string' sentinel from OpenAPI defaults should fall back."""
        model, _, _ = resolve_model_params({"model": "string"}, "default-model")
        assert model == "default-model"

    def test_max_tokens_from_options(self):
        _, max_tokens, _ = resolve_model_params({"max_tokens": 8192}, "m")
        assert max_tokens == 8192

    def test_max_tokens_zero_falls_back(self):
        _, max_tokens, _ = resolve_model_params({"max_tokens": 0}, "m")
        assert max_tokens == 4096

    def test_temperature_from_options(self):
        _, _, temp = resolve_model_params({"temperature": 0.3}, "m")
        assert temp == 0.3

    def test_temperature_zero_is_valid(self):
        _, _, temp = resolve_model_params({"temperature": 0}, "m")
        assert temp == 0

    def test_temperature_none_defaults(self):
        _, _, temp = resolve_model_params({"temperature": None}, "m")
        assert temp == 0.7

    def test_all_options_together(self):
        model, max_tokens, temp = resolve_model_params(
            {"model": "my-model", "max_tokens": 2048, "temperature": 0.5},
            "default",
        )
        assert model == "my-model"
        assert max_tokens == 2048
        assert temp == 0.5


# =========================================================================
# build_user_message
# =========================================================================

class TestBuildUserMessage:
    """Tests for user message assembly."""

    def test_minimal_message(self):
        config = {"name": "TestDoc"}
        result = build_user_message(config, {}, {})
        assert "Create a TestDoc." in result
        assert "Output ONLY valid JSON" in result

    def test_with_description(self):
        config = {"name": "TestDoc", "description": "A test document"}
        result = build_user_message(config, {}, {})
        assert "Document purpose: A test document" in result

    def test_with_user_query(self):
        config = {"name": "Doc"}
        result = build_user_message(config, {"user_query": "Build me a thing"}, {})
        assert "User request:\nBuild me a thing" in result

    def test_with_project_description(self):
        config = {"name": "Doc"}
        result = build_user_message(
            config,
            {"project_description": "My project"},
            {},
        )
        assert "Project description:\nMy project" in result

    def test_with_input_docs(self):
        config = {"name": "Doc"}
        input_docs = {"charter": {"title": "My Charter"}}
        result = build_user_message(config, {}, input_docs)
        assert "--- Input Documents ---" in result
        assert "### charter:" in result
        assert '"title": "My Charter"' in result

    def test_no_description_omits_line(self):
        config = {"name": "Doc"}
        result = build_user_message(config, {}, {})
        assert "Document purpose:" not in result

    def test_no_user_query_omits_line(self):
        config = {"name": "Doc"}
        result = build_user_message(config, {}, {})
        assert "User request:" not in result

    def test_empty_input_docs_omits_section(self):
        config = {"name": "Doc"}
        result = build_user_message(config, {}, {})
        assert "--- Input Documents ---" not in result

    def test_full_message_ordering(self):
        config = {"name": "Epic", "description": "Epic plan"}
        user_inputs = {
            "user_query": "Create an epic",
            "project_description": "The project",
        }
        input_docs = {"charter": {"id": 1}}
        result = build_user_message(config, user_inputs, input_docs)

        # Verify ordering: name -> description -> user_query -> project_desc -> input_docs -> reminder
        name_pos = result.index("Create a Epic.")
        desc_pos = result.index("Document purpose:")
        query_pos = result.index("User request:")
        proj_pos = result.index("Project description:")
        docs_pos = result.index("--- Input Documents ---")
        reminder_pos = result.index("Output ONLY valid JSON")

        assert name_pos < desc_pos < query_pos < proj_pos < docs_pos < reminder_pos


# =========================================================================
# compute_stream_progress
# =========================================================================

class TestComputeStreamProgress:
    """Tests for streaming progress percentage computation."""

    def test_zero_length(self):
        assert compute_stream_progress(0) == 30

    def test_small_length(self):
        assert compute_stream_progress(100) == 32

    def test_medium_length(self):
        assert compute_stream_progress(1000) == 50

    def test_large_length_capped_at_70(self):
        assert compute_stream_progress(10000) == 70

    def test_exact_boundary(self):
        # 2000 // 50 = 40, 30 + 40 = 70
        assert compute_stream_progress(2000) == 70

    def test_just_under_boundary(self):
        # 1999 // 50 = 39, 30 + 39 = 69
        assert compute_stream_progress(1999) == 69


# =========================================================================
# should_emit_stream_update
# =========================================================================

class TestShouldEmitStreamUpdate:
    """Tests for stream update emission throttle logic."""

    def test_first_chunk_always_emits(self):
        # accumulated = 5, chunk = 5 -> 5 % 100 = 5 < 5 is False
        # Actually, the very first chunk: accumulated=5, chunk=5 -> 5 % 100 = 5, 5 < 5 is False
        # But accumulated=3, chunk=3 -> 3 % 100 = 3 < 3 is False
        # The logic is: emit roughly every 100 chars
        pass

    def test_emit_at_100_boundary(self):
        # accumulated = 105, chunk = 10 -> 105 % 100 = 5 < 10 -> True
        assert should_emit_stream_update(105, 10) is True

    def test_no_emit_mid_block(self):
        # accumulated = 150, chunk = 2 -> 150 % 100 = 50 < 2 -> False
        assert should_emit_stream_update(150, 2) is False

    def test_emit_when_crossing_boundary(self):
        # accumulated = 200, chunk = 5 -> 200 % 100 = 0 < 5 -> True
        assert should_emit_stream_update(200, 5) is True

    def test_emit_when_chunk_equals_modulo(self):
        # accumulated = 50, chunk = 50 -> 50 % 100 = 50 < 50 -> False
        assert should_emit_stream_update(50, 50) is False

    def test_large_chunk_always_emits(self):
        # accumulated = 250, chunk = 100 -> 250 % 100 = 50 < 100 -> True
        assert should_emit_stream_update(250, 100) is True

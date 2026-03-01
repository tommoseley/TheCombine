"""Tests for intake pure functions -- WS-CRAP-002.

Tests extracted pure functions: extract_messages, build_interpretation,
determine_phase, deduplicate_pending_prompt.
"""

from app.api.v1.services.intake_pure import (
    extract_messages,
    build_interpretation,
    determine_phase,
    deduplicate_pending_prompt,
)


# =========================================================================
# extract_messages
# =========================================================================


class TestExtractMessages:
    """Tests for extract_messages pure function."""

    def test_empty_history(self):
        assert extract_messages([]) == []

    def test_user_input_only(self):
        history = [{"user_input": "hello"}]
        result = extract_messages(history)
        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "hello"}

    def test_response_only(self):
        history = [{"response": "How can I help?"}]
        result = extract_messages(history)
        assert len(result) == 1
        assert result[0] == {"role": "assistant", "content": "How can I help?"}

    def test_user_prompt_fallback(self):
        history = [{"user_prompt": "Question for user"}]
        result = extract_messages(history)
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Question for user"

    def test_response_takes_priority_over_user_prompt(self):
        history = [{"response": "Response", "user_prompt": "Prompt"}]
        result = extract_messages(history)
        assert len(result) == 1
        assert result[0]["content"] == "Response"

    def test_multiple_exchanges(self):
        history = [
            {"user_input": "Hi", "response": "Hello!"},
            {"user_input": "Help", "response": "Sure!"},
        ]
        result = extract_messages(history)
        assert len(result) == 4
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"
        assert result[3]["role"] == "assistant"

    def test_context_state_user_input_added(self):
        history = [{"response": "Hello!"}]
        result = extract_messages(history, context_state_user_input="initial input")
        user_msgs = [m for m in result if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0]["content"] == "initial input"

    def test_context_state_user_input_not_duplicated(self):
        history = [{"user_input": "already here"}]
        result = extract_messages(history, context_state_user_input="already here")
        user_msgs = [m for m in result if m["role"] == "user"]
        assert len(user_msgs) == 1

    def test_context_state_user_input_inserted_after_first_assistant(self):
        history = [
            {"response": "Welcome"},
            {"user_input": "Thanks"},
        ]
        result = extract_messages(history, context_state_user_input="initial")
        # Should be inserted after the first assistant message
        assert result[0]["role"] == "assistant"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "initial"

    def test_empty_user_input_ignored(self):
        history = [{"user_input": "", "response": "Hello"}]
        result = extract_messages(history)
        # Empty string is falsy, should not create a user message
        assert len(result) == 1
        assert result[0]["role"] == "assistant"

    def test_none_metadata_values(self):
        history = [{"user_input": None, "response": None}]
        result = extract_messages(history)
        assert result == []


# =========================================================================
# build_interpretation
# =========================================================================


class TestBuildInterpretation:
    """Tests for build_interpretation pure function."""

    def test_empty_dict(self):
        assert build_interpretation({}) == {}

    def test_dict_value_normalized(self):
        raw = {
            "project_name": {
                "value": "MyApp",
                "source": "user",
                "locked": True,
            }
        }
        result = build_interpretation(raw)
        assert result["project_name"]["value"] == "MyApp"
        assert result["project_name"]["source"] == "user"
        assert result["project_name"]["locked"] is True

    def test_dict_value_defaults(self):
        raw = {"field": {"extra": "stuff"}}
        result = build_interpretation(raw)
        assert result["field"]["value"] == ""
        assert result["field"]["source"] == "llm"
        assert result["field"]["locked"] is False

    def test_string_value_converted(self):
        raw = {"project_name": "MyApp"}
        result = build_interpretation(raw)
        assert result["project_name"]["value"] == "MyApp"
        assert result["project_name"]["source"] == "llm"
        assert result["project_name"]["locked"] is False

    def test_int_value_converted(self):
        raw = {"count": 42}
        result = build_interpretation(raw)
        assert result["count"]["value"] == "42"

    def test_multiple_fields(self):
        raw = {
            "name": {"value": "Test", "source": "user", "locked": True},
            "type": "web_app",
        }
        result = build_interpretation(raw)
        assert len(result) == 2
        assert result["name"]["locked"] is True
        assert result["type"]["value"] == "web_app"


# =========================================================================
# determine_phase
# =========================================================================


class TestDeterminePhase:
    """Tests for determine_phase pure function."""

    def test_completed(self):
        assert determine_phase("describe", True) == "complete"

    def test_not_completed_with_phase(self):
        assert determine_phase("review", False) == "review"

    def test_not_completed_none_phase(self):
        assert determine_phase(None, False) == "describe"

    def test_completed_overrides_phase(self):
        assert determine_phase("describe", True) == "complete"


# =========================================================================
# deduplicate_pending_prompt
# =========================================================================


class TestDeduplicatePendingPrompt:
    """Tests for deduplicate_pending_prompt pure function."""

    def test_none_prompt(self):
        assert deduplicate_pending_prompt(None, []) is None

    def test_empty_messages(self):
        assert deduplicate_pending_prompt("hello", []) == "hello"

    def test_no_duplicate(self):
        messages = [{"role": "assistant", "content": "different"}]
        assert deduplicate_pending_prompt("hello", messages) == "hello"

    def test_duplicate_removed(self):
        messages = [{"role": "assistant", "content": "same text"}]
        assert deduplicate_pending_prompt("same text", messages) is None

    def test_only_checks_last_assistant(self):
        messages = [
            {"role": "assistant", "content": "old"},
            {"role": "user", "content": "response"},
            {"role": "assistant", "content": "same text"},
        ]
        assert deduplicate_pending_prompt("same text", messages) is None

    def test_earlier_assistant_match_still_removed(self):
        messages = [
            {"role": "assistant", "content": "same text"},
            {"role": "user", "content": "reply"},
        ]
        # The function finds the last assistant message (first one here since
        # reversed iteration hits user first, then assistant) and it matches
        assert deduplicate_pending_prompt("same text", messages) is None

    def test_different_last_assistant(self):
        messages = [
            {"role": "assistant", "content": "same text"},
            {"role": "user", "content": "reply"},
            {"role": "assistant", "content": "new text"},
        ]
        assert deduplicate_pending_prompt("same text", messages) == "same text"

"""Tier-1 tests for LLM Response Parser.

Pure parsing tests -- no DB, no I/O, no LLM calls.
Tests the parsing strategies for extracting JSON from LLM output.
"""

import json

from app.domain.services.llm_response_parser import (
    DirectParseStrategy,
    FuzzyBoundaryStrategy,
    LLMResponseParser,
    MarkdownFenceStrategy,
)


# =========================================================================
# DirectParseStrategy
# =========================================================================


class TestDirectParseStrategy:
    """DirectParseStrategy extracts JSON via json.loads after stripping prefixes."""

    def test_clean_object(self):
        result = DirectParseStrategy().parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_clean_array(self):
        result = DirectParseStrategy().parse('[{"key": "value"}]')
        assert result == [{"key": "value"}]

    def test_with_whitespace(self):
        result = DirectParseStrategy().parse('  \n{"key": "value"}\n  ')
        assert result == {"key": "value"}

    def test_with_prefix(self):
        result = DirectParseStrategy().parse('Here is the JSON: {"key": "value"}')
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self):
        result = DirectParseStrategy().parse("not json at all")
        assert result is None

    def test_commentary_around_json_returns_none(self):
        result = DirectParseStrategy().parse(
            'Here is the output:\n[{"key": "value"}]\nHope this helps!'
        )
        assert result is None


# =========================================================================
# MarkdownFenceStrategy
# =========================================================================


class TestMarkdownFenceStrategy:
    """MarkdownFenceStrategy extracts JSON from markdown code fences."""

    def test_json_fence_with_object(self):
        text = '```json\n{"key": "value"}\n```'
        result = MarkdownFenceStrategy().parse(text)
        assert result == {"key": "value"}

    def test_json_fence_with_array(self):
        text = '```json\n[{"key": "value"}]\n```'
        result = MarkdownFenceStrategy().parse(text)
        assert result == [{"key": "value"}]

    def test_no_fences_returns_none(self):
        result = MarkdownFenceStrategy().parse('{"key": "value"}')
        assert result is None


# =========================================================================
# FuzzyBoundaryStrategy -- array handling
# =========================================================================


class TestFuzzyBoundaryStrategyObjects:
    """FuzzyBoundaryStrategy extracts JSON objects from text with commentary."""

    def test_object_with_commentary(self):
        text = 'Here is the output:\n{"key": "value"}\nDone.'
        result = FuzzyBoundaryStrategy().parse(text)
        assert result == {"key": "value"}


class TestFuzzyBoundaryStrategyArrays:
    """FuzzyBoundaryStrategy must also handle JSON arrays in text with commentary.

    Bug: The strategy only looked for { and }, missing arrays starting with [.
    The propose_work_statements task prompt requires a JSON array output.
    """

    def test_array_with_commentary(self):
        """Array wrapped in commentary text must be extracted."""
        text = 'Here are the work statements:\n[{"ws_id": "WS-001"}]\nLet me know.'
        result = FuzzyBoundaryStrategy().parse(text)
        assert result == [{"ws_id": "WS-001"}]

    def test_clean_array(self):
        """Clean JSON array (no commentary) must parse."""
        text = '[{"ws_id": "WS-001"}, {"ws_id": "WS-002"}]'
        result = FuzzyBoundaryStrategy().parse(text)
        assert result == [{"ws_id": "WS-001"}, {"ws_id": "WS-002"}]

    def test_array_in_commentary_no_braces_outside(self):
        """Array where no standalone braces exist outside the array."""
        text = 'Output:\n[{"a": 1}, {"b": 2}]\nEnd.'
        result = FuzzyBoundaryStrategy().parse(text)
        assert result == [{"a": 1}, {"b": 2}]


# =========================================================================
# LLMResponseParser integration -- array parsing end-to-end
# =========================================================================


class TestParserArraySupport:
    """LLMResponseParser must handle JSON arrays from LLM responses."""

    def test_clean_array_parses(self):
        parser = LLMResponseParser()
        result = parser.parse('[{"ws_id": "WS-001"}]')
        assert result.success is True
        assert result.data == [{"ws_id": "WS-001"}]

    def test_array_in_commentary_parses(self):
        """Array with surrounding commentary must be extracted by at least one strategy."""
        parser = LLMResponseParser()
        text = "Here are the proposed work statements:\n\n" + json.dumps(
            [{"ws_id": "WS-001", "title": "Test"}]
        ) + "\n\nPlease review."
        result = parser.parse(text)
        assert result.success is True
        assert result.data == [{"ws_id": "WS-001", "title": "Test"}]

    def test_array_in_markdown_fence_parses(self):
        parser = LLMResponseParser()
        text = '```json\n[{"ws_id": "WS-001"}]\n```'
        result = parser.parse(text)
        assert result.success is True
        assert result.data == [{"ws_id": "WS-001"}]


# =========================================================================
# Edge cases
# =========================================================================


class TestParserEdgeCases:
    """Edge cases for the parser."""

    def test_empty_string(self):
        parser = LLMResponseParser()
        result = parser.parse("")
        assert result.success is False

    def test_non_string_input(self):
        parser = LLMResponseParser()
        result = parser.parse(123)
        assert result.success is False

    def test_truncated_array_extracts_partial_object(self):
        """Truncated JSON array: FuzzyBoundary extracts the first complete object.

        This is by design -- fuzzy parsing does best-effort extraction.
        Truncation should be prevented upstream via adequate max_tokens.
        """
        parser = LLMResponseParser()
        result = parser.parse('[{"ws_id": "WS-001"}, {"ws_id": "WS-00')
        # FuzzyBoundary finds the first complete {..} and extracts it
        assert result.success is True
        assert result.data == {"ws_id": "WS-001"}

    def test_completely_invalid_text_fails(self):
        """Text with no JSON structure at all must fail."""
        parser = LLMResponseParser()
        result = parser.parse("This is just plain text with no JSON.")
        assert result.success is False

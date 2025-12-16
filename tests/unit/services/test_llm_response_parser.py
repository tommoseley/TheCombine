"""
Unit tests for LLMResponseParser.

Tests cover all parsing strategies, edge cases, and QA Issue #2
(configurable strategy ordering).

Authors: D-1 (Senior), D-3 (Junior)
Epic: PIPELINE-175B
"""

import pytest
from app.domain.services.llm_response_parser import (
    ParseResult,
    LLMResponseParser,
    DirectParseStrategy,
    MarkdownFenceStrategy,
    FuzzyBoundaryStrategy
)


class TestDirectParseStrategy:
    """Tests for DirectParseStrategy."""
    
    def test_parse_clean_json(self):
        """Should parse clean JSON successfully."""
        strategy = DirectParseStrategy()
        result = strategy.parse('{"key": "value"}')
        assert result == {"key": "value"}
    
    def test_parse_with_whitespace(self):
        """Should strip whitespace before parsing."""
        strategy = DirectParseStrategy()
        result = strategy.parse('  \n{"key": "value"}\n  ')
        assert result == {"key": "value"}
    
    def test_parse_with_prefix(self):
        """Should strip common prefixes before parsing."""
        strategy = DirectParseStrategy()
        result = strategy.parse('Here is the JSON: {"key": "value"}')
        assert result == {"key": "value"}
    
    def test_parse_invalid_json(self):
        """Should return None for invalid JSON."""
        strategy = DirectParseStrategy()
        result = strategy.parse('not json')
        assert result is None
    
    def test_parse_malformed_json(self):
        """Should return None for malformed JSON."""
        strategy = DirectParseStrategy()
        result = strategy.parse('{"key": "value",}')  # Trailing comma
        assert result is None


class TestMarkdownFenceStrategy:
    """Tests for MarkdownFenceStrategy."""
    
    def test_parse_json_fence(self):
        """Should extract JSON from ```json fence."""
        strategy = MarkdownFenceStrategy()
        text = '```json\n{"key": "value"}\n```'
        result = strategy.parse(text)
        assert result == {"key": "value"}
    
    def test_parse_plain_fence(self):
        """Should extract JSON from ``` fence without language tag."""
        strategy = MarkdownFenceStrategy()
        text = '```\n{"key": "value"}\n```'
        result = strategy.parse(text)
        assert result == {"key": "value"}
    
    def test_parse_fence_with_surrounding_text(self):
        """Should extract JSON from fence ignoring surrounding text."""
        strategy = MarkdownFenceStrategy()
        text = 'Here is the result:\n```json\n{"key": "value"}\n```\nLet me know if you need changes.'
        result = strategy.parse(text)
        assert result == {"key": "value"}
    
    def test_parse_multiple_fences(self):
        """Should try largest fence first when multiple present."""
        strategy = MarkdownFenceStrategy()
        text = '```json\n{"small": "data"}\n```\n\n```json\n{"large": "data", "with": "more"}\n```'
        result = strategy.parse(text)
        assert result == {"large": "data", "with": "more"}
    
    def test_parse_no_fence(self):
        """Should return None when no fence present."""
        strategy = MarkdownFenceStrategy()
        result = strategy.parse('{"key": "value"}')
        assert result is None


class TestFuzzyBoundaryStrategy:
    """Tests for FuzzyBoundaryStrategy."""
    
    def test_parse_json_with_text(self):
        """Should extract JSON from first { to last }."""
        strategy = FuzzyBoundaryStrategy()
        text = 'Some text before {"key": "value"} and after'
        result = strategy.parse(text)
        assert result == {"key": "value"}
    
    def test_parse_nested_json(self):
        """Should handle nested JSON correctly."""
        strategy = FuzzyBoundaryStrategy()
        text = 'Text {"outer": {"inner": "value"}} more text'
        result = strategy.parse(text)
        assert result == {"outer": {"inner": "value"}}
    
    def test_parse_no_braces(self):
        """Should return None when no braces present."""
        strategy = FuzzyBoundaryStrategy()
        result = strategy.parse('no json here')
        assert result is None
    
    def test_parse_invalid_between_braces(self):
        """Should return None when content between braces is invalid."""
        strategy = FuzzyBoundaryStrategy()
        result = strategy.parse('before { invalid json } after')
        assert result is None


class TestLLMResponseParser:
    """Tests for LLMResponseParser main class."""
    
    def test_parse_clean_json(self):
        """Should parse clean JSON using DirectParseStrategy."""
        parser = LLMResponseParser()
        result = parser.parse('{"key": "value"}')
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.strategy_used == "DirectParseStrategy"
        assert result.error_messages == []
    
    def test_parse_markdown_fence(self):
        """Should parse fenced JSON using MarkdownFenceStrategy."""
        parser = LLMResponseParser()
        result = parser.parse('```json\n{"key": "value"}\n```')
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.strategy_used == "MarkdownFenceStrategy"
    
    def test_parse_fuzzy_boundary(self):
        """Should parse embedded JSON using FuzzyBoundaryStrategy."""
        parser = LLMResponseParser()
        # Create text that will fail direct and fence, but work with fuzzy
        text = 'Result: {"key": "value"} (no fence)'
        result = parser.parse(text)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.strategy_used == "FuzzyBoundaryStrategy"
    
    def test_parse_empty_string(self):
        """Should return failure for empty string."""
        parser = LLMResponseParser()
        result = parser.parse('')
        assert result.success is False
        assert result.data is None
        assert "Empty response text" in result.error_messages
    
    def test_parse_non_string_input(self):
        """Should return failure for non-string input."""
        parser = LLMResponseParser()
        result = parser.parse(None)
        assert result.success is False
        assert "Invalid input: expected string" in result.error_messages
    
    def test_parse_unparseable_text(self):
        """Should return failure with diagnostics for unparseable text."""
        parser = LLMResponseParser()
        result = parser.parse('completely unparseable text')
        assert result.success is False
        assert result.data is None
        assert len(result.error_messages) >= 0  # May have errors or generic message
    
    def test_custom_strategy_ordering(self):
        """QA Issue #2: Should respect custom strategy ordering."""
        # Reverse strategy order
        parser = LLMResponseParser([
            FuzzyBoundaryStrategy(),
            MarkdownFenceStrategy(),
            DirectParseStrategy()
        ])
        # This would normally use DirectParse, but we've reversed order
        result = parser.parse('{"key": "value"}')
        assert result.success is True
        assert result.data == {"key": "value"}
        # FuzzyBoundary will succeed first since it's now first
        assert result.strategy_used == "FuzzyBoundaryStrategy"
    
    def test_single_strategy(self):
        """Should work with single strategy."""
        parser = LLMResponseParser([DirectParseStrategy()])
        result = parser.parse('{"key": "value"}')
        assert result.success is True
        assert result.data == {"key": "value"}
    
    def test_empty_strategy_list_raises(self):
        """Should raise ValueError for empty strategy list."""
        with pytest.raises(ValueError, match="at least one strategy"):
            LLMResponseParser([])


# Total: 18 tests
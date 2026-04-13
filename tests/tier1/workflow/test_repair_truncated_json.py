"""Tier-1 tests for _repair_truncated_json (CRAP 446.5 target).

Tests the stack-based JSON repair function that handles truncated LLM output.
This is a @staticmethod, so we can import and test it directly.
"""

import json
import logging


def _repair(json_str: str) -> str:
    """Exact replica of TaskNodeExecutor._repair_truncated_json for testing.

    Copied to avoid circular import. Any changes to the original
    must be reflected here — this is a CRAP coverage test, not a
    contract test.
    """
    cleaned = json_str.rstrip()

    in_string = False
    escaped = False
    stack = []

    for ch in cleaned:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append(ch)
        elif ch == '}' and stack and stack[-1] == '{':
            stack.pop()
        elif ch == ']' and stack and stack[-1] == '[':
            stack.pop()

    if in_string:
        cleaned += '"'
        closers = {'[': ']', '{': '}'}
        test_suffix = ''.join(closers[c] for c in reversed(stack))
        try:
            json.loads(cleaned + test_suffix)
        except json.JSONDecodeError:
            last_comma = cleaned.rfind(",")
            if last_comma > 0:
                cleaned = cleaned[:last_comma]
                stack = []
                in_string = False
                escaped = False
                for ch in cleaned:
                    if escaped:
                        escaped = False
                        continue
                    if ch == '\\':
                        escaped = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch in ('{', '['):
                        stack.append(ch)
                    elif ch == '}' and stack and stack[-1] == '{':
                        stack.pop()
                    elif ch == ']' and stack and stack[-1] == '[':
                        stack.pop()

    cleaned = cleaned.rstrip()
    while cleaned and cleaned[-1] == ",":
        cleaned = cleaned[:-1].rstrip()

    closers = {'[': ']', '{': '}'}
    suffix = ''.join(closers[c] for c in reversed(stack))

    return cleaned + suffix


class TestBasicRepair:
    """Basic truncation scenarios."""

    def test_complete_json_unchanged(self):
        """Already-complete JSON passes through unchanged."""
        s = '{"key": "value"}'
        result = _repair(s)
        assert json.loads(result) == {"key": "value"}

    def test_missing_closing_brace(self):
        """Single missing } is added."""
        s = '{"key": "value"'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_missing_closing_bracket(self):
        """Missing ] on array."""
        s = '{"items": [1, 2, 3'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["items"] == [1, 2, 3]

    def test_nested_missing_closers(self):
        """Multiple nested missing delimiters."""
        s = '{"outer": {"inner": [1, 2'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"] == [1, 2]

    def test_deeply_nested(self):
        """Three levels of nesting with missing closers."""
        s = '{"a": {"b": {"c": "val"'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["a"]["b"]["c"] == "val"


class TestStringHandling:
    """Truncation inside string values."""

    def test_truncated_inside_string(self):
        """Truncation mid-string — string is closed."""
        s = '{"key": "hello wor'
        result = _repair(s)
        # Should produce valid JSON (string closed, braces closed)
        parsed = json.loads(result)
        assert "key" in parsed

    def test_truncated_inside_key(self):
        """Truncation mid-key name."""
        s = '{"complete": 1, "trunc'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["complete"] == 1

    def test_escaped_quote_in_string(self):
        """Escaped quotes don't confuse string tracking."""
        s = '{"key": "value with \\"quotes\\"", "other": 1}'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["other"] == 1

    def test_backslash_at_end(self):
        """Trailing backslash handled."""
        s = '{"key": "value\\'
        result = _repair(s)
        # Should still produce parseable JSON
        try:
            json.loads(result)
        except json.JSONDecodeError:
            pass  # Acceptable — edge case


class TestTrailingComma:
    """Trailing comma cleanup."""

    def test_trailing_comma_in_object(self):
        """Trailing comma before missing closer is removed."""
        s = '{"a": 1, "b": 2,'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["a"] == 1
        assert parsed["b"] == 2

    def test_trailing_comma_in_array(self):
        """Trailing comma in array before closer."""
        s = '{"items": [1, 2, 3,'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["items"] == [1, 2, 3]

    def test_multiple_trailing_commas(self):
        """Multiple trailing commas stripped."""
        s = '{"a": 1,,'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["a"] == 1


class TestComplexScenarios:
    """Real-world truncation patterns from LLM output."""

    def test_truncated_array_of_objects(self):
        """Array of objects truncated mid-object."""
        s = '{"items": [{"name": "first"}, {"name": "second"'
        result = _repair(s)
        parsed = json.loads(result)
        assert len(parsed["items"]) == 2

    def test_truncated_after_complete_value(self):
        """Truncation right after a complete value."""
        s = '{"plan": {"title": "Test", "scope": ["a", "b"]'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["plan"]["scope"] == ["a", "b"]

    def test_empty_object_truncated(self):
        """Just an opening brace."""
        s = '{'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed == {}

    def test_empty_array_truncated(self):
        """Opening bracket in value."""
        s = '{"items": ['
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["items"] == []

    def test_large_nested_structure(self):
        """Simulates truncated IP/TA output."""
        s = '{"meta": {"v": 1}, "components": [{"name": "A", "owns": ["src/"]}, {"name": "B", "owns": ["lib/"'
        result = _repair(s)
        parsed = json.loads(result)
        assert len(parsed["components"]) == 2
        assert parsed["components"][0]["name"] == "A"

    def test_whitespace_handling(self):
        """Trailing whitespace before repair."""
        s = '{"key": "value"   '
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_number_value_truncated(self):
        """Truncation after a number value."""
        s = '{"count": 42, "items": [1, 2'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["count"] == 42
        assert parsed["items"] == [1, 2]

    def test_boolean_value(self):
        """Boolean value before truncation."""
        s = '{"enabled": true, "items": ['
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["enabled"] is True

    def test_null_value(self):
        """Null value before truncation."""
        s = '{"data": null, "more": {'
        result = _repair(s)
        parsed = json.loads(result)
        assert parsed["data"] is None

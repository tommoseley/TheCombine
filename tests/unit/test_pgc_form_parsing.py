"""Tests for PGC form parsing.

Regression test for the multi-select key extraction bug where
answers[X][] was incorrectly parsed as X] instead of X.
"""



class MockFormData:
    """Mock form data that mimics Starlette's form multi_items()."""

    def __init__(self, items: list):
        self._items = items

    def multi_items(self):
        return self._items


def _parse_pgc_form(form) -> dict:
    """Copy of the parsing function for testing."""
    answers = {}
    multi_values = {}

    for key, value in form.multi_items():
        if key.startswith("answers["):
            if key.endswith("[]"):
                q_id = key[8:-3]  # answers[X][] -> X (8 chars prefix, 3 chars suffix)
                if q_id not in multi_values:
                    multi_values[q_id] = []
                multi_values[q_id].append(value)
            else:
                q_id = key[8:-1]  # answers[X] -> X (8 chars prefix, 1 char suffix)
                if value == "true":
                    answers[q_id] = True
                elif value == "false":
                    answers[q_id] = False
                else:
                    answers[q_id] = value

    answers.update(multi_values)
    return answers


class TestParsePgcForm:
    """Tests for _parse_pgc_form function."""

    def test_single_choice_parsing(self):
        """Single choice values should parse correctly."""
        form = MockFormData([
            ("answers[USER_CONTEXT]", "home"),
        ])

        result = _parse_pgc_form(form)

        assert "USER_CONTEXT" in result
        assert result["USER_CONTEXT"] == "home"
        # Ensure no trailing bracket
        assert "USER_CONTEXT]" not in result

    def test_multi_choice_parsing(self):
        """Multi-choice values (with []) should parse correctly."""
        form = MockFormData([
            ("answers[MATH_SCOPE][]", "counting"),
            ("answers[MATH_SCOPE][]", "basic_arithmetic"),
        ])

        result = _parse_pgc_form(form)

        # Key should be MATH_SCOPE, NOT MATH_SCOPE]
        assert "MATH_SCOPE" in result
        assert "MATH_SCOPE]" not in result  # Regression check
        assert result["MATH_SCOPE"] == ["counting", "basic_arithmetic"]

    def test_yes_no_true_parsing(self):
        """Yes/no 'true' should parse to boolean True."""
        form = MockFormData([
            ("answers[PROGRESS_TRACKING]", "true"),
        ])

        result = _parse_pgc_form(form)

        assert result["PROGRESS_TRACKING"] is True

    def test_yes_no_false_parsing(self):
        """Yes/no 'false' should parse to boolean False."""
        form = MockFormData([
            ("answers[OFFLINE_MODE]", "false"),
        ])

        result = _parse_pgc_form(form)

        assert result["OFFLINE_MODE"] is False

    def test_free_text_parsing(self):
        """Free text values should parse as strings."""
        form = MockFormData([
            ("answers[EDUCATIONAL_STANDARDS]", "No specific standards required."),
        ])

        result = _parse_pgc_form(form)

        assert result["EDUCATIONAL_STANDARDS"] == "No specific standards required."

    def test_mixed_form_parsing(self):
        """Mixed form with all types should parse correctly."""
        form = MockFormData([
            ("answers[TARGET_PLATFORM][]", "web"),
            ("answers[TARGET_PLATFORM][]", "mobile"),
            ("answers[USER_CONTEXT]", "classroom"),
            ("answers[PROGRESS_TRACKING]", "true"),
            ("answers[NOTES]", "Some free text here"),
        ])

        result = _parse_pgc_form(form)

        assert result["TARGET_PLATFORM"] == ["web", "mobile"]
        assert result["USER_CONTEXT"] == "classroom"
        assert result["PROGRESS_TRACKING"] is True
        assert result["NOTES"] == "Some free text here"

        # Ensure no malformed keys
        assert "TARGET_PLATFORM]" not in result
        assert "USER_CONTEXT]" not in result

    def test_empty_multi_choice(self):
        """Empty multi-choice should create empty list."""
        form = MockFormData([
            ("answers[FEATURES][]", ""),
        ])

        result = _parse_pgc_form(form)

        assert "FEATURES" in result
        assert result["FEATURES"] == [""]

    def test_non_answer_fields_ignored(self):
        """Form fields not starting with 'answers[' should be ignored."""
        form = MockFormData([
            ("csrf_token", "abc123"),
            ("answers[QUESTION]", "value"),
            ("other_field", "ignored"),
        ])

        result = _parse_pgc_form(form)

        assert "QUESTION" in result
        assert "csrf_token" not in result
        assert "other_field" not in result

"""
Tests for pipeline_run_handler pure functions -- WS-CRAP-004.

Tests extracted pure functions: status_color, stage_color,
render_stages_html, render_replay_html, render_errors_html,
_html_escape.
"""

from app.domain.handlers.pipeline_run_handler import (
    _html_escape,
    status_color,
    stage_color,
    render_stages_html,
    render_replay_html,
    render_errors_html,
)


# =========================================================================
# _html_escape
# =========================================================================


class TestHtmlEscape:
    """Tests for _html_escape utility function."""

    def test_escapes_ampersand(self):
        assert _html_escape("a & b") == "a &amp; b"

    def test_escapes_less_than(self):
        assert _html_escape("a < b") == "a &lt; b"

    def test_escapes_greater_than(self):
        assert _html_escape("a > b") == "a &gt; b"

    def test_multiple_escapes(self):
        assert _html_escape("<a>&b</a>") == "&lt;a&gt;&amp;b&lt;/a&gt;"

    def test_none_returns_empty(self):
        assert _html_escape(None) == ""

    def test_non_string_converted(self):
        assert _html_escape(42) == "42"

    def test_empty_string(self):
        assert _html_escape("") == ""


# =========================================================================
# status_color
# =========================================================================


class TestStatusColor:
    """Tests for status_color pure function."""

    def test_completed_is_emerald(self):
        assert status_color("completed") == "emerald"

    def test_failed_is_red(self):
        assert status_color("failed") == "red"

    def test_unknown_is_red(self):
        assert status_color("unknown") == "red"

    def test_any_non_completed_is_red(self):
        assert status_color("running") == "red"
        assert status_color("") == "red"


# =========================================================================
# stage_color
# =========================================================================


class TestStageColor:
    """Tests for stage_color pure function."""

    def test_completed_is_emerald(self):
        assert stage_color("completed") == "emerald"

    def test_failed_is_red(self):
        assert stage_color("failed") == "red"

    def test_other_is_gray(self):
        assert stage_color("running") == "gray"
        assert stage_color("pending") == "gray"
        assert stage_color("") == "gray"


# =========================================================================
# render_stages_html
# =========================================================================


class TestRenderStagesHtml:
    """Tests for render_stages_html pure function."""

    def test_single_completed_stage(self):
        stages = {"extraction": {"status": "completed"}}
        html = render_stages_html(stages)
        assert "extraction" in html
        assert "completed" in html
        assert "bg-emerald-500" in html

    def test_failed_stage_with_error(self):
        stages = {
            "validation": {
                "status": "failed",
                "error": "Schema mismatch",
            }
        }
        html = render_stages_html(stages)
        assert "validation" in html
        assert "bg-red-500" in html
        assert "Schema mismatch" in html

    def test_unknown_status_default(self):
        stages = {"load": {}}
        html = render_stages_html(stages)
        assert "unknown" in html
        assert "bg-gray-500" in html

    def test_empty_stages(self):
        assert render_stages_html({}) == ""

    def test_multiple_stages(self):
        stages = {
            "extract": {"status": "completed"},
            "validate": {"status": "failed", "error": "bad"},
            "load": {"status": "pending"},
        }
        html = render_stages_html(stages)
        assert "extract" in html
        assert "validate" in html
        assert "load" in html

    def test_html_escaping_in_stage_name(self):
        stages = {"<script>": {"status": "completed"}}
        html = render_stages_html(stages)
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_html_escaping_in_error(self):
        stages = {"test": {"status": "failed", "error": "<b>bad</b>"}}
        html = render_stages_html(stages)
        assert "&lt;b&gt;bad&lt;/b&gt;" in html

    def test_no_error_html_when_no_error(self):
        stages = {"test": {"status": "completed"}}
        html = render_stages_html(stages)
        assert "text-red-500" not in html


# =========================================================================
# render_replay_html
# =========================================================================


class TestRenderReplayHtml:
    """Tests for render_replay_html pure function."""

    def test_short_values_displayed_fully(self):
        replay = {"hash": "abc123"}
        html = render_replay_html(replay)
        assert "hash" in html
        assert "abc123" in html

    def test_long_values_truncated(self):
        replay = {"long_hash": "a" * 20}
        html = render_replay_html(replay)
        assert "aaaaaaaaaaaa..." in html

    def test_falsy_values_skipped(self):
        replay = {"empty": "", "none": None, "zero": 0, "false": False}
        html = render_replay_html(replay)
        assert html == ""

    def test_empty_replay(self):
        assert render_replay_html({}) == ""

    def test_multiple_values(self):
        replay = {"key1": "val1", "key2": "val2"}
        html = render_replay_html(replay)
        assert "key1" in html
        assert "key2" in html

    def test_html_escaping(self):
        replay = {"key": "<script>"}
        html = render_replay_html(replay)
        assert "&lt;script&gt;" in html


# =========================================================================
# render_errors_html
# =========================================================================


class TestRenderErrorsHtml:
    """Tests for render_errors_html pure function."""

    def test_none_returns_empty(self):
        assert render_errors_html(None) == ""

    def test_empty_dict_returns_empty(self):
        assert render_errors_html({}) == ""

    def test_dependency_errors(self):
        errors = {"dependency_errors": [{"msg": "a"}, {"msg": "b"}]}
        html = render_errors_html(errors)
        assert "Dependency errors: 2" in html

    def test_hierarchy_errors(self):
        errors = {"hierarchy_errors": [{"msg": "a"}]}
        html = render_errors_html(errors)
        assert "Hierarchy errors: 1" in html

    def test_cycle_traces(self):
        errors = {"cycle_traces": [["a", "b", "a"]]}
        html = render_errors_html(errors)
        assert "Cycles detected: 1" in html

    def test_all_error_types(self):
        errors = {
            "dependency_errors": [1, 2],
            "hierarchy_errors": [1],
            "cycle_traces": [1, 2, 3],
        }
        html = render_errors_html(errors)
        assert "Dependency errors: 2" in html
        assert "Hierarchy errors: 1" in html
        assert "Cycles detected: 3" in html

    def test_empty_error_lists(self):
        errors = {
            "dependency_errors": [],
            "hierarchy_errors": [],
            "cycle_traces": [],
        }
        html = render_errors_html(errors)
        assert html == ""

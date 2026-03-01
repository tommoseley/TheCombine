"""
Tier-1 tests for view_pure.py -- pure data transformations extracted from view_routes.

No DB, no I/O. All tests use plain dicts and simple stub objects.
WS-CRAP-006: Testability refactoring.
"""

from types import SimpleNamespace

from app.web.routes.public.view_pure import (
    extract_web_fragment_id,
    find_component_by_schema_id,
    render_placeholder_html,
)


# =============================================================================
# extract_web_fragment_id
# =============================================================================

class TestExtractWebFragmentId:
    def test_object_with_bindings(self):
        component = SimpleNamespace(
            view_bindings={"web": {"fragment_id": "frag-001"}}
        )
        assert extract_web_fragment_id(component) == "frag-001"

    def test_dict_with_bindings(self):
        component = {"view_bindings": {"web": {"fragment_id": "frag-002"}}}
        assert extract_web_fragment_id(component) == "frag-002"

    def test_none_component(self):
        assert extract_web_fragment_id(None) is None

    def test_no_view_bindings(self):
        component = SimpleNamespace(view_bindings=None)
        assert extract_web_fragment_id(component) is None

    def test_empty_view_bindings(self):
        component = SimpleNamespace(view_bindings={})
        assert extract_web_fragment_id(component) is None

    def test_no_web_binding(self):
        component = SimpleNamespace(view_bindings={"mobile": {"fragment_id": "m1"}})
        assert extract_web_fragment_id(component) is None

    def test_no_fragment_id(self):
        component = SimpleNamespace(view_bindings={"web": {"other_key": "value"}})
        assert extract_web_fragment_id(component) is None

    def test_dict_no_view_bindings_key(self):
        component = {"name": "something"}
        assert extract_web_fragment_id(component) is None

    def test_non_dict_non_object(self):
        assert extract_web_fragment_id("string") is None
        assert extract_web_fragment_id(42) is None


# =============================================================================
# render_placeholder_html
# =============================================================================

class TestRenderPlaceholderHtml:
    def test_basic_placeholder(self):
        html = render_placeholder_html("Error Title", [])
        assert "Error Title" in html
        assert "border-amber-300" in html

    def test_with_details(self):
        html = render_placeholder_html("Warning", ["detail 1", "detail 2"])
        assert "detail 1" in html
        assert "detail 2" in html

    def test_empty_details(self):
        html = render_placeholder_html("Title", [])
        assert "Title" in html
        # Should not crash with empty list

    def test_html_structure(self):
        html = render_placeholder_html("Test", ["info"])
        assert "<div" in html
        assert "text-amber-800" in html
        assert "text-gray-500" in html


# =============================================================================
# find_component_by_schema_id
# =============================================================================

class TestFindComponentBySchemaId:
    def test_found_by_attribute(self):
        components = [
            SimpleNamespace(schema_id="schema:A", name="Component A"),
            SimpleNamespace(schema_id="schema:B", name="Component B"),
        ]
        result = find_component_by_schema_id(components, "schema:B")
        assert result.name == "Component B"

    def test_found_by_dict_key(self):
        components = [
            {"schema_id": "schema:A", "name": "A"},
            {"schema_id": "schema:B", "name": "B"},
        ]
        result = find_component_by_schema_id(components, "schema:A")
        assert result["name"] == "A"

    def test_not_found(self):
        components = [SimpleNamespace(schema_id="schema:A")]
        result = find_component_by_schema_id(components, "schema:Z")
        assert result is None

    def test_empty_list(self):
        assert find_component_by_schema_id([], "schema:A") is None

    def test_first_match_returned(self):
        components = [
            SimpleNamespace(schema_id="schema:A", order=1),
            SimpleNamespace(schema_id="schema:A", order=2),
        ]
        result = find_component_by_schema_id(components, "schema:A")
        assert result.order == 1

    def test_mixed_types(self):
        components = [
            SimpleNamespace(schema_id="schema:A"),
            {"schema_id": "schema:B"},
        ]
        assert find_component_by_schema_id(components, "schema:A") is not None
        assert find_component_by_schema_id(components, "schema:B") is not None

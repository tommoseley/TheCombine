"""
Tier-1 tests for render_model_pure.py — pure data transformation functions
extracted from RenderModelBuilder.

No I/O, no DB, no mocking of external services.
"""

import hashlib
import json

from app.domain.services.render_model_pure import (
    resolve_pointer,
    compute_schema_bundle_hash,
    collect_component_ids_from_sections,
    flatten_nested_list,
    process_container_repeat,
    build_parent_as_data,
    apply_derivation,
    build_context,
    resolve_docdef_id,
    extract_document_type,
    sort_sections,
)


# =========================================================================
# resolve_pointer
# =========================================================================

class TestResolvePointer:
    """Tests for JSON pointer resolution."""

    def test_empty_pointer_returns_data(self):
        data = {"a": 1}
        assert resolve_pointer(data, "") is data

    def test_slash_pointer_returns_data(self):
        data = {"a": 1}
        assert resolve_pointer(data, "/") is data

    def test_none_pointer_returns_data(self):
        data = {"a": 1}
        assert resolve_pointer(data, None) is data

    def test_single_level_key(self):
        data = {"epics": [1, 2, 3]}
        assert resolve_pointer(data, "/epics") == [1, 2, 3]

    def test_nested_key(self):
        data = {"a": {"b": {"c": 42}}}
        assert resolve_pointer(data, "/a/b/c") == 42

    def test_missing_key_returns_none(self):
        data = {"a": 1}
        assert resolve_pointer(data, "/b") is None

    def test_missing_nested_key_returns_none(self):
        data = {"a": {"b": 1}}
        assert resolve_pointer(data, "/a/c") is None

    def test_list_index(self):
        data = {"items": ["x", "y", "z"]}
        assert resolve_pointer(data, "/items/1") == "y"

    def test_list_index_out_of_range(self):
        data = {"items": ["x"]}
        assert resolve_pointer(data, "/items/5") is None

    def test_list_index_non_integer(self):
        data = {"items": ["x"]}
        assert resolve_pointer(data, "/items/abc") is None

    def test_traverse_through_list_into_dict(self):
        data = {"items": [{"name": "a"}, {"name": "b"}]}
        assert resolve_pointer(data, "/items/0/name") == "a"

    def test_none_value_in_path(self):
        data = {"a": None}
        assert resolve_pointer(data, "/a/b") is None

    def test_scalar_in_path(self):
        data = {"a": 42}
        assert resolve_pointer(data, "/a/b") is None

    def test_leading_slash_stripped(self):
        data = {"x": 1}
        assert resolve_pointer(data, "x") == 1

    def test_multiple_slashes(self):
        data = {"a": {"b": 1}}
        # Extra empty parts from double-slash are skipped
        assert resolve_pointer(data, "/a//b") == 1


# =========================================================================
# compute_schema_bundle_hash
# =========================================================================

class TestComputeSchemaBundleHash:
    """Tests for deterministic schema bundle hashing."""

    def test_empty_bundle(self):
        bundle = {"schemas": {}}
        result = compute_schema_bundle_hash(bundle)
        assert result.startswith("sha256:")
        assert len(result) == 7 + 64  # "sha256:" + 64 hex chars

    def test_deterministic(self):
        bundle = {"schemas": {"a": {"type": "object"}}}
        h1 = compute_schema_bundle_hash(bundle)
        h2 = compute_schema_bundle_hash(bundle)
        assert h1 == h2

    def test_key_order_irrelevant(self):
        """Keys are sorted in JSON serialization, so order does not matter."""
        bundle1 = {"schemas": {"a": 1, "b": 2}}
        bundle2 = {"schemas": {"b": 2, "a": 1}}
        assert compute_schema_bundle_hash(bundle1) == compute_schema_bundle_hash(bundle2)

    def test_different_bundles_different_hashes(self):
        h1 = compute_schema_bundle_hash({"schemas": {"a": 1}})
        h2 = compute_schema_bundle_hash({"schemas": {"a": 2}})
        assert h1 != h2

    def test_matches_manual_computation(self):
        bundle = {"schemas": {}}
        expected_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(expected_json.encode()).hexdigest()
        result = compute_schema_bundle_hash(bundle)
        assert result == f"sha256:{expected_hash}"


# =========================================================================
# collect_component_ids_from_sections
# =========================================================================

class TestCollectComponentIdsFromSections:
    """Tests for component ID collection from section configs."""

    def test_empty_sections(self):
        assert collect_component_ids_from_sections([]) == []

    def test_single_section(self):
        sections = [{"component_id": "comp:A:1.0.0"}]
        assert collect_component_ids_from_sections(sections) == ["comp:A:1.0.0"]

    def test_dedup_preserves_first(self):
        sections = [
            {"component_id": "comp:A:1.0.0", "order": 1},
            {"component_id": "comp:A:1.0.0", "order": 2},
        ]
        assert collect_component_ids_from_sections(sections) == ["comp:A:1.0.0"]

    def test_preserves_input_order(self):
        """Function preserves input order; it does NOT sort by 'order' field."""
        sections = [
            {"component_id": "comp:B:1.0.0", "order": 2},
            {"component_id": "comp:A:1.0.0", "order": 1},
        ]
        assert collect_component_ids_from_sections(sections) == [
            "comp:B:1.0.0",
            "comp:A:1.0.0",
        ]

    def test_skips_missing_component_id(self):
        sections = [
            {"component_id": "comp:A:1.0.0"},
            {"not_a_component": True},
            {"component_id": None},
        ]
        assert collect_component_ids_from_sections(sections) == ["comp:A:1.0.0"]


# =========================================================================
# flatten_nested_list
# =========================================================================

class TestFlattenNestedList:
    """Tests for nested list flattening into block descriptors."""

    def test_basic_nested_list(self):
        data = {
            "parents": [
                {"name": "P1", "items": [{"val": 1}, {"val": 2}]},
                {"name": "P2", "items": [{"val": 3}]},
            ]
        }
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={"parent_name": "/name"},
            document_data=data,
        )
        assert len(result) == 3
        assert result[0]["key"] == "sec1:0:0"
        assert result[0]["data"] == {"val": 1}
        assert result[0]["context"] == {"parent_name": "P1"}
        assert result[2]["key"] == "sec1:1:0"
        assert result[2]["data"] == {"val": 3}

    def test_missing_repeat_over(self):
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/nonexistent",
            context_mapping={},
            document_data={"other": 1},
        )
        assert result == []

    def test_non_list_repeat_over(self):
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            document_data={"parents": "not a list"},
        )
        assert result == []

    def test_non_dict_parent_skipped(self):
        data = {"parents": ["string_parent", {"items": [{"val": 1}]}]}
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            document_data=data,
        )
        assert len(result) == 1
        assert result[0]["key"] == "sec1:1:0"

    def test_scalar_items_wrapped(self):
        data = {"parents": [{"items": ["a", "b"]}]}
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            document_data=data,
        )
        assert result[0]["data"] == {"value": "a"}
        assert result[1]["data"] == {"value": "b"}

    def test_empty_items_skipped(self):
        data = {"parents": [{"items": []}]}
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            document_data=data,
        )
        assert result == []

    def test_no_context_mapping(self):
        data = {"parents": [{"items": [{"val": 1}]}]}
        result = flatten_nested_list(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            document_data=data,
        )
        assert result[0]["context"] is None


# =========================================================================
# process_container_repeat
# =========================================================================

class TestProcessContainerRepeat:
    """Tests for container-with-repeat processing."""

    def test_basic_container_repeat(self):
        data = {
            "parents": [
                {"title": "P1", "items": [{"val": 1}]},
                {"title": "P2", "items": [{"val": 2}, {"val": 3}]},
            ]
        }
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={"title": "/title"},
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
            document_data=data,
        )
        assert len(result) == 2
        assert result[0]["key"] == "sec1:container:0"
        assert result[0]["data"] == {"items": [{"val": 1}]}
        assert result[0]["context"] == {"title": "P1"}
        assert result[1]["data"] == {"items": [{"val": 2}, {"val": 3}]}

    def test_parent_as_data_mode(self):
        """When source_pointer is "/" the parent is used as block data."""
        data = {"parents": [{"name": "P1", "score": 10}]}
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
            document_data=data,
        )
        assert len(result) == 1
        assert result[0]["data"] == {"name": "P1", "score": 10}

    def test_parent_as_data_with_exclude(self):
        data = {"parents": [{"name": "P1", "internal_id": "x"}]}
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[],
            exclude_fields=["internal_id"],
            detail_ref_template=None,
            derivation_functions={},
            document_data=data,
        )
        assert "internal_id" not in result[0]["data"]
        assert result[0]["data"]["name"] == "P1"

    def test_empty_parents_returns_empty(self):
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
            document_data={"parents": []},
        )
        assert result == []

    def test_non_dict_parent_skipped(self):
        data = {"parents": ["not_a_dict"]}
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
            document_data=data,
        )
        assert result == []

    def test_missing_items_in_parent_skipped(self):
        data = {"parents": [{"title": "P1"}]}
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
            document_data=data,
        )
        assert result == []

    def test_scalar_items_wrapped(self):
        data = {"parents": [{"items": ["x", "y"]}]}
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/items",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
            document_data=data,
        )
        assert result[0]["data"] == {"items": [{"value": "x"}, {"value": "y"}]}

    def test_with_derived_fields(self):
        def fake_derive(data):
            return "derived_value"

        data = {"parents": [{"name": "P1"}]}
        result = process_container_repeat(
            section_id="sec1",
            source_pointer="/",
            repeat_over_pointer="/parents",
            context_mapping={},
            derived_fields=[{"field": "level", "function": "fake", "source": "/"}],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={"fake": fake_derive},
            document_data=data,
        )
        assert result[0]["data"]["level"] == "derived_value"


# =========================================================================
# build_parent_as_data
# =========================================================================

class TestBuildParentAsData:
    """Tests for parent-as-data assembly."""

    def test_basic_copy(self):
        parent = {"a": 1, "b": 2}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
        )
        assert result == {"a": 1, "b": 2}

    def test_exclude_fields(self):
        parent = {"a": 1, "b": 2, "c": 3}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[],
            exclude_fields=["b"],
            detail_ref_template=None,
            derivation_functions={},
        )
        assert result == {"a": 1, "c": 3}

    def test_derived_fields_applied(self):
        parent = {"risks": [{"likelihood": "high"}]}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[{"field": "level", "function": "risk_level", "source": "/risks"}],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={"risk_level": lambda risks: "high" if any(r.get("likelihood") == "high" for r in risks) else "low"},
        )
        assert result["level"] == "high"

    def test_derived_field_source_root(self):
        parent = {"name": "test"}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[{"field": "echo", "function": "echo_fn", "source": "/"}],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={"echo_fn": lambda d: d.get("name", "")},
        )
        assert result["echo"] == "test"

    def test_derived_field_missing_source(self):
        parent = {"name": "test"}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[{"field": "x", "function": "fn", "source": "/nonexistent"}],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={"fn": lambda d: len(d)},
        )
        # Source resolves to None, gets defaulted to []
        assert result["x"] == 0

    def test_derived_field_unknown_function_skipped(self):
        parent = {"name": "test"}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[{"field": "x", "function": "unknown_fn", "source": "/"}],
            exclude_fields=[],
            detail_ref_template=None,
            derivation_functions={},
        )
        assert "x" not in result

    def test_detail_ref_template(self):
        parent = {"id": "epic-1", "name": "Epic 1"}
        result = build_parent_as_data(
            parent=parent,
            derived_fields=[],
            exclude_fields=[],
            detail_ref_template={
                "document_type": "EpicDetailView",
                "params": {"epic_id": "/id"},
            },
            derivation_functions={},
        )
        assert result["detail_ref"] == {
            "document_type": "EpicDetailView",
            "params": {"epic_id": "epic-1"},
        }


# =========================================================================
# apply_derivation
# =========================================================================

class TestApplyDerivation:
    """Tests for derivation function application."""

    def _make_fns(self):
        return {
            "count": lambda items: len(items) if isinstance(items, list) else 0,
            "sum": lambda items: sum(items) if isinstance(items, list) else 0,
        }

    def test_basic_derivation(self):
        fns = self._make_fns()
        result = apply_derivation(
            source_pointer="/items",
            func_name="count",
            omit_when_empty=False,
            derivation_functions=fns,
            document_data={"items": [1, 2, 3]},
        )
        assert result == 3

    def test_unknown_function_returns_none(self):
        result = apply_derivation(
            source_pointer="/items",
            func_name="nonexistent",
            omit_when_empty=False,
            derivation_functions={},
            document_data={"items": [1]},
        )
        assert result is None

    def test_root_source(self):
        fns = {"echo": lambda d: d}
        result = apply_derivation(
            source_pointer="/",
            func_name="echo",
            omit_when_empty=False,
            derivation_functions=fns,
            document_data={"key": "val"},
        )
        assert result == {"key": "val"}

    def test_omit_when_empty_with_empty_list(self):
        fns = self._make_fns()
        result = apply_derivation(
            source_pointer="/items",
            func_name="count",
            omit_when_empty=True,
            derivation_functions=fns,
            document_data={"items": []},
        )
        assert result is None

    def test_omit_when_empty_with_none_source(self):
        fns = self._make_fns()
        result = apply_derivation(
            source_pointer="/nonexistent",
            func_name="count",
            omit_when_empty=True,
            derivation_functions=fns,
            document_data={},
        )
        # Source resolves to None -> default to [] -> empty list -> omitted
        assert result is None

    def test_omit_when_empty_with_empty_dict(self):
        fns = {"fn": lambda d: "computed"}
        result = apply_derivation(
            source_pointer="/data",
            func_name="fn",
            omit_when_empty=True,
            derivation_functions=fns,
            document_data={"data": {}},
        )
        assert result is None

    def test_omit_when_empty_false_allows_empty_list(self):
        fns = self._make_fns()
        result = apply_derivation(
            source_pointer="/items",
            func_name="count",
            omit_when_empty=False,
            derivation_functions=fns,
            document_data={"items": []},
        )
        assert result == 0

    def test_missing_source_defaults_to_empty_list(self):
        fns = self._make_fns()
        result = apply_derivation(
            source_pointer="/nonexistent",
            func_name="count",
            omit_when_empty=False,
            derivation_functions=fns,
            document_data={},
        )
        assert result == 0


# =========================================================================
# build_context
# =========================================================================

class TestBuildContext:
    """Tests for context dict building."""

    def test_empty_mapping_returns_none(self):
        assert build_context({"a": 1}, {}) is None

    def test_basic_mapping(self):
        parent = {"name": "Epic 1", "id": "e1"}
        result = build_context(parent, {"title": "/name", "epic_id": "/id"})
        assert result == {"title": "Epic 1", "epic_id": "e1"}

    def test_missing_value_omitted(self):
        parent = {"name": "Epic 1"}
        result = build_context(parent, {"title": "/name", "missing": "/nonexistent"})
        assert result == {"title": "Epic 1"}

    def test_all_values_missing_returns_none(self):
        parent = {}
        result = build_context(parent, {"a": "/x", "b": "/y"})
        assert result is None


# =========================================================================
# resolve_docdef_id
# =========================================================================

class TestResolveDocdefId:
    """Tests for docdef ID resolution."""

    def test_short_name(self):
        assert resolve_docdef_id("EpicDetailView") == "docdef:EpicDetailView:1.0.0"

    def test_already_full(self):
        assert resolve_docdef_id("docdef:EpicDetailView:1.0.0") == "docdef:EpicDetailView:1.0.0"

    def test_different_version(self):
        assert resolve_docdef_id("docdef:Foo:2.0.0") == "docdef:Foo:2.0.0"


# =========================================================================
# extract_document_type
# =========================================================================

class TestExtractDocumentType:
    """Tests for document type extraction from docdef ID."""

    def test_standard_format(self):
        assert extract_document_type("docdef:EpicDetailView:1.0.0") == "EpicDetailView"

    def test_no_colons(self):
        assert extract_document_type("SomeType") == "SomeType"

    def test_two_parts(self):
        assert extract_document_type("docdef:Foo") == "Foo"


# =========================================================================
# sort_sections
# =========================================================================

class TestSortSections:
    """Tests for section sorting."""

    def test_already_sorted(self):
        sections = [{"order": 1}, {"order": 2}]
        assert sort_sections(sections) == [{"order": 1}, {"order": 2}]

    def test_reverse_order(self):
        sections = [{"order": 3}, {"order": 1}, {"order": 2}]
        result = sort_sections(sections)
        assert [s["order"] for s in result] == [1, 2, 3]

    def test_missing_order_defaults_to_zero(self):
        sections = [{"order": 1}, {"name": "no_order"}]
        result = sort_sections(sections)
        assert result[0] == {"name": "no_order"}
        assert result[1] == {"order": 1}

    def test_empty_list(self):
        assert sort_sections([]) == []

    def test_does_not_mutate_input(self):
        sections = [{"order": 2}, {"order": 1}]
        sort_sections(sections)
        assert sections[0]["order"] == 2  # original unchanged

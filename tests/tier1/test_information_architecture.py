"""Golden contract tests for Information Architecture (ADR-054).

Tests validate alignment between:
- Schema Contract (output.schema.json)
- Information Architecture Contract (package.yaml information_architecture)
- Rendering targets (package.yaml rendering.detail_html, rendering.pdf)

WS-IA-001: TA golden contract tests (C1-C8)
WS-IA-002: Extended to PD, IPP, IPF (parametrized C1-C5) + SPA generic rendering (C6-C7)
WS-IA-003: Block rendering model for TA (C6-C13, Level 2 IA, IABlockRenderer)
"""

import json
from pathlib import Path

import pytest
import yaml

COMBINE_CONFIG = Path("combine-config/document_types")

# System envelope fields excluded from IA coverage checks.
# These are metadata containers (schema_version, artifact_id, timestamps),
# not renderable content sections.
SYSTEM_FIELDS = {"meta"}

# All Tier-1 document types that must have governed IA
TIER1_DOC_TYPES = [
    "technical_architecture",
    "project_discovery",
    "primary_implementation_plan",
    "implementation_plan",
]

# Valid render_as vocabulary for Level 2 IA binds
VALID_RENDER_AS = {
    "paragraph", "list", "ordered-list", "table",
    "key-value-pairs", "card-list", "nested-object",
}


def _normalize_bind(bind):
    """Normalize a bind entry: string → {path: str}, dict passes through."""
    if isinstance(bind, str):
        return {"path": bind}
    return bind


def _extract_bind_paths(section):
    """Extract bind paths from a section, handling both Level 1 and Level 2 formats."""
    return [_normalize_bind(b)["path"] for b in section.get("binds", [])]


def _load_package(doc_type: str) -> dict:
    """Load package.yaml for a document type (latest release)."""
    type_dir = COMBINE_CONFIG / doc_type
    releases_dir = type_dir / "releases"
    if not releases_dir.exists():
        pytest.skip(f"No releases dir for {doc_type}")
    versions = sorted(releases_dir.iterdir())
    if not versions:
        pytest.skip(f"No versions for {doc_type}")
    latest = versions[-1]
    pkg_file = latest / "package.yaml"
    assert pkg_file.exists(), f"package.yaml not found: {pkg_file}"
    with open(pkg_file) as f:
        return yaml.safe_load(f)


def _load_schema(doc_type: str) -> dict:
    """Load output.schema.json for a document type (latest release)."""
    type_dir = COMBINE_CONFIG / doc_type
    releases_dir = type_dir / "releases"
    versions = sorted(releases_dir.iterdir())
    latest = versions[-1]
    schema_file = latest / "schemas" / "output.schema.json"
    assert schema_file.exists(), f"schema not found: {schema_file}"
    with open(schema_file) as f:
        return json.load(f)


def _get_schema_top_level_fields(schema: dict) -> set:
    """Get top-level property names from a JSON schema."""
    return set(schema.get("properties", {}).keys())


def _get_schema_required_fields(schema: dict) -> set:
    """Get required field names from a JSON schema, excluding system envelope fields."""
    return set(schema.get("required", [])) - SYSTEM_FIELDS


# --- Criteria 1-5: Golden Contract Tests (parametrized across all Tier-1 types) ---


class TestGoldenContracts:
    """Validate IA <-> Schema <-> Rendering alignment for all Tier-1 types."""

    @pytest.mark.parametrize("doc_type", TIER1_DOC_TYPES)
    def test_c1_binds_exist_in_schema(self, doc_type):
        """C1: Every binds path in IA sections resolves to a valid schema field."""
        pkg = _load_package(doc_type)
        schema = _load_schema(doc_type)

        ia = pkg.get("information_architecture")
        assert ia is not None, f"{doc_type}: information_architecture section missing from package.yaml"

        schema_fields = _get_schema_top_level_fields(schema)

        for section in ia["sections"]:
            for path in _extract_bind_paths(section):
                assert path in schema_fields, (
                    f"{doc_type}: Section '{section['id']}' binds '{path}' which is not a "
                    f"schema property. Valid: {sorted(schema_fields)}"
                )

    @pytest.mark.parametrize("doc_type", TIER1_DOC_TYPES)
    def test_c2_required_fields_covered(self, doc_type):
        """C2: Every schema-required field appears in at least one IA section's binds."""
        pkg = _load_package(doc_type)
        schema = _load_schema(doc_type)

        ia = pkg.get("information_architecture")
        assert ia is not None, f"{doc_type}: information_architecture section missing from package.yaml"

        all_binds = set()
        for section in ia["sections"]:
            all_binds.update(_extract_bind_paths(section))

        required = _get_schema_required_fields(schema)

        for field in required:
            assert field in all_binds, (
                f"{doc_type}: Schema-required field '{field}' is not bound by any IA section. "
                f"Bound fields: {sorted(all_binds)}"
            )

    @pytest.mark.parametrize("doc_type", TIER1_DOC_TYPES)
    def test_c3_html_sections_valid(self, doc_type):
        """C3: Every section in rendering.detail_html tabs exists in IA sections."""
        pkg = _load_package(doc_type)

        ia = pkg.get("information_architecture")
        assert ia is not None, f"{doc_type}: information_architecture section missing from package.yaml"

        rendering = pkg.get("rendering")
        assert rendering is not None, f"{doc_type}: rendering section missing from package.yaml"

        detail_html = rendering.get("detail_html")
        assert detail_html is not None, f"{doc_type}: rendering.detail_html missing from package.yaml"

        declared_ids = {s["id"] for s in ia["sections"]}

        for tab in detail_html.get("tabs", []):
            for section_id in tab.get("sections", []):
                assert section_id in declared_ids, (
                    f"{doc_type}: Tab '{tab['id']}' references section '{section_id}' "
                    f"which is not declared in information_architecture. "
                    f"Declared: {sorted(declared_ids)}"
                )

    @pytest.mark.parametrize("doc_type", TIER1_DOC_TYPES)
    def test_c4_no_orphaned_sections(self, doc_type):
        """C4: No IA section is unreferenced by any rendering target."""
        pkg = _load_package(doc_type)

        ia = pkg.get("information_architecture")
        assert ia is not None, f"{doc_type}: information_architecture section missing from package.yaml"

        rendering = pkg.get("rendering")
        assert rendering is not None, f"{doc_type}: rendering section missing from package.yaml"

        declared_ids = {s["id"] for s in ia["sections"]}

        # Collect all referenced section IDs across all rendering targets
        referenced = set()
        detail_html = rendering.get("detail_html", {})
        for tab in detail_html.get("tabs", []):
            referenced.update(tab.get("sections", []))

        pdf = rendering.get("pdf", {})
        referenced.update(pdf.get("linear_order", []))

        orphaned = declared_ids - referenced
        assert not orphaned, (
            f"{doc_type}: IA sections not referenced by any rendering target: {sorted(orphaned)}"
        )

    @pytest.mark.parametrize("doc_type", TIER1_DOC_TYPES)
    def test_c5_pdf_linear_order_valid(self, doc_type):
        """C5: Every entry in rendering.pdf.linear_order references a declared section ID."""
        pkg = _load_package(doc_type)

        ia = pkg.get("information_architecture")
        assert ia is not None, f"{doc_type}: information_architecture section missing from package.yaml"

        rendering = pkg.get("rendering")
        assert rendering is not None, f"{doc_type}: rendering section missing from package.yaml"

        pdf = rendering.get("pdf")
        assert pdf is not None, f"{doc_type}: rendering.pdf missing from package.yaml"

        linear_order = pdf.get("linear_order")
        assert linear_order is not None, f"{doc_type}: rendering.pdf.linear_order missing"

        declared_ids = {s["id"] for s in ia["sections"]}

        for section_id in linear_order:
            assert section_id in declared_ids, (
                f"{doc_type}: pdf.linear_order references '{section_id}' "
                f"which is not declared in information_architecture. "
                f"Declared: {sorted(declared_ids)}"
            )


# --- TA-Specific Tests (from WS-IA-001) ---


class TestTASpecific:
    """TA-specific rendering assertions."""

    def test_ta_has_content_tabs(self):
        """TA detail_html defines tabs for workflows, components, data_models, interfaces."""
        pkg = _load_package("technical_architecture")

        rendering = pkg.get("rendering")
        assert rendering is not None, "rendering section missing from package.yaml"

        detail_html = rendering.get("detail_html")
        assert detail_html is not None, "rendering.detail_html missing"

        tab_ids = {t["id"] for t in detail_html.get("tabs", [])}

        required_tabs = {"components", "workflows", "data_models", "interfaces"}
        missing = required_tabs - tab_ids
        assert not missing, f"TA missing required tabs: {sorted(missing)}"

    def test_ta_tabs_have_sections(self):
        """Each TA content tab references at least one section."""
        pkg = _load_package("technical_architecture")

        rendering = pkg.get("rendering", {})
        detail_html = rendering.get("detail_html")
        assert detail_html is not None, "rendering.detail_html missing"

        for tab in detail_html.get("tabs", []):
            assert tab.get("sections"), (
                f"Tab '{tab.get('id', '?')}' has no sections"
            )


# --- SPA Renderer Tests (grep-based, Mode B) ---


class TestSPARenderer:
    """Verify SPA renders from config, not hardcoded definitions."""

    SPA_VIEWER = Path("spa/src/components/viewers/ConfigDrivenDocViewer.jsx")
    SPA_FULL = Path("spa/src/components/FullDocumentViewer.jsx")

    def test_no_hardcoded_section_routing(self):
        """SPA does not contain hardcoded section-to-tab mapping constants."""
        content = self.SPA_VIEWER.read_text()

        hardcoded_markers = [
            "DATA_MODEL_IDS",
            "INTERFACE_IDS",
            "QUALITY_IDS",
            "WORKFLOW_IDS",
            "COMPONENT_IDS",
        ]

        found = [m for m in hardcoded_markers if m in content]
        assert not found, (
            f"ConfigDrivenDocViewer.jsx still contains hardcoded "
            f"section routing constants: {found}. "
            f"These should be replaced with config-driven tab rendering."
        )

    def test_viewer_reads_rendering_config(self):
        """SPA viewer reads tab structure from rendering config."""
        viewer_content = self.SPA_VIEWER.read_text() if self.SPA_VIEWER.exists() else ""
        full_content = self.SPA_FULL.read_text()
        combined = viewer_content + full_content

        config_markers = [
            "detail_html",
            "rendering_config",
            "information_architecture",
        ]

        found = [m for m in config_markers if m in combined]
        assert found, (
            "Neither TechnicalArchitectureViewer nor FullDocumentViewer "
            "reads rendering config (detail_html/rendering_config/information_architecture) "
            "from the API response. Tabs are still hardcoded."
        )

    @pytest.mark.parametrize("doc_type", TIER1_DOC_TYPES)
    def test_all_tab_sections_resolve_to_binds(self, doc_type):
        """Every section ID referenced by a tab must resolve to an IA section with at least one bind.

        This validates the IA config is sufficient for raw-content rendering
        (no DocDef needed) — every tab section has bindings that can pull
        fields directly from raw_content.
        """
        pkg = _load_package(doc_type)

        ia = pkg.get("information_architecture")
        assert ia is not None, f"{doc_type}: information_architecture section missing"

        rendering = pkg.get("rendering")
        assert rendering is not None, f"{doc_type}: rendering section missing"

        detail_html = rendering.get("detail_html")
        assert detail_html is not None, f"{doc_type}: rendering.detail_html missing"

        # Build lookup: section id -> list of bind paths
        section_binds = {s["id"]: _extract_bind_paths(s) for s in ia["sections"]}

        for tab in detail_html.get("tabs", []):
            for section_id in tab.get("sections", []):
                assert section_id in section_binds, (
                    f"{doc_type}: Tab '{tab['id']}' references section '{section_id}' "
                    f"which is not declared in information_architecture"
                )
                binds = section_binds[section_id]
                assert len(binds) > 0, (
                    f"{doc_type}: Tab '{tab['id']}' section '{section_id}' "
                    f"has no binds — cannot render from raw content"
                )

    def test_no_hardcoded_doc_type_routing(self):
        """FullDocumentViewer does not hardcode doc type routing for tabbed rendering."""
        content = self.SPA_FULL.read_text()

        # After config-driven refactor, FullDocumentViewer should not check
        # specific doc type IDs to decide whether to render tabs.
        hardcoded_type_checks = [
            "isTechnicalArchitecture",
            "'technical_architecture'",
            '"technical_architecture"',
        ]

        found = [m for m in hardcoded_type_checks if m in content]
        assert not found, (
            f"FullDocumentViewer.jsx still contains hardcoded doc type routing: {found}. "
            f"Tabbed rendering should be driven by rendering_config presence, "
            f"not doc type checks."
        )


# --- Level 2 Block Rendering Contract Tests (WS-IA-003) ---

# Document types that have Level 2 IA (object binds with render_as)
LEVEL2_DOC_TYPES = TIER1_DOC_TYPES


def _get_schema_type_at_path(schema: dict, path: str) -> str | None:
    """Resolve the JSON schema type for a top-level property."""
    prop = schema.get("properties", {}).get(path)
    if not prop:
        return None
    return prop.get("type")


class TestBlockRenderingContract:
    """C6-C9: Validate Level 2 IA block rendering declarations."""

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c6_render_as_vocabulary(self, doc_type):
        """C6: All render_as values must be in the pinned vocabulary."""
        pkg = _load_package(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                render_as = bind.get("render_as")
                if render_as is not None:
                    assert render_as in VALID_RENDER_AS, (
                        f"{doc_type}: Section '{section['id']}' bind '{bind['path']}' "
                        f"has render_as='{render_as}' which is not in vocabulary: "
                        f"{sorted(VALID_RENDER_AS)}"
                    )

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c7_card_list_has_card_definition(self, doc_type):
        """C7: Every card-list bind has a card with title and fields, each with path + render_as."""
        pkg = _load_package(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                if bind.get("render_as") != "card-list":
                    continue
                card = bind.get("card")
                assert card is not None, (
                    f"{doc_type}: Section '{section['id']}' bind '{bind['path']}' "
                    f"is card-list but has no 'card' definition"
                )
                assert "title" in card, (
                    f"{doc_type}: card-list bind '{bind['path']}' card missing 'title'"
                )
                assert "fields" in card, (
                    f"{doc_type}: card-list bind '{bind['path']}' card missing 'fields'"
                )
                for field in card["fields"]:
                    assert "path" in field, (
                        f"{doc_type}: card-list '{bind['path']}' card field missing 'path'"
                    )
                    assert "render_as" in field, (
                        f"{doc_type}: card-list '{bind['path']}' card field "
                        f"'{field.get('path', '?')}' missing 'render_as'"
                    )

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c8_table_has_columns(self, doc_type):
        """C8: Every table bind has a columns array with field + label."""
        pkg = _load_package(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                if bind.get("render_as") != "table":
                    continue
                columns = bind.get("columns")
                assert columns is not None and len(columns) > 0, (
                    f"{doc_type}: Section '{section['id']}' bind '{bind['path']}' "
                    f"is table but has no 'columns' array"
                )
                for col in columns:
                    assert "field" in col, (
                        f"{doc_type}: table '{bind['path']}' column missing 'field'"
                    )
                    assert "label" in col, (
                        f"{doc_type}: table '{bind['path']}' column missing 'label'"
                    )

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c9_nested_object_has_fields(self, doc_type):
        """C9: Every nested-object bind has fields with path + render_as."""
        pkg = _load_package(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                if bind.get("render_as") != "nested-object":
                    continue
                fields = bind.get("fields")
                assert fields is not None and len(fields) > 0, (
                    f"{doc_type}: Section '{section['id']}' bind '{bind['path']}' "
                    f"is nested-object but has no 'fields'"
                )
                for field in fields:
                    assert "path" in field, (
                        f"{doc_type}: nested-object '{bind['path']}' field missing 'path'"
                    )
                    assert "render_as" in field, (
                        f"{doc_type}: nested-object '{bind['path']}' field "
                        f"'{field.get('path', '?')}' missing 'render_as'"
                    )


class TestNoGuessing:
    """C10-C13: Ensure complex schema types are never left to SPA guessing."""

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c10_complex_types_have_render_as(self, doc_type):
        """C10: If schema type at path is object/array, render_as MUST be present."""
        pkg = _load_package(doc_type)
        schema = _load_schema(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                schema_type = _get_schema_type_at_path(schema, bind["path"])
                if schema_type in ("object", "array"):
                    assert bind.get("render_as") is not None, (
                        f"{doc_type}: Bind '{bind['path']}' has schema type '{schema_type}' "
                        f"but no render_as — SPA will guess rendering"
                    )

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c11_paragraph_not_on_complex(self, doc_type):
        """C11: render_as='paragraph' on object/array is a failure."""
        pkg = _load_package(doc_type)
        schema = _load_schema(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                schema_type = _get_schema_type_at_path(schema, bind["path"])
                if schema_type in ("object", "array"):
                    assert bind.get("render_as") != "paragraph", (
                        f"{doc_type}: Bind '{bind['path']}' is schema type '{schema_type}' "
                        f"but render_as='paragraph' — this would lose structure"
                    )

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c12_card_sub_fields_have_render_as(self, doc_type):
        """C12: Every sub-field in card.fields has its own render_as."""
        pkg = _load_package(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                card = bind.get("card")
                if not card:
                    continue
                for field in card.get("fields", []):
                    assert "render_as" in field, (
                        f"{doc_type}: card-list '{bind['path']}' sub-field "
                        f"'{field.get('path', '?')}' missing render_as"
                    )

    @pytest.mark.parametrize("doc_type", LEVEL2_DOC_TYPES)
    def test_c13_full_level2_coverage(self, doc_type):
        """C13: 100% Level 2 coverage — every bind in every section is an object with render_as."""
        pkg = _load_package(doc_type)
        ia = pkg["information_architecture"]

        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                bind = _normalize_bind(raw_bind)
                assert isinstance(raw_bind, dict), (
                    f"{doc_type}: Section '{section['id']}' bind '{bind['path']}' "
                    f"is a string (Level 1) — expected Level 2 object bind"
                )
                assert "render_as" in bind, (
                    f"{doc_type}: Section '{section['id']}' bind '{bind['path']}' "
                    f"missing render_as — not Level 2"
                )


class TestTABlockModel:
    """TA-specific block model assertions."""

    def test_ta_has_six_tabs(self):
        """TA has 6 tabs: overview, components, workflows, data_models, interfaces, quality."""
        pkg = _load_package("technical_architecture")
        tabs = pkg["rendering"]["detail_html"]["tabs"]
        tab_ids = {t["id"] for t in tabs}
        expected = {"overview", "components", "workflows", "data_models", "interfaces", "quality"}
        assert tab_ids == expected, f"TA tabs mismatch. Got: {sorted(tab_ids)}, expected: {sorted(expected)}"

    def test_ta_workflows_card_list(self):
        """Workflows section uses card-list with steps sub-field."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        wf_section = next(s for s in ia["sections"] if s["id"] == "workflows")
        bind = _normalize_bind(wf_section["binds"][0])
        assert bind["render_as"] == "card-list", "workflows bind should be card-list"
        assert "card" in bind, "workflows bind should have card definition"
        field_paths = {f["path"] for f in bind["card"]["fields"]}
        assert "steps" in field_paths, "workflows card should include steps sub-field"

    def test_ta_components_card_list(self):
        """Components section uses card-list with appropriate sub-fields."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        comp_section = next(s for s in ia["sections"] if s["id"] == "components")
        bind = _normalize_bind(comp_section["binds"][0])
        assert bind["render_as"] == "card-list", "components bind should be card-list"
        assert "card" in bind, "components bind should have card definition"
        field_paths = {f["path"] for f in bind["card"]["fields"]}
        assert "purpose" in field_paths or "technology" in field_paths, (
            "components card should include purpose or technology sub-fields"
        )

    def test_ta_data_models_card_list(self):
        """Data models section uses card-list."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        dm_section = next(s for s in ia["sections"] if s["id"] == "data_models")
        bind = _normalize_bind(dm_section["binds"][0])
        assert bind["render_as"] == "card-list", "data_models bind should be card-list"

    def test_ta_api_interfaces_card_list(self):
        """API interfaces section uses card-list."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        api_section = next(s for s in ia["sections"] if s["id"] == "api_interfaces")
        bind = _normalize_bind(api_section["binds"][0])
        assert bind["render_as"] == "card-list", "api_interfaces bind should be card-list"

    def test_ta_risks_table(self):
        """Risks section uses table rendering."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        risk_section = next(s for s in ia["sections"] if s["id"] == "overview.risks")
        bind = _normalize_bind(risk_section["binds"][0])
        assert bind["render_as"] == "table", "risks bind should be table"
        assert "columns" in bind, "risks table bind should have columns"

    def test_ta_open_questions_table(self):
        """Open questions section uses table rendering."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        oq_section = next(s for s in ia["sections"] if s["id"] == "overview.open_questions")
        bind = _normalize_bind(oq_section["binds"][0])
        assert bind["render_as"] == "table", "open_questions bind should be table"


class TestSPABlockRenderer:
    """Mode B grep-based tests for IABlockRenderer SPA component."""

    SPA_BLOCK_RENDERER = Path("spa/src/components/blocks/IABlockRenderer.jsx")
    SPA_VIEWER = Path("spa/src/components/viewers/ConfigDrivenDocViewer.jsx")

    def test_ia_block_renderer_exists(self):
        """IABlockRenderer.jsx exists."""
        assert self.SPA_BLOCK_RENDERER.exists(), (
            "spa/src/components/blocks/IABlockRenderer.jsx does not exist"
        )

    def test_ia_block_renderer_has_all_render_types(self):
        """IABlockRenderer contains all 7 render_as type strings."""
        content = self.SPA_BLOCK_RENDERER.read_text()
        for render_type in VALID_RENDER_AS:
            assert render_type in content, (
                f"IABlockRenderer.jsx missing render_as type: '{render_type}'"
            )

    def test_config_driven_viewer_uses_ia_block_renderer(self):
        """ConfigDrivenDocViewer imports and uses IABlockRenderer."""
        content = self.SPA_VIEWER.read_text()
        assert "IABlockRenderer" in content, (
            "ConfigDrivenDocViewer.jsx does not reference IABlockRenderer"
        )

    def test_config_driven_viewer_reads_ia_config(self):
        """ConfigDrivenDocViewer reads information_architecture from render model."""
        content = self.SPA_VIEWER.read_text()
        assert "information_architecture" in content, (
            "ConfigDrivenDocViewer.jsx does not read information_architecture"
        )

    def test_no_studio_panel_imports(self):
        """ConfigDrivenDocViewer does not import WorkflowStudioPanel or ComponentsStudioPanel."""
        content = self.SPA_VIEWER.read_text()
        assert "WorkflowStudioPanel" not in content, (
            "ConfigDrivenDocViewer.jsx still imports WorkflowStudioPanel"
        )
        assert "ComponentsStudioPanel" not in content, (
            "ConfigDrivenDocViewer.jsx still imports ComponentsStudioPanel"
        )


class TestCoverageReport:
    """Coverage report: asserts 100% Level 2 coverage for TA."""

    def test_ta_level2_ia_version(self):
        """TA information_architecture version is 2."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]
        assert ia["version"] == 2, (
            f"TA IA version is {ia['version']}, expected 2 (Level 2)"
        )

    def test_ta_all_binds_are_level2(self):
        """Every bind in TA is a Level 2 object (not a string)."""
        pkg = _load_package("technical_architecture")
        ia = pkg["information_architecture"]

        total = 0
        level2 = 0
        for section in ia["sections"]:
            for raw_bind in section.get("binds", []):
                total += 1
                if isinstance(raw_bind, dict) and "render_as" in raw_bind:
                    level2 += 1

        assert total > 0, "TA has no binds"
        assert level2 == total, (
            f"TA Level 2 coverage: {level2}/{total} "
            f"({100 * level2 // total}%) — expected 100%"
        )

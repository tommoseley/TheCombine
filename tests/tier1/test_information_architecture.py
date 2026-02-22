"""Golden contract tests for Information Architecture (ADR-054).

Tests validate alignment between:
- Schema Contract (output.schema.json)
- Information Architecture Contract (package.yaml information_architecture)
- Rendering targets (package.yaml rendering.detail_html, rendering.pdf)

WS-IA-001: TA golden contract tests (C1-C8)
WS-IA-002: Extended to PD, IPP, IPF (parametrized C1-C5) + SPA generic rendering (C6-C7)
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
            for bind in section.get("binds", []):
                assert bind in schema_fields, (
                    f"{doc_type}: Section '{section['id']}' binds '{bind}' which is not a "
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
            all_binds.update(section.get("binds", []))

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

    SPA_VIEWER = Path("spa/src/components/viewers/TechnicalArchitectureViewer.jsx")
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
            f"TechnicalArchitectureViewer.jsx still contains hardcoded "
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

"""WS-ONTOLOGY-007: Production Floor UI — WP/WS hierarchy guard tests.

Since no React test harness exists (Mode B debt), these tests use source
code inspection to verify the Production Floor renders WP/WS nodes and
contains no Epic UI elements.

Tier 1 Verification Criteria:
  C1 - WP nodes rendered (DocumentNode shows WORK PACKAGE label for L2)
  C2 - WP progress displayed (ws_done/ws_total in component)
  C3 - WP Mode B count displayed
  C4 - WP dependency count displayed
  C5 - WS children rendered on expand (WSChildList component exists)
  C6 - No Epic UI elements in Production Floor
  C7 - Regression guard (no Epic type references in spa/src/)
"""

import pathlib
import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SPA_SRC = PROJECT_ROOT / "spa" / "src"
COMPONENTS = SPA_SRC / "components"
BLOCKS = COMPONENTS / "blocks"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ===================================================================
# C1 — WP nodes rendered
# ===================================================================

class TestC1WPNodesRendered:
    """DocumentNode renders 'WORK PACKAGE' label for L2 nodes."""

    def test_document_node_has_work_package_label(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "WORK PACKAGE" in src, "DocumentNode does not render WORK PACKAGE label"

    def test_document_node_has_wp_header_class(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "subway-node-header-wp" in src, "DocumentNode missing WP header CSS class"


# ===================================================================
# C2 — WP progress displayed
# ===================================================================

class TestC2WPProgressDisplayed:
    """WP node shows ws_done/ws_total progress indicator."""

    def test_document_node_shows_ws_done(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "ws_done" in src, "DocumentNode does not display ws_done"

    def test_document_node_shows_ws_total(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "ws_total" in src, "DocumentNode does not display ws_total"


# ===================================================================
# C3 — WP Mode B count displayed
# ===================================================================

class TestC3WPModeBCount:
    """WP node shows Mode B count."""

    def test_document_node_shows_mode_b(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "mode_b" in src.lower(), "DocumentNode does not display Mode B count"


# ===================================================================
# C4 — WP dependency count displayed
# ===================================================================

class TestC4WPDependencyCount:
    """WP node shows dependency count."""

    def test_document_node_shows_dependency_count(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "dependencies" in src.lower() or "dep_count" in src, \
            "DocumentNode does not display dependency count"


# ===================================================================
# C5 — WS children rendered on expand
# ===================================================================

class TestC5WSChildrenRendered:
    """WSChildList component exists and renders WS details."""

    def test_ws_child_list_component_exists(self):
        assert (COMPONENTS / "WSChildList.jsx").exists(), \
            "WSChildList.jsx component does not exist"

    def test_ws_child_list_shows_status(self):
        src = _read(COMPONENTS / "WSChildList.jsx")
        # Must render WS status badges
        for status in ["DRAFT", "READY", "IN_PROGRESS", "ACCEPTED"]:
            if status in src:
                return
        pytest.fail("WSChildList does not render WS status values")

    def test_ws_child_list_shows_verification_mode(self):
        src = _read(COMPONENTS / "WSChildList.jsx")
        assert "mode" in src.lower() and ("A" in src or "B" in src), \
            "WSChildList does not show verification mode indicator"

    def test_document_node_imports_ws_child_list(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "WSChildList" in src, "DocumentNode does not import WSChildList"


# ===================================================================
# C6 — No Epic UI elements
# ===================================================================

class TestC6NoEpicUIElements:
    """No Production Floor component renders Epic nodes or labels."""

    def test_document_node_no_epic_label(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        # Should NOT have "EPIC" as a level label
        assert "'EPIC'" not in src and '"EPIC"' not in src, \
            "DocumentNode still renders EPIC label"

    def test_document_node_no_epic_header_class(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "subway-node-header-epic" not in src, \
            "DocumentNode still uses epic header CSS class"

    def test_no_feature_grid_component(self):
        assert not (COMPONENTS / "FeatureGrid.jsx").exists(), \
            "FeatureGrid.jsx still exists"

    def test_document_node_no_feature_grid_import(self):
        src = _read(COMPONENTS / "DocumentNode.jsx")
        assert "FeatureGrid" not in src, \
            "DocumentNode still imports FeatureGrid"

    def test_no_epic_summary_block_in_registry(self):
        src = _read(BLOCKS / "index.jsx")
        assert "EpicSummaryBlock" not in src, \
            "Block registry still references EpicSummaryBlock"

    def test_layout_no_epic_function_names(self):
        src = _read(SPA_SRC / "utils" / "layout.js")
        assert "addEpicsToLayout" not in src, \
            "Layout still has addEpicsToLayout function"
        assert "epicChildren" not in src, \
            "Layout still has epicChildren variable"
        assert "epicBacklogId" not in src, \
            "Layout still has epicBacklogId variable"


# ===================================================================
# C7 — Regression guard
# ===================================================================

class TestC7RegressionGuard:
    """No React component references 'Epic' as a doc/node type."""

    def test_no_epic_type_references_in_spa_components(self):
        hits = []
        for jsx in COMPONENTS.rglob("*.jsx"):
            if "__pycache__" in str(jsx):
                continue
            try:
                lines = jsx.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                # Look for Epic as a node/doc type label (not substring of other words)
                if any(p in stripped for p in [
                    "'EPIC'", '"EPIC"',
                    "EpicNode", "epicNode",
                    "FeatureGrid",
                    "epicName",
                    "header-epic",
                ]):
                    hits.append((jsx.relative_to(PROJECT_ROOT), i, stripped))
        if hits:
            report = "\n".join(f"  {f}:{ln}: {text}" for f, ln, text in hits)
            pytest.fail(f"Epic UI references found:\n{report}")

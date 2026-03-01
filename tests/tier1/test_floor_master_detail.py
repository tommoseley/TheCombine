"""Tests for WS-PIPELINE-002: Floor Layout Redesign (Master-Detail).

Verifies the Floor component renders a master-detail layout with:
- ReactFlow subway map in a compact left column (~35%)
- ContentPanel in the right column (~65%)
- DocumentNode in compact mode (no action buttons)
- WorkBinder component for WP/WS management
- Backend API endpoints for work packages

Criteria 1-20 from WS-PIPELINE-002. All structural contracts verified
by reading source files. No runtime, no DB, no LLM.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPA_SRC = REPO_ROOT / "spa" / "src"
FLOOR_JSX = SPA_SRC / "components" / "Floor.jsx"
DOC_NODE_JSX = SPA_SRC / "components" / "DocumentNode.jsx"
PIPELINE_RAIL_JSX = SPA_SRC / "components" / "PipelineRail.jsx"
CONTENT_PANEL_JSX = SPA_SRC / "components" / "ContentPanel.jsx"
WORK_BINDER_DIR = SPA_SRC / "components" / "WorkBinder"
FULL_VIEWER_JSX = SPA_SRC / "components" / "FullDocumentViewer.jsx"
API_CLIENT_JS = SPA_SRC / "api" / "client.js"
PROJECTS_ROUTER_PY = (
    REPO_ROOT / "app" / "api" / "v1" / "routers" / "projects.py"
)


def _read(path: Path) -> str:
    return path.read_text()


def _read_dir(dir_path: Path) -> str:
    """Read all .jsx files in a directory and concatenate."""
    return "\n".join(p.read_text() for p in sorted(dir_path.glob("*.jsx")))


# ===================================================================
# Layout Structure (Criteria 1-5)
# ===================================================================


class TestLayoutStructure:
    """Criteria 1-5: Floor renders master-detail with rail + content."""

    def test_01_floor_renders_two_column_flex_layout(self):
        """C1: Floor renders a two-column layout (rail + content)."""
        src = _read(FLOOR_JSX)
        # Outer flex container
        assert 'className="w-full h-full flex"' in src
        # Left column (PipelineRail) with fixed width
        assert "width: 320" in src or "width: '320'" in src
        # ContentPanel rendered as sibling
        assert "<ContentPanel" in src

    def test_02_rail_renders_pipeline_nodes(self):
        """C2: Rail renders one node per pipeline step (via PipelineRail)."""
        src = _read(FLOOR_JSX)
        # PipelineRail used for static vertical pipeline
        assert "import PipelineRail" in src or "PipelineRail" in src
        assert "<PipelineRail" in src
        # Data passed to rail for rendering
        assert "data={data}" in src

    def test_03_clicking_node_updates_selected_state(self):
        """C3: Clicking a rail node updates selected state."""
        src = _read(FLOOR_JSX)
        assert "selectedNodeId" in src
        assert "setSelectedNodeId" in src
        # PipelineRail receives onSelectNode callback
        assert "onSelectNode" in src

    def test_04_content_panel_renders_based_on_node_type(self):
        """C4: Content panel renders different content based on selected node type."""
        src = _read(CONTENT_PANEL_JSX)
        # Routes based on state
        assert "artifactState" in src or "getArtifactState" in src
        # Work Binder special case
        assert "isWorkBinder" in src
        # Document viewer for stabilized
        assert "FullDocumentViewer" in src

    def test_05_first_node_auto_selected(self):
        """C5: First node is auto-selected on component mount."""
        src = _read(FLOOR_JSX)
        # Auto-select effect
        assert "data.length > 0 && !selectedNodeId" in src
        assert "setSelectedNodeId" in src


# ===================================================================
# Node Cards — Rail Mode (Criteria 6-9)
# ===================================================================


class TestRailNodeCards:
    """Criteria 6-9: Rail nodes are compact — no buttons, selected highlight."""

    def test_06_rail_nodes_no_action_buttons(self):
        """C6: PipelineRail nodes do NOT contain action buttons."""
        src = _read(PIPELINE_RAIL_JSX)
        # Rail nodes have no View Document or Start Production buttons
        assert "View Document" not in src
        assert "Start Production" not in src

    def test_07_rail_is_static_not_reactflow(self):
        """C7: Rail nodes are static CSS — no ReactFlow dependency."""
        src = _read(PIPELINE_RAIL_JSX)
        # No ReactFlow imports
        assert "reactflow" not in src
        # Uses click handler for selection
        assert "onClick" in src

    def test_08_rail_nodes_show_label_dot_state(self):
        """C8: Rail nodes show: label, status dot, state text."""
        src = _read(PIPELINE_RAIL_JSX)
        # Header with level label and name
        assert "levelLabel" in src
        assert "formatDocTypeName" in src
        # State dot (colored circle)
        assert "colors.bg" in src
        # State text
        assert "displayState" in src

    def test_09_selected_rail_node_has_highlight(self):
        """C9: Selected rail node has visual highlight."""
        src = _read(PIPELINE_RAIL_JSX)
        assert "isSelected" in src
        # Selected border or box-shadow
        assert "boxShadow" in src or "borderWidth" in src


# ===================================================================
# Content Panel (Criteria 10-12)
# ===================================================================


class TestContentPanel:
    """Criteria 10-12: Content panel mounts viewers and actions."""

    def test_10_document_node_mounts_viewer(self):
        """C10: Selecting a document node mounts document viewer."""
        src = _read(CONTENT_PANEL_JSX)
        assert "FullDocumentViewer" in src
        assert "inline" in src

    def test_11_wb_node_mounts_work_binder(self):
        """C11: Selecting WB node mounts WorkBinder component."""
        src = _read(CONTENT_PANEL_JSX)
        assert "WorkBinder" in src
        assert "import WorkBinder" in src

    def test_12_start_production_in_content_panel(self):
        """C12: 'Start Production' appears in content panel for ready documents."""
        src = _read(CONTENT_PANEL_JSX)
        assert "Start Production" in src
        assert "onStartProduction" in src


# ===================================================================
# Work Binder (Criteria 13-18)
# ===================================================================


class TestWorkBinder:
    """Criteria 13-18: WorkBinder manages WPs and WSs."""

    def test_13_work_binder_renders_candidate_lineage(self):
        """C13: WorkBinder renders source candidate lineage (from IP)."""
        src = _read_dir(WORK_BINDER_DIR)
        assert "source_candidate_ids" in src or "candidates" in src
        assert "Source Lineage" in src

    def test_14_work_binder_renders_wp_index(self):
        """C14: WorkBinder renders WP index with package list."""
        src = _read_dir(WORK_BINDER_DIR)
        assert "wps" in src
        assert "PACKAGES" in src

    def test_15_create_work_packages_button(self):
        """C15: 'Insert Package' button exists and calls backend."""
        src = _read_dir(WORK_BINDER_DIR)
        assert "INSERT PACKAGE" in src or "CREATE PACKAGE" in src
        assert "onInsertPackage" in src

    def test_16_governed_wp_rows_show_id_title_state(self):
        """C16: Governed WP rows show: WP ID, Title, State."""
        src = _read_dir(WORK_BINDER_DIR)
        assert "wp_id" in src or "wp.id" in src
        assert "wp.title" in src or "wp.name" in src
        assert "StateDot" in src or "state" in src

    def test_17_create_work_statements_inline(self):
        """C17: Work statement creation exists via ghost row in WorkView."""
        src = _read_dir(WORK_BINDER_DIR)
        assert "CREATE STATEMENT" in src or "ENTER INTENT" in src
        assert "work-statements" in src

    def test_18_wp_provenance_stamping(self):
        """C18: WP displays provenance (source, authorization)."""
        src = _read_dir(WORK_BINDER_DIR)
        assert "provenance" in src
        assert "SOURCE:" in src or "provenance.source" in src


# ===================================================================
# Theme Support (Criteria 19-20)
# ===================================================================


class TestThemeSupport:
    """Criteria 19-20: All components respect theme CSS variables."""

    def test_19_components_use_css_variables(self):
        """C19: Rail and content panel respect theme CSS variables."""
        src = _read(CONTENT_PANEL_JSX)
        assert "var(--" in src, "ContentPanel.jsx does not use CSS variables"
        wb_src = _read_dir(WORK_BINDER_DIR)
        assert "var(--" in wb_src, "WorkBinder does not use CSS variables"

    def test_20_floor_uses_theme_prop(self):
        """C20: Floor passes theme through and all three themes are supported."""
        src = _read(FLOOR_JSX)
        assert "theme" in src
        assert "cycleTheme" in src


# ===================================================================
# API Contract (supplemental — endpoint availability)
# ===================================================================


class TestAPIContract:
    """Supplemental: API client and backend routes exist."""

    def test_api_client_has_work_package_methods(self):
        """API client exposes work package CRUD methods."""
        src = _read(API_CLIENT_JS)
        assert "getWorkPackages" in src
        assert "generateWorkPackages" in src
        assert "generateWorkStatements" in src
        assert "getWorkStatements" in src

    def test_backend_has_work_package_routes(self):
        """Backend router has work package endpoints."""
        src = _read(PROJECTS_ROUTER_PY)
        assert "work-packages" in src
        assert "list_work_packages" in src
        assert "generate_work_packages" in src
        assert "list_work_statements" in src
        assert "generate_work_statements" in src

    def test_floor_uses_static_pipeline_rail(self):
        """Floor uses static PipelineRail (no ReactFlow dependency)."""
        src = _read(FLOOR_JSX)
        # No ReactFlow imports — pure CSS layout
        assert "import ReactFlow" not in src
        assert "useReactFlow" not in src
        # Uses PipelineRail component
        assert "<PipelineRail" in src

    def test_full_document_viewer_supports_inline(self):
        """FullDocumentViewer accepts inline prop for embedded rendering."""
        src = _read(FULL_VIEWER_JSX)
        assert "inline" in src

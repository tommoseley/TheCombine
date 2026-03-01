"""Tier-1 tests for admin_workbench_pure.py.

Pure data transformation tests -- no DB, no I/O, no filesystem.
"""


from app.api.services.admin_workbench_pure import (
    build_fragment_dict,
    build_orchestration_summary,
    build_workflow_summary,
)


# =========================================================================
# build_fragment_dict
# =========================================================================


class TestBuildFragmentDict:
    """Tests for build_fragment_dict."""

    def test_basic_fragment(self):
        result = build_fragment_dict(
            fragment_id="role:architect",
            kind="role",
            version="1.0.0",
            name="Technical Architect",
            intent="Design systems",
            tags=["core"],
            content="You are a technical architect.",
            source_doc_type=None,
        )
        assert result["fragment_id"] == "role:architect"
        assert result["kind"] == "role"
        assert result["version"] == "1.0.0"
        assert result["name"] == "Technical Architect"
        assert result["intent"] == "Design systems"
        assert result["tags"] == ["core"]
        assert result["content_preview"] == "You are a technical architect."
        assert result["source_doc_type"] is None

    def test_long_content_truncated(self):
        long_content = "A" * 300
        result = build_fragment_dict(
            fragment_id="task:test",
            kind="task",
            version="1.0.0",
            name="Test",
            intent=None,
            tags=[],
            content=long_content,
            source_doc_type="charter",
        )
        assert result["content_preview"] == "A" * 200 + "..."
        assert len(result["content_preview"]) == 203

    def test_content_at_exactly_preview_length(self):
        content = "B" * 200
        result = build_fragment_dict(
            fragment_id="task:test",
            kind="task",
            version="1.0.0",
            name="Test",
            intent=None,
            tags=[],
            content=content,
            source_doc_type=None,
        )
        assert result["content_preview"] == content
        assert "..." not in result["content_preview"]

    def test_custom_preview_length(self):
        content = "C" * 100
        result = build_fragment_dict(
            fragment_id="task:test",
            kind="task",
            version="1.0.0",
            name="Test",
            intent=None,
            tags=[],
            content=content,
            source_doc_type=None,
            preview_length=50,
        )
        assert result["content_preview"] == "C" * 50 + "..."

    def test_source_doc_type_preserved(self):
        result = build_fragment_dict(
            fragment_id="qa:charter",
            kind="qa",
            version="1.0.0",
            name="Charter QA",
            intent=None,
            tags=[],
            content="Check quality",
            source_doc_type="charter",
        )
        assert result["source_doc_type"] == "charter"

    def test_empty_content(self):
        result = build_fragment_dict(
            fragment_id="task:test",
            kind="task",
            version="1.0.0",
            name="Test",
            intent=None,
            tags=[],
            content="",
            source_doc_type=None,
        )
        assert result["content_preview"] == ""


# =========================================================================
# build_workflow_summary
# =========================================================================


class TestBuildWorkflowSummary:
    """Tests for build_workflow_summary."""

    def test_graph_workflow_returns_summary(self):
        raw = {
            "name": "Concierge Intake",
            "description": "Intake workflow",
            "nodes": [{"id": "start"}, {"id": "pgc"}, {"id": "end"}],
            "edges": [{"from": "start", "to": "pgc"}, {"from": "pgc", "to": "end"}],
        }
        result = build_workflow_summary("concierge_intake", raw, "1.3.0")
        assert result is not None
        assert result["workflow_id"] == "concierge_intake"
        assert result["name"] == "Concierge Intake"
        assert result["active_version"] == "1.3.0"
        assert result["description"] == "Intake workflow"
        assert result["node_count"] == 3
        assert result["edge_count"] == 2

    def test_non_graph_workflow_returns_none(self):
        raw = {"steps": [{"id": "step1"}]}
        result = build_workflow_summary("some_workflow", raw, "1.0.0")
        assert result is None

    def test_missing_nodes_returns_none(self):
        raw = {"edges": [{"from": "a", "to": "b"}]}
        result = build_workflow_summary("test", raw, "1.0.0")
        assert result is None

    def test_missing_edges_returns_none(self):
        raw = {"nodes": [{"id": "a"}]}
        result = build_workflow_summary("test", raw, "1.0.0")
        assert result is None

    def test_default_name_is_workflow_id(self):
        raw = {"nodes": [], "edges": []}
        result = build_workflow_summary("my_workflow", raw, "1.0.0")
        assert result["name"] == "my_workflow"

    def test_no_description(self):
        raw = {"nodes": [], "edges": []}
        result = build_workflow_summary("test", raw, "1.0.0")
        assert result["description"] is None

    def test_empty_nodes_and_edges(self):
        raw = {"nodes": [], "edges": []}
        result = build_workflow_summary("test", raw, "1.0.0")
        assert result["node_count"] == 0
        assert result["edge_count"] == 0


# =========================================================================
# build_orchestration_summary
# =========================================================================


class TestBuildOrchestrationSummary:
    """Tests for build_orchestration_summary."""

    def test_step_based_workflow(self):
        raw = {
            "name": "Software Product Development",
            "description": "Master POW",
            "steps": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}],
            "schema_version": "workflow.v2",
            "pow_class": "canonical",
            "derived_from": {"workflow_id": "base", "version": "1.0.0"},
            "source_version": "0.9.0",
            "tags": ["prod"],
        }
        result = build_orchestration_summary("spd", raw, "1.0.0")
        assert result is not None
        assert result["workflow_id"] == "spd"
        assert result["name"] == "Software Product Development"
        assert result["step_count"] == 3
        assert result["schema_version"] == "workflow.v2"
        assert result["pow_class"] == "canonical"
        assert result["derived_from_label"] == "base v1.0.0"
        assert result["source_version"] == "0.9.0"
        assert result["tags"] == ["prod"]

    def test_graph_workflow_returns_none(self):
        raw = {"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "b"}]}
        result = build_orchestration_summary("test", raw, "1.0.0")
        assert result is None

    def test_default_values(self):
        raw = {"steps": []}
        result = build_orchestration_summary("my_workflow", raw, "2.0.0")
        assert result["name"] == "My Workflow"
        assert result["schema_version"] == "workflow.v1"
        assert result["pow_class"] == "reference"
        assert result["derived_from"] is None
        assert result["derived_from_label"] is None
        assert result["source_version"] is None
        assert result["tags"] == []

    def test_derived_from_non_dict_no_label(self):
        raw = {"steps": [], "derived_from": "some_string"}
        result = build_orchestration_summary("test", raw, "1.0.0")
        assert result["derived_from"] == "some_string"
        assert result["derived_from_label"] is None

    def test_derived_from_dict_partial_keys(self):
        raw = {"steps": [], "derived_from": {"workflow_id": "base"}}
        result = build_orchestration_summary("test", raw, "1.0.0")
        assert result["derived_from_label"] == "base v"

    def test_no_steps_key(self):
        raw = {}
        result = build_orchestration_summary("test", raw, "1.0.0")
        assert result["step_count"] == 0

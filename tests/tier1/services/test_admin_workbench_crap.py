"""Tier-1 CRAP score remediation tests for AdminWorkbenchService methods.

Covers branching logic for three methods:
1. list_prompt_fragments (CC=13):
   - kind filter: None, valid enum, invalid string
   - Role fragments: skipped when kind_filter != ROLE, loaded, load failure
   - Doc type fragments: each artifact kind, content present/absent, load failure
2. list_workflows (CC=13):
   - workflows dir missing
   - skip non-dirs and underscore-prefixed
   - active version from releases, fallback to scanning releases dir
   - no version -> skip
   - successful load: build_workflow_summary returns dict / returns None
   - load failure -> error summary
3. list_orchestration_workflows (CC=13):
   - Same structure as list_workflows but uses build_orchestration_summary
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.api.services.admin_workbench_service import AdminWorkbenchService
from app.config.package_loader import PackageLoaderError
from app.config.package_model import (
    ActiveReleases,
    DocumentTypePackage,
    PackageArtifacts,
    PromptFragment,
    PromptFragmentKind,
    RolePrompt,
)


# =========================================================================
# Helpers
# =========================================================================


def _make_mock_loader(
    roles=None,
    doc_types=None,
    active_releases=None,
    config_path=None,
):
    """Build a mock PackageLoader."""
    loader = MagicMock()
    loader.list_roles.return_value = roles or []
    loader.list_document_types.return_value = doc_types or []
    loader.config_path = config_path or Path("/fake/combine-config")

    ar = active_releases or ActiveReleases()
    loader.get_active_releases.return_value = ar

    return loader


def _make_role_prompt(role_id="architect", version="1.0.0", content="You are an architect."):
    return RolePrompt(
        role_id=role_id,
        version=version,
        content=content,
        name=role_id.replace("_", " ").title(),
        intent="Design systems",
        tags=["core"],
    )


def _make_doc_type_package(
    doc_type_id="project_discovery",
    version="1.0.0",
    has_task=True,
    has_qa=False,
    has_pgc=False,
    has_reflection=False,
):
    """Build a mock DocumentTypePackage."""
    pkg = MagicMock(spec=DocumentTypePackage)
    pkg.doc_type_id = doc_type_id
    pkg.version = version
    pkg.display_name = doc_type_id.replace("_", " ").title()

    pkg.get_task_prompt.return_value = "Task prompt content" if has_task else None
    pkg.get_qa_prompt.return_value = "QA prompt content" if has_qa else None
    pkg.get_pgc_context.return_value = "PGC context content" if has_pgc else None
    pkg.get_reflection_prompt.return_value = "Reflection content" if has_reflection else None

    return pkg


# =========================================================================
# list_prompt_fragments
# =========================================================================


class TestListPromptFragmentsKindFilter:
    """Tests for kind filter logic."""

    def test_no_kind_filter_returns_all(self):
        """When kind is None, all fragment types are collected."""
        loader = _make_mock_loader(
            roles=["architect"],
            doc_types=["pd"],
        )
        loader.get_role.return_value = _make_role_prompt()

        pkg = _make_doc_type_package("pd", has_task=True)
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind=None)

        # Should have role + task (from doc type)
        assert len(result) >= 2
        kinds = {f["kind"] for f in result}
        assert "role" in kinds
        assert "task" in kinds

    def test_valid_kind_filter_role(self):
        """When kind='role', only role fragments returned."""
        loader = _make_mock_loader(
            roles=["architect"],
            doc_types=["pd"],
        )
        loader.get_role.return_value = _make_role_prompt()

        pkg = _make_doc_type_package("pd", has_task=True)
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind="role")

        assert len(result) == 1
        assert all(f["kind"] == "role" for f in result)

    def test_valid_kind_filter_task(self):
        """When kind='task', only task fragments returned."""
        loader = _make_mock_loader(
            roles=["architect"],
            doc_types=["pd"],
        )
        loader.get_role.return_value = _make_role_prompt()

        pkg = _make_doc_type_package("pd", has_task=True)
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind="task")

        assert len(result) == 1
        assert all(f["kind"] == "task" for f in result)

    def test_invalid_kind_filter_ignored(self):
        """When kind is an invalid value, filter is ignored (returns all)."""
        loader = _make_mock_loader(
            roles=["architect"],
            doc_types=[],
        )
        loader.get_role.return_value = _make_role_prompt()

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind="bogus_kind")

        # kind_filter remains None, so all types collected
        # Only roles exist, so should have 1 role fragment
        assert len(result) == 1
        assert result[0]["kind"] == "role"


class TestListPromptFragmentsRoles:
    """Tests for role fragment loading."""

    def test_role_load_failure_skipped(self):
        """When a role fails to load, it's skipped with a warning."""
        loader = _make_mock_loader(
            roles=["bad_role"],
            doc_types=[],
        )
        loader.get_role.side_effect = PackageLoaderError("role not found")

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind="role")

        assert result == []


class TestListPromptFragmentsDocTypes:
    """Tests for document type fragment loading."""

    def test_doc_type_with_multiple_artifacts(self):
        """Doc type with task + QA + PGC yields multiple fragments."""
        loader = _make_mock_loader(
            roles=[],
            doc_types=["pd"],
        )
        pkg = _make_doc_type_package(
            "pd", has_task=True, has_qa=True, has_pgc=True, has_reflection=True,
        )
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind=None)

        kinds = {f["kind"] for f in result}
        assert "task" in kinds
        assert "qa" in kinds
        assert "pgc" in kinds
        assert "reflection" in kinds
        assert len(result) == 4

    def test_doc_type_with_no_artifacts(self):
        """Doc type with no prompts yields no fragments."""
        loader = _make_mock_loader(
            roles=[],
            doc_types=["empty"],
        )
        pkg = _make_doc_type_package(
            "empty", has_task=False, has_qa=False, has_pgc=False, has_reflection=False,
        )
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind=None)

        assert result == []

    def test_doc_type_load_failure_skipped(self):
        """When doc type fails to load, it's skipped."""
        loader = _make_mock_loader(
            roles=[],
            doc_types=["broken"],
        )
        loader.get_document_type.side_effect = PackageLoaderError("not found")

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind=None)

        assert result == []

    def test_kind_filter_qa_skips_task(self):
        """When kind='qa', task fragments are not collected."""
        loader = _make_mock_loader(
            roles=[],
            doc_types=["pd"],
        )
        pkg = _make_doc_type_package("pd", has_task=True, has_qa=True)
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind="qa")

        assert len(result) == 1
        assert result[0]["kind"] == "qa"

    def test_source_doc_type_populated(self):
        """Fragment from doc type has source_doc_type set."""
        loader = _make_mock_loader(
            roles=[],
            doc_types=["pd"],
        )
        pkg = _make_doc_type_package("pd", has_task=True)
        loader.get_document_type.return_value = pkg

        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_prompt_fragments(kind="task")

        assert result[0]["source_doc_type"] == "pd"


# =========================================================================
# list_workflows
# =========================================================================


class TestListWorkflowsDirMissing:
    """Tests for missing workflows directory."""

    def test_returns_empty_when_dir_missing(self, tmp_path):
        """When workflows/ doesn't exist, returns []."""
        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert result == []


class TestListWorkflowsDirIteration:
    """Tests for directory filtering."""

    def test_skips_non_dirs_and_underscore(self, tmp_path):
        """Files and underscore-prefixed dirs are skipped."""
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        (wf_dir / "some_file.json").write_text("{}")
        (wf_dir / "_hidden").mkdir()

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert result == []


class TestListWorkflowsVersionResolution:
    """Tests for active version resolution."""

    def test_active_version_from_releases(self, tmp_path):
        """When active_releases has the version, uses it directly."""
        wf_dir = tmp_path / "workflows" / "wf_a"
        wf_dir.mkdir(parents=True)
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Workflow A",
            "description": "Test",
            "nodes": [{"id": "n1"}],
            "edges": [{"src": "n1", "dst": "n2"}],
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"wf_a": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert len(result) == 1
        assert result[0]["workflow_id"] == "wf_a"
        assert result[0]["active_version"] == "1.0.0"

    def test_fallback_to_scanning_releases(self, tmp_path):
        """When no active version, picks latest from releases/ scan."""
        wf_dir = tmp_path / "workflows" / "wf_b"
        wf_dir.mkdir(parents=True)
        for v in ["1.0.0", "2.0.0"]:
            defn_path = wf_dir / "releases" / v / "definition.json"
            defn_path.parent.mkdir(parents=True)
            defn_path.write_text(json.dumps({
                "name": "Workflow B",
                "nodes": [{"id": "n1"}],
                "edges": [{"src": "n1", "dst": "n2"}],
            }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert len(result) == 1
        assert result[0]["active_version"] == "2.0.0"

    def test_no_version_found_skips(self, tmp_path):
        """When no active version and no releases dir, workflow is skipped."""
        wf_dir = tmp_path / "workflows" / "wf_c"
        wf_dir.mkdir(parents=True)

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert result == []

    def test_empty_releases_dir_skips(self, tmp_path):
        """When releases/ exists but empty, workflow is skipped."""
        wf_dir = tmp_path / "workflows" / "wf_d"
        (wf_dir / "releases").mkdir(parents=True)

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert result == []


class TestListWorkflowsLoadSuccess:
    """Tests for successful workflow loading."""

    def test_graph_workflow_returns_summary(self, tmp_path):
        """Graph-based workflow (nodes+edges) returns summary."""
        wf_dir = tmp_path / "workflows" / "wf_graph"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Graph Workflow",
            "description": "A graph",
            "nodes": [{"id": "n1"}, {"id": "n2"}],
            "edges": [{"src": "n1", "dst": "n2"}],
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"wf_graph": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert len(result) == 1
        assert result[0]["name"] == "Graph Workflow"
        assert result[0]["node_count"] == 2
        assert result[0]["edge_count"] == 1

    def test_non_graph_workflow_returns_none(self, tmp_path):
        """Step-based workflow (no nodes/edges) returns None from build_workflow_summary."""
        wf_dir = tmp_path / "workflows" / "wf_step"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Step Workflow",
            "steps": [{"id": "s1"}],
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"wf_step": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        # build_workflow_summary returns None for non-graph -> not appended
        assert result == []


class TestListWorkflowsLoadFailure:
    """Tests for load failure paths."""

    def test_json_decode_error_produces_error_summary(self, tmp_path):
        """Malformed JSON produces an error summary."""
        wf_dir = tmp_path / "workflows" / "wf_bad"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text("NOT JSON")

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"wf_bad": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert len(result) == 1
        assert result[0]["workflow_id"] == "wf_bad"
        assert "error" in result[0]
        assert result[0]["node_count"] == 0

    def test_file_not_found_produces_error_summary(self, tmp_path):
        """Missing definition.json produces an error summary."""
        wf_dir = tmp_path / "workflows" / "wf_missing"
        (wf_dir / "releases" / "1.0.0").mkdir(parents=True)
        # No definition.json

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"wf_missing": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_workflows()

        assert len(result) == 1
        assert "error" in result[0]


# =========================================================================
# list_orchestration_workflows
# =========================================================================


class TestListOrchWorkflowsDirMissing:
    """Tests for missing workflows directory."""

    def test_returns_empty_when_dir_missing(self, tmp_path):
        """When workflows/ doesn't exist, returns []."""
        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert result == []


class TestListOrchWorkflowsDirIteration:
    """Tests for directory filtering."""

    def test_skips_non_dirs_and_underscore(self, tmp_path):
        """Files and underscore-prefixed dirs are skipped."""
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        (wf_dir / "readme.md").write_text("hi")
        (wf_dir / "_internal").mkdir()

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert result == []


class TestListOrchWorkflowsVersionResolution:
    """Tests for active version resolution."""

    def test_active_version_from_releases(self, tmp_path):
        """Active version used directly."""
        wf_dir = tmp_path / "workflows" / "orch_a"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Orch A",
            "steps": [{"id": "s1"}],
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"orch_a": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert len(result) == 1
        assert result[0]["workflow_id"] == "orch_a"

    def test_fallback_scanning_releases(self, tmp_path):
        """Falls back to scanning releases/ when no active version."""
        wf_dir = tmp_path / "workflows" / "orch_b"
        for v in ["1.0.0", "3.0.0"]:
            defn_path = wf_dir / "releases" / v / "definition.json"
            defn_path.parent.mkdir(parents=True)
            defn_path.write_text(json.dumps({
                "name": "Orch B",
                "steps": [{"id": "s1"}],
            }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert len(result) == 1
        assert result[0]["active_version"] == "3.0.0"

    def test_no_version_skips(self, tmp_path):
        """No version -> skipped."""
        wf_dir = tmp_path / "workflows" / "orch_c"
        wf_dir.mkdir(parents=True)

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert result == []


class TestListOrchWorkflowsLoadSuccess:
    """Tests for successful orchestration workflow loading."""

    def test_step_based_returns_summary(self, tmp_path):
        """Step-based (no nodes/edges) returns orchestration summary."""
        wf_dir = tmp_path / "workflows" / "orch_step"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Orchestration Step",
            "description": "Step based workflow",
            "steps": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}],
            "schema_version": "workflow.v1",
            "pow_class": "production",
            "tags": ["core"],
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"orch_step": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert len(result) == 1
        assert result[0]["name"] == "Orchestration Step"
        assert result[0]["step_count"] == 3
        assert result[0]["pow_class"] == "production"
        assert result[0]["tags"] == ["core"]

    def test_graph_based_returns_none(self, tmp_path):
        """Graph-based (has nodes+edges) returns None from build_orchestration_summary."""
        wf_dir = tmp_path / "workflows" / "orch_graph"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Graph Based",
            "nodes": [{"id": "n1"}],
            "edges": [{"src": "n1", "dst": "n2"}],
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"orch_graph": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert result == []

    def test_derived_from_populated(self, tmp_path):
        """When derived_from is present, derived_from_label is built."""
        wf_dir = tmp_path / "workflows" / "orch_derived"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text(json.dumps({
            "name": "Derived Orch",
            "steps": [{"id": "s1"}],
            "derived_from": {
                "workflow_id": "parent_wf",
                "version": "2.0.0",
            },
            "source_version": "2.0.0",
        }))

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"orch_derived": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert len(result) == 1
        assert result[0]["derived_from_label"] == "parent_wf v2.0.0"
        assert result[0]["source_version"] == "2.0.0"


class TestListOrchWorkflowsLoadFailure:
    """Tests for load failure paths."""

    def test_malformed_json_produces_error(self, tmp_path):
        """Malformed JSON produces error summary."""
        wf_dir = tmp_path / "workflows" / "orch_bad"
        defn_path = wf_dir / "releases" / "1.0.0" / "definition.json"
        defn_path.parent.mkdir(parents=True)
        defn_path.write_text("{broken")

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"orch_bad": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["step_count"] == 0

    def test_missing_definition_json_produces_error(self, tmp_path):
        """Missing definition.json produces error summary."""
        wf_dir = tmp_path / "workflows" / "orch_nofile"
        (wf_dir / "releases" / "1.0.0").mkdir(parents=True)

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={"orch_nofile": "1.0.0"}),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        assert len(result) == 1
        assert "error" in result[0]

    def test_mixed_success_and_failure(self, tmp_path):
        """One good workflow + one bad produces both in results."""
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()

        # Good
        good_path = wf_dir / "good_orch" / "releases" / "1.0.0" / "definition.json"
        good_path.parent.mkdir(parents=True)
        good_path.write_text(json.dumps({
            "name": "Good Orch",
            "steps": [{"id": "s1"}],
        }))

        # Bad
        bad_path = wf_dir / "bad_orch" / "releases" / "1.0.0" / "definition.json"
        bad_path.parent.mkdir(parents=True)
        bad_path.write_text("NOT JSON")

        loader = _make_mock_loader(
            config_path=tmp_path,
            active_releases=ActiveReleases(workflows={
                "good_orch": "1.0.0",
                "bad_orch": "1.0.0",
            }),
        )
        svc = AdminWorkbenchService(loader=loader)
        result = svc.list_orchestration_workflows()

        ids = {r["workflow_id"] for r in result}
        assert "good_orch" in ids
        assert "bad_orch" in ids
        errors = [r for r in result if "error" in r]
        assert len(errors) == 1

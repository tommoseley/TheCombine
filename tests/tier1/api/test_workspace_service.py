"""
Tier-1 tests: WorkspaceService business logic.

Tests artifact ID parsing, workspace lifecycle, and state management
without external dependencies (Git, filesystem).
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceDirtyError,
    ArtifactIdError,
    Tier1Result,
    Tier1Report,
    WORKSPACE_TTL_HOURS,
)


# =============================================================================
# Fixtures
# =============================================================================


@dataclass
class MockBranch:
    """Mock branch result."""
    name: str
    commit_hash: str


@dataclass
class MockGitStatus:
    """Mock git status result."""
    is_dirty: bool = False
    modified_files: list = None
    added_files: list = None
    deleted_files: list = None
    untracked_files: list = None

    def __post_init__(self):
        self.modified_files = self.modified_files or []
        self.added_files = self.added_files or []
        self.deleted_files = self.deleted_files or []
        self.untracked_files = self.untracked_files or []


@dataclass
class MockValidationReport:
    """Mock validation report."""
    valid: bool = True
    errors: list = None

    def __post_init__(self):
        self.errors = self.errors or []


@pytest.fixture
def mock_git_service():
    """Create a mock GitService."""
    mock = Mock()
    mock.config_path = Mock()
    mock.config_path.__truediv__ = Mock(return_value=Mock())
    mock.create_branch.return_value = MockBranch(
        name="workbench/ws-abc123",
        commit_hash="abc123def456"
    )
    mock.get_status.return_value = MockGitStatus()
    mock.checkout_branch.return_value = None
    mock._run_git.return_value = None
    mock.stage_all.return_value = None
    mock.discard_changes.return_value = None
    return mock


@pytest.fixture
def mock_validator():
    """Create a mock ConfigValidator."""
    mock = Mock()
    mock.validate_package.return_value = MockValidationReport(valid=True)
    return mock


@pytest.fixture
def mock_loader():
    """Create a mock PackageLoader."""
    mock = Mock()
    mock.invalidate_cache.return_value = None
    return mock


@pytest.fixture
def service(mock_git_service, mock_validator, mock_loader):
    """Create WorkspaceService with mocked dependencies."""
    return WorkspaceService(
        git_service=mock_git_service,
        validator=mock_validator,
        loader=mock_loader,
    )


# =============================================================================
# Artifact ID Parsing Tests
# =============================================================================


class TestArtifactIdParsing:
    """Tests for artifact ID parsing."""

    def test_parse_valid_doctype_artifact(self, service):
        """Valid doctype artifact ID parses correctly."""
        result = service._parse_artifact_id("doctype:project_discovery:1.4.0:task_prompt")

        assert result["scope"] == "doctype"
        assert result["name"] == "project_discovery"
        assert result["version"] == "1.4.0"
        assert result["kind"] == "task_prompt"

    def test_parse_valid_role_artifact(self, service):
        """Valid role artifact ID parses correctly."""
        result = service._parse_artifact_id("role:technical_architect:1.0.0:role_prompt")

        assert result["scope"] == "role"
        assert result["name"] == "technical_architect"
        assert result["version"] == "1.0.0"
        assert result["kind"] == "role_prompt"

    def test_parse_valid_template_artifact(self, service):
        """Valid template artifact ID parses correctly."""
        result = service._parse_artifact_id("template:document_generator:2.0.0:template")

        assert result["scope"] == "template"
        assert result["name"] == "document_generator"
        assert result["version"] == "2.0.0"
        assert result["kind"] == "template"

    def test_parse_invalid_format_too_few_parts(self, service):
        """Artifact ID with too few parts raises error."""
        with pytest.raises(ArtifactIdError, match="Invalid artifact ID format"):
            service._parse_artifact_id("doctype:project_discovery:1.0.0")

    def test_parse_invalid_format_too_many_parts(self, service):
        """Artifact ID with too many parts raises error."""
        with pytest.raises(ArtifactIdError, match="Invalid artifact ID format"):
            service._parse_artifact_id("doctype:project:discovery:1.0.0:task_prompt")

    def test_parse_invalid_scope(self, service):
        """Artifact ID with invalid scope raises error."""
        with pytest.raises(ArtifactIdError, match="Invalid scope"):
            service._parse_artifact_id("invalid:project_discovery:1.0.0:task_prompt")


class TestArtifactIdToPath:
    """Tests for artifact ID to file path conversion."""

    def test_doctype_task_prompt_path(self, service):
        """Doctype task_prompt maps to correct path."""
        path = service._artifact_id_to_path("doctype:project_discovery:1.4.0:task_prompt")
        assert path == "document_types/project_discovery/releases/1.4.0/prompts/task.prompt.txt"

    def test_doctype_qa_prompt_path(self, service):
        """Doctype qa_prompt maps to correct path."""
        path = service._artifact_id_to_path("doctype:project_discovery:1.4.0:qa_prompt")
        assert path == "document_types/project_discovery/releases/1.4.0/prompts/qa.prompt.txt"

    def test_doctype_pgc_context_path(self, service):
        """Doctype pgc_context maps to correct path."""
        path = service._artifact_id_to_path("doctype:project_discovery:1.4.0:pgc_context")
        assert path == "document_types/project_discovery/releases/1.4.0/prompts/pgc_context.prompt.txt"

    def test_doctype_schema_path(self, service):
        """Doctype schema maps to correct path."""
        path = service._artifact_id_to_path("doctype:project_discovery:1.4.0:schema")
        assert path == "document_types/project_discovery/releases/1.4.0/schemas/output.schema.json"

    def test_doctype_manifest_path(self, service):
        """Doctype manifest maps to correct path."""
        path = service._artifact_id_to_path("doctype:project_discovery:1.4.0:manifest")
        assert path == "document_types/project_discovery/releases/1.4.0/package.yaml"

    def test_role_prompt_path(self, service):
        """Role role_prompt maps to correct path."""
        path = service._artifact_id_to_path("role:technical_architect:1.0.0:role_prompt")
        assert path == "prompts/roles/technical_architect/releases/1.0.0/role.prompt.txt"

    def test_template_path(self, service):
        """Template maps to correct path."""
        path = service._artifact_id_to_path("template:document_generator:1.0.0:template")
        assert path == "prompts/templates/document_generator/releases/1.0.0/template.txt"

    def test_invalid_doctype_kind(self, service):
        """Invalid doctype kind raises error."""
        with pytest.raises(ArtifactIdError, match="Unknown artifact kind for doctype"):
            service._artifact_id_to_path("doctype:project_discovery:1.0.0:invalid_kind")

    def test_invalid_role_kind(self, service):
        """Invalid role kind raises error."""
        with pytest.raises(ArtifactIdError, match="Unknown artifact kind for role"):
            service._artifact_id_to_path("role:technical_architect:1.0.0:invalid_kind")


class TestPathToArtifactId:
    """Tests for file path to artifact ID conversion."""

    def test_task_prompt_to_artifact_id(self, service):
        """Task prompt path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "document_types/project_discovery/releases/1.4.0/prompts/task.prompt.txt"
        )
        assert artifact_id == "doctype:project_discovery:1.4.0:task_prompt"

    def test_qa_prompt_to_artifact_id(self, service):
        """QA prompt path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "document_types/project_discovery/releases/1.4.0/prompts/qa.prompt.txt"
        )
        assert artifact_id == "doctype:project_discovery:1.4.0:qa_prompt"

    def test_pgc_context_to_artifact_id(self, service):
        """PGC context path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "document_types/project_discovery/releases/1.4.0/prompts/pgc_context.prompt.txt"
        )
        assert artifact_id == "doctype:project_discovery:1.4.0:pgc_context"

    def test_schema_to_artifact_id(self, service):
        """Schema path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "document_types/project_discovery/releases/1.4.0/schemas/output.schema.json"
        )
        assert artifact_id == "doctype:project_discovery:1.4.0:schema"

    def test_manifest_to_artifact_id(self, service):
        """Manifest path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "document_types/project_discovery/releases/1.4.0/package.yaml"
        )
        assert artifact_id == "doctype:project_discovery:1.4.0:manifest"

    def test_role_prompt_to_artifact_id(self, service):
        """Role prompt path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "prompts/roles/technical_architect/releases/1.0.0/role.prompt.txt"
        )
        assert artifact_id == "role:technical_architect:1.0.0:role_prompt"

    def test_template_to_artifact_id(self, service):
        """Template path converts to correct artifact ID."""
        artifact_id = service._path_to_artifact_id(
            "prompts/templates/document_generator/releases/1.0.0/template.txt"
        )
        assert artifact_id == "template:document_generator:1.0.0:template"

    def test_unmapped_path_returns_none(self, service):
        """Unmapped path returns None."""
        artifact_id = service._path_to_artifact_id("some/random/path.txt")
        assert artifact_id is None


# =============================================================================
# Workspace Lifecycle Tests
# =============================================================================


class TestWorkspaceLifecycle:
    """Tests for workspace creation and management."""

    def test_create_workspace_generates_unique_id(self, service):
        """Creating workspace generates unique ID and branch."""
        state = service.create_workspace("user-1")

        assert state.workspace_id.startswith("ws-")
        assert state.branch.startswith("workbench/ws-")
        assert state.user_id == "user-1"

    def test_create_workspace_sets_expiry(self, service):
        """Creating workspace sets correct expiry time."""
        before = datetime.utcnow()
        state = service.create_workspace("user-1")
        after = datetime.utcnow()

        # Expiry should be ~24 hours from now
        min_expiry = before + timedelta(hours=WORKSPACE_TTL_HOURS)
        max_expiry = after + timedelta(hours=WORKSPACE_TTL_HOURS)

        assert min_expiry <= state.expires_at <= max_expiry

    def test_create_workspace_calls_git_create_branch(self, service, mock_git_service):
        """Creating workspace creates Git branch."""
        service.create_workspace("user-1")

        mock_git_service.create_branch.assert_called_once()
        call_args = mock_git_service.create_branch.call_args[0]
        assert call_args[0].startswith("workbench/ws-")

    def test_create_workspace_rejects_duplicate_user(self, service):
        """User cannot create second workspace."""
        service.create_workspace("user-1")

        with pytest.raises(WorkspaceError, match="already has an active workspace"):
            service.create_workspace("user-1")

    def test_get_current_workspace_returns_none_for_new_user(self, service):
        """get_current_workspace returns None for user without workspace."""
        result = service.get_current_workspace("user-1")
        assert result is None

    def test_get_current_workspace_returns_existing(self, service):
        """get_current_workspace returns existing workspace."""
        created = service.create_workspace("user-1")
        retrieved = service.get_current_workspace("user-1")

        assert retrieved.workspace_id == created.workspace_id
        assert retrieved.user_id == created.user_id

    def test_close_workspace_removes_from_registry(self, service):
        """Closing workspace removes it from registry."""
        state = service.create_workspace("user-1")

        service.close_workspace(state.workspace_id)

        assert service.get_current_workspace("user-1") is None

    def test_close_workspace_not_found_raises(self, service):
        """Closing non-existent workspace raises error."""
        with pytest.raises(WorkspaceNotFoundError):
            service.close_workspace("ws-nonexistent")

    def test_close_dirty_workspace_without_force_raises(self, service, mock_git_service):
        """Closing dirty workspace without force raises error."""
        state = service.create_workspace("user-1")

        # Simulate dirty state
        mock_git_service.get_status.return_value = MockGitStatus(is_dirty=True)

        with pytest.raises(WorkspaceDirtyError, match="uncommitted changes"):
            service.close_workspace(state.workspace_id)

    def test_close_dirty_workspace_with_force_succeeds(self, service, mock_git_service):
        """Closing dirty workspace with force succeeds."""
        state = service.create_workspace("user-1")

        # Simulate dirty state
        mock_git_service.get_status.return_value = MockGitStatus(is_dirty=True)

        # Should not raise with force=True
        service.close_workspace(state.workspace_id, force=True)

        assert service.get_current_workspace("user-1") is None


class TestWorkspaceState:
    """Tests for workspace state queries."""

    def test_get_workspace_state_returns_git_status(self, service, mock_git_service):
        """Workspace state includes git dirty status."""
        state = service.create_workspace("user-1")

        mock_git_service.get_status.return_value = MockGitStatus(is_dirty=True)

        current = service.get_workspace_state(state.workspace_id)

        assert current.is_dirty is True

    def test_get_workspace_state_maps_modified_files(self, service, mock_git_service):
        """Workspace state maps modified files to artifact IDs."""
        state = service.create_workspace("user-1")

        mock_git_service.get_status.return_value = MockGitStatus(
            is_dirty=True,
            modified_files=[
                "document_types/project_discovery/releases/1.4.0/prompts/task.prompt.txt"
            ]
        )

        # Mock Path operations for validation
        from pathlib import Path
        mock_path = MagicMock(spec=Path)
        mock_path.__truediv__ = lambda self, other: mock_path
        mock_path.exists.return_value = False  # Skip validation by pretending path doesn't exist
        mock_git_service.config_path = mock_path

        current = service.get_workspace_state(state.workspace_id)

        assert "doctype:project_discovery:1.4.0:task_prompt" in current.modified_artifacts

    def test_get_workspace_state_not_found_raises(self, service):
        """Getting state for non-existent workspace raises error."""
        with pytest.raises(WorkspaceNotFoundError):
            service.get_workspace_state("ws-nonexistent")

    def test_workspace_state_updates_last_touched(self, service):
        """Accessing workspace state updates last_touched."""
        state = service.create_workspace("user-1")
        original_touched = state.last_touched

        # Small delay to ensure time difference
        import time
        time.sleep(0.01)

        updated = service.get_workspace_state(state.workspace_id)

        assert updated.last_touched >= original_touched


# =============================================================================
# Tier 1 Validation Tests
# =============================================================================


class TestTier1Validation:
    """Tests for Tier 1 validation."""

    def test_tier1_passes_with_no_modified_packages(self, service):
        """Tier 1 passes when no packages modified."""
        report = service._run_tier1_validation([])

        assert report.passed is True
        assert any(r.rule_id == "NO_PACKAGES_MODIFIED" for r in report.results)

    def test_tier1_reports_validation_errors(self, service, mock_validator, mock_git_service):
        """Tier 1 reports validation errors from validator."""
        # Setup mock validation failure
        @dataclass
        class MockError:
            rule_id: str
            message: str

        mock_validator.validate_package.return_value = MockValidationReport(
            valid=False,
            errors=[MockError(rule_id="MANIFEST_INVALID", message="Bad manifest")]
        )

        # Mock path existence
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_git_service.config_path.__truediv__.return_value = mock_path

        report = service._run_tier1_validation(["doctype:project_discovery:1.4.0:task_prompt"])

        assert report.passed is False
        assert any(r.rule_id == "MANIFEST_INVALID" for r in report.results)


class TestTier1ValidationCoverage:
    """Extended tests for _run_tier1_validation to cover untested branches."""

    # -----------------------------------------------------------------
    # Doctype validation branches
    # -----------------------------------------------------------------

    def test_tier1_doctype_valid_package_reports_pass(self, service, mock_validator, mock_git_service, tmp_path):
        """Tier 1 reports PACKAGE_VALID when validator says valid."""
        mock_validator.validate_package.return_value = MockValidationReport(valid=True, errors=[])

        # Create the package directory so path.exists() returns True
        dt_dir = tmp_path / "document_types" / "project_discovery" / "releases" / "1.4.0"
        dt_dir.mkdir(parents=True)
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["doctype:project_discovery:1.4.0:task_prompt"])

        assert report.passed is True
        assert any(r.rule_id == "PACKAGE_VALID" and r.status == "pass" for r in report.results)
        assert any("doctype:project_discovery:1.4.0:manifest" == r.artifact_id for r in report.results)

    def test_tier1_doctype_package_path_not_exists_skipped(self, service, mock_validator, mock_git_service, tmp_path):
        """Tier 1 skips validation when package path does not exist."""
        # Point config_path to a real dir, but do NOT create the package subdir
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["doctype:project_discovery:1.4.0:task_prompt"])

        # Validator should not be called since the path doesn't exist
        mock_validator.validate_package.assert_not_called()
        # Report should still pass (no errors added)
        assert report.passed is True

    def test_tier1_doctype_deduplicates_same_package(self, service, mock_validator, mock_git_service, tmp_path):
        """Two artifacts from the same doctype/version validate package once."""
        mock_validator.validate_package.return_value = MockValidationReport(valid=True, errors=[])

        dt_dir = tmp_path / "document_types" / "project_discovery" / "releases" / "1.4.0"
        dt_dir.mkdir(parents=True)
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation([
            "doctype:project_discovery:1.4.0:task_prompt",
            "doctype:project_discovery:1.4.0:qa_prompt",
        ])

        # validate_package called exactly once because both map to same (name, version)
        assert mock_validator.validate_package.call_count == 1
        assert report.passed is True

    def test_tier1_invalid_artifact_id_skipped_in_doctype_scan(self, service, mock_git_service):
        """Invalid artifact IDs are silently skipped during doctype extraction."""
        # "bad" is not a valid scope -- _parse_artifact_id will raise ArtifactIdError
        report = service._run_tier1_validation(["bad:id:format"])

        # Should not crash; reports NO_PACKAGES_MODIFIED since nothing valid was found
        assert report.passed is True
        assert any(r.rule_id == "NO_PACKAGES_MODIFIED" for r in report.results)

    def test_tier1_non_doctype_artifact_skipped_for_package_validation(self, service, mock_validator, mock_git_service, tmp_path):
        """Role artifacts do not trigger package validation."""
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["role:technical_architect:1.0.0:role_prompt"])

        mock_validator.validate_package.assert_not_called()
        # Still passes -- role is not a doctype so no package validation
        assert report.passed is True

    def test_tier1_doctype_validation_multiple_errors(self, service, mock_validator, mock_git_service, tmp_path):
        """Multiple validation errors from a single package all appear."""
        @dataclass
        class MockError:
            rule_id: str
            message: str

        mock_validator.validate_package.return_value = MockValidationReport(
            valid=False,
            errors=[
                MockError(rule_id="MISSING_FIELD", message="Missing required field"),
                MockError(rule_id="INVALID_VALUE", message="Bad value for field"),
            ]
        )

        dt_dir = tmp_path / "document_types" / "test_doc" / "releases" / "2.0.0"
        dt_dir.mkdir(parents=True)
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["doctype:test_doc:2.0.0:schema"])

        assert report.passed is False
        fail_ids = [r.rule_id for r in report.results if r.status == "fail"]
        assert "MISSING_FIELD" in fail_ids
        assert "INVALID_VALUE" in fail_ids
        assert len(fail_ids) == 2

    # -----------------------------------------------------------------
    # Workflow validation branches
    # -----------------------------------------------------------------

    def test_tier1_workflow_valid_graph_based(self, service, mock_git_service, tmp_path):
        """Tier 1 validates graph-based workflow and reports WORKFLOW_VALID."""
        # Create a temporary workflow file
        wf_dir = tmp_path / "workflows" / "test_wf" / "releases" / "1.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        wf_file.write_text(json.dumps({
            "workflow_id": "test_wf",
            "nodes": [
                {"id": "start", "type": "intake_gate"},
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "end", "kind": "auto"},
            ],
            "entry_node_ids": ["start"],
        }))

        # Point config_path to tmp_path
        mock_git_service.config_path = tmp_path

        with patch("app.domain.workflow.plan_validator.PlanValidator") as MockPV:
            mock_pv_instance = Mock()
            MockPV.return_value = mock_pv_instance

            @dataclass
            class MockPVResult:
                valid: bool
                errors: list = field(default_factory=list)

            mock_pv_instance.validate.return_value = MockPVResult(valid=True)

            report = service._run_tier1_validation(["workflow:test_wf:1.0.0:definition"])

        assert report.passed is True
        assert any(r.rule_id == "WORKFLOW_VALID" and r.status == "pass" for r in report.results)

    def test_tier1_workflow_invalid_graph_based(self, service, mock_git_service, tmp_path):
        """Tier 1 reports errors for invalid graph-based workflow."""
        wf_dir = tmp_path / "workflows" / "bad_wf" / "releases" / "1.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        wf_file.write_text(json.dumps({
            "workflow_id": "bad_wf",
            "nodes": [],
            "edges": [],
            "entry_node_ids": ["missing"],
        }))

        mock_git_service.config_path = tmp_path

        with patch("app.domain.workflow.plan_validator.PlanValidator") as MockPV:
            mock_pv_instance = Mock()
            MockPV.return_value = mock_pv_instance

            @dataclass
            class MockPVError:
                code: str
                message: str

            @dataclass
            class MockPVResult:
                valid: bool
                errors: list = field(default_factory=list)

            mock_pv_instance.validate.return_value = MockPVResult(
                valid=False,
                errors=[MockPVError(code="ENTRY_NODE_NOT_FOUND", message="Entry node 'missing' not found")]
            )

            report = service._run_tier1_validation(["workflow:bad_wf:1.0.0:definition"])

        assert report.passed is False
        assert any(r.rule_id == "ENTRY_NODE_NOT_FOUND" and r.status == "fail" for r in report.results)
        assert any("workflow:bad_wf:1.0.0:definition" == r.artifact_id for r in report.results)

    def test_tier1_workflow_invalid_graph_error_code_with_value_attr(self, service, mock_git_service, tmp_path):
        """Tier 1 extracts error.code.value when code has a value attribute (Enum)."""
        wf_dir = tmp_path / "workflows" / "enum_wf" / "releases" / "1.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        wf_file.write_text(json.dumps({
            "workflow_id": "enum_wf",
            "nodes": [],
            "edges": [],
            "entry_node_ids": ["missing"],
        }))

        mock_git_service.config_path = tmp_path

        with patch("app.domain.workflow.plan_validator.PlanValidator") as MockPV:
            mock_pv_instance = Mock()
            MockPV.return_value = mock_pv_instance

            # Simulate Enum-like code with .value attribute
            mock_code = Mock()
            mock_code.value = "ORPHAN_NODE"

            @dataclass
            class MockPVResult:
                valid: bool
                errors: list = field(default_factory=list)

            mock_error = Mock()
            mock_error.code = mock_code
            mock_error.message = "Orphan node detected"

            mock_pv_instance.validate.return_value = MockPVResult(
                valid=False,
                errors=[mock_error]
            )

            report = service._run_tier1_validation(["workflow:enum_wf:1.0.0:definition"])

        assert report.passed is False
        assert any(r.rule_id == "ORPHAN_NODE" for r in report.results)

    def test_tier1_workflow_step_based_json_valid(self, service, mock_git_service, tmp_path):
        """Tier 1 reports WORKFLOW_JSON_VALID for step-based (non-graph) workflows."""
        wf_dir = tmp_path / "workflows" / "step_wf" / "releases" / "1.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        # Step-based workflow: no "nodes" or "edges" keys
        wf_file.write_text(json.dumps({
            "workflow_id": "step_wf",
            "version": "workflow.v1",
            "steps": [{"action": "run_task", "task_id": "intake"}],
        }))

        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["workflow:step_wf:1.0.0:definition"])

        assert report.passed is True
        assert any(r.rule_id == "WORKFLOW_JSON_VALID" and r.status == "pass" for r in report.results)

    def test_tier1_workflow_invalid_json(self, service, mock_git_service, tmp_path):
        """Tier 1 reports INVALID_JSON for malformed workflow JSON."""
        wf_dir = tmp_path / "workflows" / "broken_wf" / "releases" / "1.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        wf_file.write_text("{invalid json content!!!")

        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["workflow:broken_wf:1.0.0:definition"])

        assert report.passed is False
        assert any(r.rule_id == "INVALID_JSON" and r.status == "fail" for r in report.results)
        fail_result = [r for r in report.results if r.rule_id == "INVALID_JSON"][0]
        assert "Invalid JSON" in fail_result.message

    def test_tier1_workflow_path_not_exists_skipped(self, service, mock_git_service, tmp_path):
        """Tier 1 skips workflow when definition file does not exist."""
        # Point config_path to tmp_path but do NOT create the workflow file
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation(["workflow:missing_wf:1.0.0:definition"])

        # Should still pass -- no file found means nothing to validate
        assert report.passed is True

    def test_tier1_invalid_artifact_id_skipped_in_workflow_scan(self, service, mock_git_service):
        """Invalid artifact IDs are silently skipped during workflow extraction."""
        report = service._run_tier1_validation(["not:enough:parts"])

        assert report.passed is True
        assert any(r.rule_id == "NO_PACKAGES_MODIFIED" for r in report.results)

    # -----------------------------------------------------------------
    # Mixed artifact tests
    # -----------------------------------------------------------------

    def test_tier1_mix_doctype_and_workflow(self, service, mock_validator, mock_git_service, tmp_path):
        """Tier 1 validates both doctype packages and workflow definitions."""
        # Setup doctype validation (pass)
        mock_validator.validate_package.return_value = MockValidationReport(valid=True, errors=[])

        # Setup workflow file (step-based, valid JSON)
        wf_dir = tmp_path / "workflows" / "my_wf" / "releases" / "2.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        wf_file.write_text(json.dumps({"workflow_id": "my_wf", "steps": []}))

        # For doctype, config_path needs to return a mock path with exists()=True
        # For workflow, config_path needs to be real tmp_path.
        # The function does config_path / "document_types" / ... for doctype,
        # and config_path / "workflows" / ... for workflow.
        # Use tmp_path and create the doctype directory structure too.
        dt_dir = tmp_path / "document_types" / "test_doc" / "releases" / "1.0.0"
        dt_dir.mkdir(parents=True)

        mock_git_service.config_path = tmp_path

        with patch("app.domain.workflow.plan_validator.PlanValidator"):
            report = service._run_tier1_validation([
                "doctype:test_doc:1.0.0:task_prompt",
                "workflow:my_wf:2.0.0:definition",
            ])

        assert report.passed is True
        rule_ids = [r.rule_id for r in report.results]
        assert "PACKAGE_VALID" in rule_ids
        assert "WORKFLOW_JSON_VALID" in rule_ids

    def test_tier1_no_packages_no_workflows_only_role(self, service, mock_validator, mock_git_service, tmp_path):
        """When only non-doctype/non-workflow artifacts are modified, NO_PACKAGES_MODIFIED is returned."""
        mock_git_service.config_path = tmp_path

        report = service._run_tier1_validation([
            "role:technical_architect:1.0.0:role_prompt",
            "template:document_generator:1.0.0:template",
        ])

        assert report.passed is True
        assert any(r.rule_id == "NO_PACKAGES_MODIFIED" for r in report.results)

    def test_tier1_workflow_multiple_errors(self, service, mock_git_service, tmp_path):
        """Multiple validation errors from a graph workflow all appear in report."""
        wf_dir = tmp_path / "workflows" / "multi_err" / "releases" / "1.0.0"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "definition.json"
        wf_file.write_text(json.dumps({
            "workflow_id": "multi_err",
            "nodes": [],
            "edges": [{"source": "a", "target": "b"}],
            "entry_node_ids": ["c"],
        }))

        mock_git_service.config_path = tmp_path

        with patch("app.domain.workflow.plan_validator.PlanValidator") as MockPV:
            mock_pv_instance = Mock()
            MockPV.return_value = mock_pv_instance

            @dataclass
            class MockPVResult:
                valid: bool
                errors: list = field(default_factory=list)

            err1 = Mock()
            err1.code = "ERR_ONE"
            err1.message = "First error"

            err2 = Mock()
            err2.code = "ERR_TWO"
            err2.message = "Second error"

            mock_pv_instance.validate.return_value = MockPVResult(
                valid=False,
                errors=[err1, err2]
            )

            report = service._run_tier1_validation(["workflow:multi_err:1.0.0:definition"])

        assert report.passed is False
        fail_ids = [r.rule_id for r in report.results if r.status == "fail"]
        assert "ERR_ONE" in fail_ids
        assert "ERR_TWO" in fail_ids
        assert len(fail_ids) == 2


# =============================================================================
# Commit and Discard Tests
# =============================================================================


class TestCommitDiscard:
    """Tests for commit and discard operations."""

    def test_discard_calls_git_discard(self, service, mock_git_service):
        """Discard calls git discard_changes."""
        state = service.create_workspace("user-1")

        service.discard(state.workspace_id)

        mock_git_service.discard_changes.assert_called_once()

    def test_discard_not_found_raises(self, service):
        """Discarding non-existent workspace raises error."""
        with pytest.raises(WorkspaceNotFoundError):
            service.discard("ws-nonexistent")

    def test_commit_stages_and_commits(self, service, mock_git_service):
        """Commit stages all and creates commit."""
        state = service.create_workspace("user-1")

        # Mock commit result
        @dataclass
        class MockCommit:
            commit_hash: str
            commit_hash_short: str

        mock_git_service.commit.return_value = MockCommit(
            commit_hash="abc123def456",
            commit_hash_short="abc123"
        )

        result = service.commit(state.workspace_id, "Test commit", "user-1", "123")

        mock_git_service.stage_all.assert_called_once()
        mock_git_service.commit.assert_called_once()
        assert result.commit_hash == "abc123def456"

    def test_commit_includes_actor_trailer(self, service, mock_git_service):
        """Commit includes Combine-Actor trailer in message."""
        state = service.create_workspace("user-1")

        @dataclass
        class MockCommit:
            commit_hash: str
            commit_hash_short: str

        mock_git_service.commit.return_value = MockCommit(
            commit_hash="abc123def456",
            commit_hash_short="abc123"
        )

        service.commit(state.workspace_id, "Test commit", "tom", "123")

        # Check commit message includes trailer
        call_args = mock_git_service.commit.call_args[0]
        message = call_args[0]
        assert "Combine-Actor: tom" in message
        assert "Combine-Actor-Id: 123" in message
        assert "Combine-Intent: prompt-edit" in message

    def test_commit_blocked_by_tier1_failure(self, service, mock_git_service, mock_validator):
        """Commit is blocked when Tier 1 validation fails."""
        state = service.create_workspace("user-1")

        # Setup modified file
        mock_git_service.get_status.return_value = MockGitStatus(
            is_dirty=True,
            modified_files=["document_types/test/releases/1.0.0/prompts/task.prompt.txt"]
        )

        # Setup validation failure
        @dataclass
        class MockError:
            rule_id: str
            message: str

        mock_validator.validate_package.return_value = MockValidationReport(
            valid=False,
            errors=[MockError(rule_id="VALIDATION_FAILED", message="Error")]
        )

        # Mock path
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_git_service.config_path.__truediv__.return_value = mock_path

        with pytest.raises(WorkspaceError, match="Tier 1 validation failed"):
            service.commit(state.workspace_id, "Test commit", "user-1")


# =============================================================================
# TTL Cleanup Tests
# =============================================================================


class TestTTLCleanup:
    """Tests for TTL-based workspace cleanup."""

    def test_cleanup_removes_expired_workspaces(self, service):
        """Cleanup removes workspaces past expiry."""
        state = service.create_workspace("user-1")

        # Force expire the workspace
        workspace_id = state.workspace_id
        with service._lock:
            service._workspaces[workspace_id].expires_at = datetime.utcnow() - timedelta(hours=1)

        cleaned = service.cleanup_expired_workspaces()

        assert cleaned == 1
        assert service.get_current_workspace("user-1") is None

    def test_cleanup_preserves_active_workspaces(self, service):
        """Cleanup preserves non-expired workspaces."""
        service.create_workspace("user-1")

        cleaned = service.cleanup_expired_workspaces()

        assert cleaned == 0
        assert service.get_current_workspace("user-1") is not None

    def test_get_current_workspace_returns_none_for_expired(self, service):
        """get_current_workspace returns None for expired workspace."""
        state = service.create_workspace("user-1")

        # Force expire
        with service._lock:
            service._workspaces[state.workspace_id].expires_at = datetime.utcnow() - timedelta(hours=1)

        result = service.get_current_workspace("user-1")

        assert result is None

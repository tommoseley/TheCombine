"""
Tier-1 tests: WorkspaceService business logic.

Tests artifact ID parsing, workspace lifecycle, and state management
without external dependencies (Git, filesystem).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceDirtyError,
    ArtifactIdError,
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
        state = service.create_workspace("user-1")

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

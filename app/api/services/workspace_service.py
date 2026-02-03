"""
Workspace Service for Admin Workbench.

Per ADR-044 WS-044-03, this service manages editing workspaces
for configuration artifacts with Git-integrated workflow.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from app.api.services.git_service import (
    GitService,
    GitServiceError,
    GitConflictError,
    get_git_service,
)
from app.api.services.config_validator import (
    ConfigValidator,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
)
from app.config.package_loader import (
    PackageLoader,
    get_package_loader,
    PackageNotFoundError,
)

logger = logging.getLogger(__name__)

# Workspace TTL (24 hours)
WORKSPACE_TTL_HOURS = 24

# Branch prefix for workspaces
WORKSPACE_BRANCH_PREFIX = "workbench/ws-"


class WorkspaceError(Exception):
    """Base error for workspace operations."""
    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Workspace not found."""
    pass


class WorkspaceDirtyError(WorkspaceError):
    """Workspace has uncommitted changes."""
    pass


class ArtifactError(WorkspaceError):
    """Error with artifact operations."""
    pass


class ArtifactNotFoundError(ArtifactError):
    """Artifact not found."""
    pass


class ArtifactIdError(ArtifactError):
    """Invalid artifact ID format."""
    pass


@dataclass
class Tier1Result:
    """Single tier 1 validation result."""
    rule_id: str
    status: str  # "pass" or "fail"
    message: Optional[str] = None
    artifact_id: Optional[str] = None


@dataclass
class Tier1Report:
    """Tier 1 validation report."""
    passed: bool
    results: List[Tier1Result] = field(default_factory=list)


@dataclass
class WorkspaceState:
    """Current workspace state."""
    workspace_id: str
    user_id: str
    branch: str
    base_commit: str
    is_dirty: bool
    modified_artifacts: List[str]
    modified_files: List[str]
    tier1: Tier1Report
    last_touched: datetime
    expires_at: datetime


@dataclass
class ArtifactContent:
    """Artifact content response."""
    artifact_id: str
    content: str
    version: str


@dataclass
class PreviewProvenance:
    """Provenance information for preview."""
    role: Optional[str] = None
    schema: Optional[str] = None
    package: Optional[str] = None


@dataclass
class PreviewResult:
    """Preview result with resolved prompt."""
    resolved_prompt: str
    provenance: PreviewProvenance


@dataclass
class CommitResult:
    """Result of a commit operation."""
    commit_hash: str
    commit_hash_short: str
    message: str


@dataclass
class WorkspaceMetadata:
    """Internal workspace metadata."""
    workspace_id: str
    user_id: str
    branch: str
    base_commit: str
    created_at: datetime
    last_touched: datetime
    expires_at: datetime


class WorkspaceService:
    """
    Service for managing Admin Workbench workspaces.

    Workspaces are isolated editing contexts (Git branches) that persist
    until explicitly closed, discarded+clean, or TTL expires.
    """

    def __init__(
        self,
        git_service: Optional[GitService] = None,
        validator: Optional[ConfigValidator] = None,
        loader: Optional[PackageLoader] = None,
    ):
        """
        Initialize the workspace service.

        Args:
            git_service: Optional GitService instance.
            validator: Optional ConfigValidator instance.
            loader: Optional PackageLoader instance.
        """
        self._git = git_service or get_git_service()
        self._validator = validator or ConfigValidator()
        self._loader = loader or get_package_loader()

        # In-memory workspace registry (keyed by workspace_id)
        self._workspaces: Dict[str, WorkspaceMetadata] = {}
        # Index by user_id for quick lookup
        self._user_workspaces: Dict[str, str] = {}  # user_id -> workspace_id
        self._lock = Lock()

    # =========================================================================
    # Artifact ID Parsing
    # =========================================================================

    def _parse_artifact_id(self, artifact_id: str) -> Dict[str, str]:
        """
        Parse artifact ID into components.

        Format: {scope}:{name}:{version}:{kind}

        Examples:
        - doctype:project_discovery:1.4.0:task_prompt
        - role:technical_architect:1.0.0:role_prompt
        - template:document_generator:1.0.0:template

        Returns:
            Dict with scope, name, version, kind
        """
        parts = artifact_id.split(":")
        if len(parts) != 4:
            raise ArtifactIdError(
                f"Invalid artifact ID format: {artifact_id}. "
                f"Expected {{scope}}:{{name}}:{{version}}:{{kind}}"
            )

        scope, name, version, kind = parts

        if scope not in ("doctype", "role", "template"):
            raise ArtifactIdError(
                f"Invalid scope '{scope}' in artifact ID. "
                f"Expected: doctype, role, or template"
            )

        return {
            "scope": scope,
            "name": name,
            "version": version,
            "kind": kind,
        }

    def _artifact_id_to_path(self, artifact_id: str) -> str:
        """
        Convert artifact ID to file path (relative to combine-config).

        Returns:
            File path string
        """
        parsed = self._parse_artifact_id(artifact_id)
        scope = parsed["scope"]
        name = parsed["name"]
        version = parsed["version"]
        kind = parsed["kind"]

        if scope == "doctype":
            # Document type artifacts
            kind_to_file = {
                "task_prompt": "prompts/task.prompt.txt",
                "qa_prompt": "prompts/qa.prompt.txt",
                "reflection_prompt": "prompts/reflection.prompt.txt",
                "pgc_context": "prompts/pgc_context.prompt.txt",
                "questions_prompt": "prompts/questions.prompt.txt",
                "schema": "schemas/output.schema.json",
                "manifest": "package.yaml",
            }
            if kind not in kind_to_file:
                raise ArtifactIdError(f"Unknown artifact kind for doctype: {kind}")
            return f"document_types/{name}/releases/{version}/{kind_to_file[kind]}"

        elif scope == "role":
            if kind != "role_prompt":
                raise ArtifactIdError(f"Unknown artifact kind for role: {kind}")
            return f"prompts/roles/{name}/releases/{version}/role.prompt.txt"

        elif scope == "template":
            if kind != "template":
                raise ArtifactIdError(f"Unknown artifact kind for template: {kind}")
            return f"prompts/templates/{name}/releases/{version}/template.txt"

        raise ArtifactIdError(f"Unknown scope: {scope}")

    def _path_to_artifact_id(self, file_path: str) -> Optional[str]:
        """
        Convert file path to artifact ID.

        Returns:
            Artifact ID or None if not mappable
        """
        # Document type artifacts
        match = re.match(
            r"document_types/([^/]+)/releases/([^/]+)/prompts/task\.prompt\.txt$",
            file_path
        )
        if match:
            return f"doctype:{match.group(1)}:{match.group(2)}:task_prompt"

        match = re.match(
            r"document_types/([^/]+)/releases/([^/]+)/prompts/qa\.prompt\.txt$",
            file_path
        )
        if match:
            return f"doctype:{match.group(1)}:{match.group(2)}:qa_prompt"

        match = re.match(
            r"document_types/([^/]+)/releases/([^/]+)/prompts/reflection\.prompt\.txt$",
            file_path
        )
        if match:
            return f"doctype:{match.group(1)}:{match.group(2)}:reflection_prompt"

        match = re.match(
            r"document_types/([^/]+)/releases/([^/]+)/prompts/pgc_context\.prompt\.txt$",
            file_path
        )
        if match:
            return f"doctype:{match.group(1)}:{match.group(2)}:pgc_context"

        match = re.match(
            r"document_types/([^/]+)/releases/([^/]+)/schemas/output\.schema\.json$",
            file_path
        )
        if match:
            return f"doctype:{match.group(1)}:{match.group(2)}:schema"

        match = re.match(
            r"document_types/([^/]+)/releases/([^/]+)/package\.yaml$",
            file_path
        )
        if match:
            return f"doctype:{match.group(1)}:{match.group(2)}:manifest"

        # Role prompts
        match = re.match(
            r"prompts/roles/([^/]+)/releases/([^/]+)/role\.prompt\.txt$",
            file_path
        )
        if match:
            return f"role:{match.group(1)}:{match.group(2)}:role_prompt"

        # Templates
        match = re.match(
            r"prompts/templates/([^/]+)/releases/([^/]+)/template\.txt$",
            file_path
        )
        if match:
            return f"template:{match.group(1)}:{match.group(2)}:template"

        return None

    # =========================================================================
    # Workspace Lifecycle
    # =========================================================================

    def get_current_workspace(self, user_id: str) -> Optional[WorkspaceState]:
        """
        Get the current workspace for a user.

        Args:
            user_id: User identifier

        Returns:
            WorkspaceState or None if no workspace exists
        """
        with self._lock:
            workspace_id = self._user_workspaces.get(user_id)
            if not workspace_id:
                return None

            metadata = self._workspaces.get(workspace_id)
            if not metadata:
                # Inconsistent state, clean up
                del self._user_workspaces[user_id]
                return None

            # Check if expired
            if datetime.utcnow() > metadata.expires_at:
                self._cleanup_workspace(workspace_id)
                return None

        return self._get_workspace_state(workspace_id)

    def create_workspace(self, user_id: str) -> WorkspaceState:
        """
        Create a new workspace for a user.

        Creates a new branch from the current HEAD for isolated editing.

        Args:
            user_id: User identifier

        Returns:
            WorkspaceState for the new workspace
        """
        with self._lock:
            # Check if user already has a workspace
            if user_id in self._user_workspaces:
                raise WorkspaceError(
                    f"User {user_id} already has an active workspace. "
                    f"Close it first or use get_current_workspace."
                )

            # Generate workspace ID
            workspace_id = f"ws-{uuid.uuid4().hex[:12]}"
            branch_name = f"{WORKSPACE_BRANCH_PREFIX}{workspace_id[3:]}"

            # Create branch
            try:
                branch = self._git.create_branch(branch_name)
            except GitServiceError as e:
                raise WorkspaceError(f"Failed to create workspace branch: {e}")

            # Record metadata
            now = datetime.utcnow()
            metadata = WorkspaceMetadata(
                workspace_id=workspace_id,
                user_id=user_id,
                branch=branch_name,
                base_commit=branch.commit_hash,
                created_at=now,
                last_touched=now,
                expires_at=now + timedelta(hours=WORKSPACE_TTL_HOURS),
            )

            self._workspaces[workspace_id] = metadata
            self._user_workspaces[user_id] = workspace_id

        return self._get_workspace_state(workspace_id)

    def close_workspace(self, workspace_id: str, force: bool = False) -> None:
        """
        Close a workspace.

        Args:
            workspace_id: Workspace to close
            force: If True, close even if dirty

        Raises:
            WorkspaceNotFoundError: Workspace not found
            WorkspaceDirtyError: Workspace has uncommitted changes and force=False
        """
        with self._lock:
            metadata = self._workspaces.get(workspace_id)
            if not metadata:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

            # Check if dirty (need to be on the branch first)
            status = self._git.get_status()
            if status.is_dirty and not force:
                raise WorkspaceDirtyError(
                    "Workspace has uncommitted changes. "
                    "Commit or discard changes first, or use force=True."
                )

            self._cleanup_workspace(workspace_id)

    def _cleanup_workspace(self, workspace_id: str) -> None:
        """
        Internal cleanup of workspace (must hold lock).

        Args:
            workspace_id: Workspace to clean up
        """
        metadata = self._workspaces.get(workspace_id)
        if metadata:
            # Remove from indexes
            if metadata.user_id in self._user_workspaces:
                if self._user_workspaces[metadata.user_id] == workspace_id:
                    del self._user_workspaces[metadata.user_id]
            del self._workspaces[workspace_id]

            # Try to switch to main and delete branch
            try:
                self._git.checkout_branch("main")
                self._git._run_git("branch", "-D", metadata.branch)
            except GitServiceError:
                # Best effort - branch cleanup may fail
                logger.warning(f"Failed to clean up branch {metadata.branch}")

    def _touch_workspace(self, workspace_id: str) -> None:
        """Update last_touched and expires_at for a workspace."""
        with self._lock:
            metadata = self._workspaces.get(workspace_id)
            if metadata:
                now = datetime.utcnow()
                metadata.last_touched = now
                metadata.expires_at = now + timedelta(hours=WORKSPACE_TTL_HOURS)

    # =========================================================================
    # Workspace State
    # =========================================================================

    def get_workspace_state(self, workspace_id: str) -> WorkspaceState:
        """
        Get current state of a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            WorkspaceState with git status, validation, and TTL info
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)
        return self._get_workspace_state(workspace_id)

    def _get_workspace_state(self, workspace_id: str) -> WorkspaceState:
        """
        Internal: Get workspace state (no lock).

        Args:
            workspace_id: Workspace identifier

        Returns:
            WorkspaceState
        """
        metadata = self._workspaces.get(workspace_id)
        if not metadata:
            raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        # Get git status
        git_status = self._git.get_status()

        # Convert file paths to artifact IDs
        all_modified_files = (
            git_status.modified_files +
            git_status.added_files +
            git_status.deleted_files +
            git_status.untracked_files
        )
        modified_artifacts = []
        for file_path in all_modified_files:
            artifact_id = self._path_to_artifact_id(file_path)
            if artifact_id:
                modified_artifacts.append(artifact_id)

        # Run tier1 validation
        tier1 = self._run_tier1_validation(modified_artifacts)

        return WorkspaceState(
            workspace_id=workspace_id,
            user_id=metadata.user_id,
            branch=metadata.branch,
            base_commit=metadata.base_commit,
            is_dirty=git_status.is_dirty,
            modified_artifacts=modified_artifacts,
            modified_files=all_modified_files,
            tier1=tier1,
            last_touched=metadata.last_touched,
            expires_at=metadata.expires_at,
        )

    def _run_tier1_validation(self, modified_artifacts: List[str]) -> Tier1Report:
        """
        Run tier 1 validation on modified artifacts.

        Tier 1 rules run continuously and block commit.

        Args:
            modified_artifacts: List of modified artifact IDs

        Returns:
            Tier1Report
        """
        results = []
        all_passed = True

        # Get unique doc types from modified artifacts
        doc_types_to_validate = set()
        for artifact_id in modified_artifacts:
            try:
                parsed = self._parse_artifact_id(artifact_id)
                if parsed["scope"] == "doctype":
                    doc_types_to_validate.add((parsed["name"], parsed["version"]))
            except ArtifactIdError:
                continue

        # Validate each affected package
        for doc_type_id, version in doc_types_to_validate:
            package_path = (
                self._git.config_path /
                "document_types" /
                doc_type_id /
                "releases" /
                version
            )

            if package_path.exists():
                report = self._validator.validate_package(package_path)

                for error in report.errors:
                    results.append(Tier1Result(
                        rule_id=error.rule_id,
                        status="fail",
                        message=error.message,
                        artifact_id=f"doctype:{doc_type_id}:{version}:manifest",
                    ))
                    all_passed = False

                if report.valid:
                    results.append(Tier1Result(
                        rule_id="PACKAGE_VALID",
                        status="pass",
                        artifact_id=f"doctype:{doc_type_id}:{version}:manifest",
                    ))

        # If no packages to validate, report clean
        if not doc_types_to_validate:
            results.append(Tier1Result(
                rule_id="NO_PACKAGES_MODIFIED",
                status="pass",
            ))

        return Tier1Report(passed=all_passed, results=results)

    # =========================================================================
    # Artifact Operations
    # =========================================================================

    def get_artifact(self, workspace_id: str, artifact_id: str) -> ArtifactContent:
        """
        Get artifact content.

        Args:
            workspace_id: Workspace identifier
            artifact_id: Artifact identifier

        Returns:
            ArtifactContent
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Convert artifact ID to path
        try:
            file_path = self._artifact_id_to_path(artifact_id)
        except ArtifactIdError as e:
            raise ArtifactError(str(e))

        # Read file content
        full_path = self._git.config_path / file_path
        if not full_path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {artifact_id}")

        content = full_path.read_text(encoding="utf-8")
        parsed = self._parse_artifact_id(artifact_id)

        return ArtifactContent(
            artifact_id=artifact_id,
            content=content,
            version=parsed["version"],
        )

    def write_artifact(
        self,
        workspace_id: str,
        artifact_id: str,
        content: str,
    ) -> Tier1Report:
        """
        Write artifact content.

        Auto-saves to the filesystem. Returns tier1 validation result.

        Args:
            workspace_id: Workspace identifier
            artifact_id: Artifact identifier
            content: New content

        Returns:
            Tier1Report for the write
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Convert artifact ID to path
        try:
            file_path = self._artifact_id_to_path(artifact_id)
        except ArtifactIdError as e:
            raise ArtifactError(str(e))

        # Write file content
        full_path = self._git.config_path / file_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(content, encoding="utf-8")

        # Run tier1 validation on affected artifacts
        return self._run_tier1_validation([artifact_id])

    def get_preview(
        self,
        workspace_id: str,
        artifact_id: str,
        mode: str = "execution",
    ) -> PreviewResult:
        """
        Get preview of resolved prompt.

        Args:
            workspace_id: Workspace identifier
            artifact_id: Artifact identifier (must be a task_prompt)
            mode: Preview mode ("execution")

        Returns:
            PreviewResult with resolved prompt and provenance
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Parse artifact ID
        try:
            parsed = self._parse_artifact_id(artifact_id)
        except ArtifactIdError as e:
            raise ArtifactError(str(e))

        if parsed["scope"] != "doctype":
            raise ArtifactError("Preview only supported for doctype artifacts")

        doc_type_id = parsed["name"]
        version = parsed["version"]

        # Invalidate cache to get fresh data
        self._loader.invalidate_cache()

        # Load package and assemble prompt
        try:
            package = self._loader.get_document_type(doc_type_id, version)
        except PackageNotFoundError as e:
            raise ArtifactError(f"Package not found: {e}")

        resolved_prompt = self._loader.assemble_prompt(package)
        if not resolved_prompt:
            raise ArtifactError("Failed to assemble prompt")

        # Build provenance
        role_ref = package.role_prompt_ref
        provenance = PreviewProvenance(
            role=role_ref if role_ref else None,
            schema=f"{doc_type_id}@{version}",
            package=f"{doc_type_id}@{version}",
        )

        return PreviewResult(
            resolved_prompt=resolved_prompt,
            provenance=provenance,
        )

    # =========================================================================
    # Commit Operations
    # =========================================================================

    def commit(
        self,
        workspace_id: str,
        message: str,
        actor_name: str,
        actor_id: Optional[str] = None,
    ) -> CommitResult:
        """
        Commit all changes in the workspace.

        Args:
            workspace_id: Workspace identifier
            message: Commit message
            actor_name: Name of the user performing the commit
            actor_id: Optional user ID for audit

        Returns:
            CommitResult
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Check tier1 validation
        state = self._get_workspace_state(workspace_id)
        if not state.tier1.passed:
            failing_rules = [r for r in state.tier1.results if r.status == "fail"]
            raise WorkspaceError(
                f"Cannot commit: Tier 1 validation failed. "
                f"Failing rules: {[r.rule_id for r in failing_rules]}"
            )

        # Stage all changes
        self._git.stage_all()

        # Build commit message with trailer
        full_message = message.strip()
        full_message += f"\n\nCombine-Actor: {actor_name}"
        if actor_id:
            full_message += f"\nCombine-Actor-Id: {actor_id}"
        full_message += "\nCombine-Intent: prompt-edit"

        # Commit
        try:
            commit = self._git.commit(full_message, actor_name)
        except GitServiceError as e:
            raise WorkspaceError(f"Commit failed: {e}")

        return CommitResult(
            commit_hash=commit.commit_hash,
            commit_hash_short=commit.commit_hash_short,
            message=message,
        )

    def discard(self, workspace_id: str) -> None:
        """
        Discard all uncommitted changes in the workspace.

        Args:
            workspace_id: Workspace identifier
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        try:
            self._git.discard_changes()
        except GitServiceError as e:
            raise WorkspaceError(f"Discard failed: {e}")

    # =========================================================================
    # TTL Cleanup
    # =========================================================================

    def cleanup_expired_workspaces(self) -> int:
        """
        Clean up expired workspaces.

        Should be called periodically (e.g., by a background task).

        Returns:
            Number of workspaces cleaned up
        """
        cleaned = 0
        now = datetime.utcnow()

        with self._lock:
            expired_ids = [
                ws_id for ws_id, metadata in self._workspaces.items()
                if now > metadata.expires_at
            ]

            for workspace_id in expired_ids:
                try:
                    self._cleanup_workspace(workspace_id)
                    cleaned += 1
                except Exception as e:
                    logger.error(f"Failed to clean up workspace {workspace_id}: {e}")

        return cleaned


# Module-level singleton
_service: Optional[WorkspaceService] = None


def get_workspace_service() -> WorkspaceService:
    """Get the singleton WorkspaceService instance."""
    global _service
    if _service is None:
        _service = WorkspaceService()
    return _service


def reset_workspace_service() -> None:
    """Reset the singleton (for testing)."""
    global _service
    _service = None

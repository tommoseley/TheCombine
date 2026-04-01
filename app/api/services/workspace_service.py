"""
Workspace Service for Admin Workbench.

Per ADR-044 WS-044-03, this service manages editing workspaces
for configuration artifacts with Git-integrated workflow.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional

from app.api.services.artifact_id_resolver import (
    ArtifactIdError,
    parse_artifact_id,
    artifact_id_to_path,
    path_to_artifact_id,
)
from app.api.services.release_manager import ReleaseUpdateError
from app.api.services.workspace_scaffolders import (
    ScaffoldError,
    ScaffoldNotFoundError,
    create_orchestration_workflow as _scaffold_create_orchestration_workflow,
    delete_orchestration_workflow as _scaffold_delete_orchestration_workflow,
    create_document_type as _scaffold_create_document_type,
    delete_document_type as _scaffold_delete_document_type,
    create_dcw_workflow as _scaffold_create_dcw_workflow,
    create_role_prompt as _scaffold_create_role_prompt,
    create_template as _scaffold_create_template,
    create_standalone_schema as _scaffold_create_standalone_schema,
)
from app.api.services.git_service import (
    GitService,
    GitServiceError,
    get_git_service,
)
from app.api.services.config_validator import (
    ConfigValidator,
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


# Re-export ArtifactIdError from the resolver module so existing
# imports from workspace_service continue to work.
ArtifactIdError = ArtifactIdError


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
class ArtifactDiff:
    """Diff for a single artifact."""
    artifact_id: str
    file_path: str
    status: str  # M=modified, A=added, D=deleted
    old_content: Optional[str]
    new_content: Optional[str]
    diff_content: str
    additions: int = 0
    deletions: int = 0


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
    # Artifact ID Parsing — delegates to artifact_id_resolver
    # =========================================================================

    _parse_artifact_id = staticmethod(parse_artifact_id)
    _artifact_id_to_path = staticmethod(artifact_id_to_path)
    _path_to_artifact_id = staticmethod(path_to_artifact_id)

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
            aid = path_to_artifact_id(file_path)
            if aid:
                modified_artifacts.append(aid)

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
        for aid in modified_artifacts:
            try:
                parsed = parse_artifact_id(aid)
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

        # Validate workflow artifacts
        workflows_to_validate = set()
        for aid in modified_artifacts:
            try:
                parsed = parse_artifact_id(aid)
                if parsed["scope"] == "workflow":
                    workflows_to_validate.add((parsed["name"], parsed["version"]))
            except ArtifactIdError:
                continue

        for workflow_id, version in workflows_to_validate:
            workflow_path = (
                self._git.config_path /
                "workflows" /
                workflow_id /
                "releases" /
                version /
                "definition.json"
            )

            if workflow_path.exists():
                import json as _json
                try:
                    with open(workflow_path, "r", encoding="utf-8-sig") as f:
                        raw = _json.load(f)

                    # Only validate graph-based workflows (ADR-039) with PlanValidator.
                    # Step-based orchestration workflows (workflow.v1) get JSON validity only.
                    if "nodes" in raw and "edges" in raw:
                        from app.domain.workflow.plan_validator import PlanValidator
                        plan_validator = PlanValidator()
                        result = plan_validator.validate(raw)

                        if not result.valid:
                            for error in result.errors:
                                results.append(Tier1Result(
                                    rule_id=error.code.value if hasattr(error.code, 'value') else str(error.code),
                                    status="fail",
                                    message=error.message,
                                    artifact_id=f"workflow:{workflow_id}:{version}:definition",
                                ))
                                all_passed = False
                        else:
                            results.append(Tier1Result(
                                rule_id="WORKFLOW_VALID",
                                status="pass",
                                artifact_id=f"workflow:{workflow_id}:{version}:definition",
                            ))
                    else:
                        results.append(Tier1Result(
                            rule_id="WORKFLOW_JSON_VALID",
                            status="pass",
                            artifact_id=f"workflow:{workflow_id}:{version}:definition",
                        ))
                except _json.JSONDecodeError as e:
                    results.append(Tier1Result(
                        rule_id="INVALID_JSON",
                        status="fail",
                        message=f"Invalid JSON: {e}",
                        artifact_id=f"workflow:{workflow_id}:{version}:definition",
                    ))
                    all_passed = False

        # If no packages or workflows to validate, report clean
        if not doc_types_to_validate and not workflows_to_validate:
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
            file_path = artifact_id_to_path(artifact_id)
        except ArtifactIdError as e:
            raise ArtifactError(str(e))

        # Read file content
        full_path = self._git.config_path / file_path
        if not full_path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {artifact_id}")

        content = full_path.read_text(encoding="utf-8")
        parsed = parse_artifact_id(artifact_id)

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
            file_path = artifact_id_to_path(artifact_id)
        except ArtifactIdError as e:
            raise ArtifactError(str(e))

        # Write file content
        full_path = self._git.config_path / file_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(content, encoding="utf-8")

        # Run tier1 validation on affected artifacts
        return self._run_tier1_validation([artifact_id])

    def get_diff(
        self,
        workspace_id: str,
        artifact_id: Optional[str] = None,
    ) -> List[ArtifactDiff]:
        """
        Get diff for workspace changes.

        Args:
            workspace_id: Workspace identifier
            artifact_id: Specific artifact or None for all changes

        Returns:
            List of ArtifactDiff objects
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Get file path if artifact_id specified
        file_path = None
        if artifact_id:
            try:
                file_path = artifact_id_to_path(artifact_id)
            except ArtifactIdError as e:
                raise ArtifactError(str(e))

        # Get diffs from git
        git_diffs = self._git.get_diff(file_path)

        # Convert to ArtifactDiff with content
        result = []
        for git_diff in git_diffs:
            # Try to map file path back to artifact ID
            mapped_artifact_id = path_to_artifact_id(git_diff.file_path)
            if artifact_id and mapped_artifact_id != artifact_id:
                continue

            # Get old content (from HEAD)
            old_content = self._git.get_file_content(git_diff.file_path, "HEAD")

            # Get new content (current workspace)
            new_content = None
            if git_diff.status != "D":
                full_path = self._git.config_path / git_diff.file_path
                if full_path.exists():
                    new_content = full_path.read_text(encoding="utf-8")

            result.append(ArtifactDiff(
                artifact_id=mapped_artifact_id or f"file:{git_diff.file_path}",
                file_path=git_diff.file_path,
                status=git_diff.status,
                old_content=old_content,
                new_content=new_content,
                diff_content=git_diff.diff_content,
                additions=git_diff.additions,
                deletions=git_diff.deletions,
            ))

        return result

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
            parsed = parse_artifact_id(artifact_id)
        except ArtifactIdError as e:
            raise ArtifactError(str(e))

        if parsed["scope"] != "doctype":
            raise ArtifactError("Preview only supported for doctype artifacts")

        doc_type_id = parsed["name"]
        version = parsed["version"]
        kind = parsed["kind"]

        # Invalidate cache to get fresh data
        self._loader.invalidate_cache()

        # Load package
        try:
            package = self._loader.get_document_type(doc_type_id, version)
        except PackageNotFoundError as e:
            raise ArtifactError(f"Package not found: {e}")

        # Assemble prompt based on artifact kind
        if kind == "task_prompt":
            resolved_prompt = self._loader.assemble_prompt(package)
            prompt_type = "Task"
        elif kind == "qa_prompt":
            resolved_prompt = self._loader.assemble_qa_prompt(package)
            prompt_type = "QA"
        elif kind == "pgc_context":
            resolved_prompt = self._loader.assemble_pgc_prompt(package)
            prompt_type = "PGC Context"
        elif kind == "reflection_prompt":
            resolved_prompt = self._loader.assemble_reflection_prompt(package)
            prompt_type = "Reflection"
        else:
            raise ArtifactError(f"Preview not supported for artifact kind: {kind}")

        if not resolved_prompt:
            raise ArtifactError(f"Failed to assemble {prompt_type} prompt - content not available")

        # Build provenance - use appropriate role based on artifact kind
        if kind == "task_prompt":
            role_ref = package.role_prompt_ref
        elif kind in ("qa_prompt", "reflection_prompt"):
            # QA and Reflection use the quality_assurance role
            role_ref = "prompt:role:quality_assurance:1.0.0"
        else:
            # PGC context doesn't have a role
            role_ref = None

        provenance = PreviewProvenance(
            role=role_ref,
            schema=f"{doc_type_id}@{version}" if kind == "task_prompt" else None,
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
    # Scaffolding Operations — delegates to workspace_scaffolders
    # =========================================================================

    def _require_workspace(self, workspace_id: str) -> None:
        """Verify workspace exists and touch it."""
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")
        self._touch_workspace(workspace_id)

    def create_orchestration_workflow(
        self,
        workspace_id: str,
        workflow_id: str,
        name: Optional[str] = None,
        version: str = "1.0.0",
        pow_class: str = "template",
        derived_from: Optional[Dict[str, str]] = None,
        source_version: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new orchestration workflow definition."""
        self._require_workspace(workspace_id)
        try:
            return _scaffold_create_orchestration_workflow(
                config_path=self._git.config_path,
                workflow_id=workflow_id,
                name=name,
                version=version,
                pow_class=pow_class,
                derived_from=derived_from,
                source_version=source_version,
                tags=tags,
            )
        except (ScaffoldError, ScaffoldNotFoundError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def delete_orchestration_workflow(
        self,
        workspace_id: str,
        workflow_id: str,
    ) -> None:
        """Delete an orchestration workflow."""
        self._require_workspace(workspace_id)
        try:
            _scaffold_delete_orchestration_workflow(
                config_path=self._git.config_path,
                workflow_id=workflow_id,
            )
        except ScaffoldNotFoundError as e:
            raise ArtifactNotFoundError(str(e))
        except (ScaffoldError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def create_document_type(
        self,
        workspace_id: str,
        doc_type_id: str,
        display_name: Optional[str] = None,
        version: str = "1.0.0",
        scope: str = "project",
        role_ref: str = "prompt:role:technical_architect:1.0.0",
    ) -> str:
        """Create a new document type definition (DCW)."""
        self._require_workspace(workspace_id)
        try:
            return _scaffold_create_document_type(
                config_path=self._git.config_path,
                doc_type_id=doc_type_id,
                display_name=display_name,
                version=version,
                scope=scope,
                role_ref=role_ref,
            )
        except (ScaffoldError, ScaffoldNotFoundError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def delete_document_type(
        self,
        workspace_id: str,
        doc_type_id: str,
    ) -> None:
        """Delete a document type definition."""
        self._require_workspace(workspace_id)
        try:
            _scaffold_delete_document_type(
                config_path=self._git.config_path,
                doc_type_id=doc_type_id,
            )
        except ScaffoldNotFoundError as e:
            raise ArtifactNotFoundError(str(e))
        except (ScaffoldError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def create_dcw_workflow(
        self,
        workspace_id: str,
        doc_type_id: str,
        version: str = "1.0.0",
    ) -> str:
        """Create a graph-based workflow definition for a document type."""
        self._require_workspace(workspace_id)
        try:
            return _scaffold_create_dcw_workflow(
                config_path=self._git.config_path,
                doc_type_id=doc_type_id,
                version=version,
            )
        except (ScaffoldError, ScaffoldNotFoundError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def create_role_prompt(
        self,
        workspace_id: str,
        role_id: str,
        name: Optional[str] = None,
        version: str = "1.0.0",
    ) -> str:
        """Create a new role prompt."""
        self._require_workspace(workspace_id)
        try:
            return _scaffold_create_role_prompt(
                config_path=self._git.config_path,
                role_id=role_id,
                name=name,
                version=version,
            )
        except (ScaffoldError, ScaffoldNotFoundError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def create_template(
        self,
        workspace_id: str,
        template_id: str,
        name: Optional[str] = None,
        purpose: str = "general",
        version: str = "1.0.0",
    ) -> str:
        """Create a new template."""
        self._require_workspace(workspace_id)
        try:
            return _scaffold_create_template(
                config_path=self._git.config_path,
                template_id=template_id,
                name=name,
                purpose=purpose,
                version=version,
            )
        except (ScaffoldError, ScaffoldNotFoundError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

    def create_standalone_schema(
        self,
        workspace_id: str,
        schema_id: str,
        title: Optional[str] = None,
        version: str = "1.0.0",
    ) -> str:
        """Create a new standalone schema."""
        self._require_workspace(workspace_id)
        try:
            return _scaffold_create_standalone_schema(
                config_path=self._git.config_path,
                schema_id=schema_id,
                title=title,
                version=version,
            )
        except (ScaffoldError, ScaffoldNotFoundError, ReleaseUpdateError) as e:
            raise ArtifactError(str(e))

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

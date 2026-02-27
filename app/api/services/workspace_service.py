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
from threading import Lock
from typing import Dict, List, Optional

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
    # Artifact ID Parsing
    # =========================================================================

    def _parse_artifact_id(self, artifact_id: str) -> Dict[str, str]:
        """
        Parse artifact ID into components.

        Format: {scope}:{name}:{version}:{kind}

        Special case for fragments:
        Format: fragment:{frag_kind}:{frag_id}:{version}:{kind}
        Example: fragment:role:technical_architect:1.0.0:content
        The name becomes "{frag_kind}:{frag_id}" (e.g., "role:technical_architect")

        Examples:
        - doctype:project_discovery:1.4.0:task_prompt
        - role:technical_architect:1.0.0:role_prompt
        - template:document_generator:1.0.0:template
        - fragment:role:technical_architect:1.0.0:content

        Returns:
            Dict with scope, name, version, kind
        """
        parts = artifact_id.split(":")

        # Handle fragment scope specially - it has 5 parts
        # fragment:{frag_kind}:{frag_id}:{version}:{kind}
        if len(parts) == 5 and parts[0] == "fragment":
            scope = parts[0]
            name = f"{parts[1]}:{parts[2]}"  # e.g., "role:technical_architect"
            version = parts[3]
            kind = parts[4]
        elif len(parts) == 4:
            scope, name, version, kind = parts
        else:
            raise ArtifactIdError(
                f"Invalid artifact ID format: {artifact_id}. "
                f"Expected {{scope}}:{{name}}:{{version}}:{{kind}}"
            )

        if scope not in ("doctype", "role", "template", "workflow", "fragment", "schema"):
            raise ArtifactIdError(
                f"Invalid scope '{scope}' in artifact ID. "
                f"Expected: doctype, role, template, workflow, fragment, or schema"
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
                "package": "package.yaml",  # alias for manifest
            }
            if kind not in kind_to_file:
                raise ArtifactIdError(f"Unknown artifact kind for doctype: {kind}")
            return f"document_types/{name}/releases/{version}/{kind_to_file[kind]}"

        elif scope == "role":
            if kind != "role_prompt":
                raise ArtifactIdError(f"Unknown artifact kind for role: {kind}")
            return f"prompts/roles/{name}/releases/{version}/role.prompt.txt"

        elif scope == "template":
            if kind == "template":
                return f"prompts/templates/{name}/releases/{version}/template.txt"
            elif kind == "meta":
                return f"prompts/templates/{name}/releases/{version}/meta.yaml"
            else:
                raise ArtifactIdError(f"Unknown artifact kind for template: {kind}")

        elif scope == "workflow":
            if kind != "definition":
                raise ArtifactIdError(f"Unknown artifact kind for workflow: {kind}")
            return f"workflows/{name}/releases/{version}/definition.json"

        elif scope == "fragment":
            # Fragment artifacts - name format: {kind}:{doc_type_or_role_id}
            # e.g., fragment:role:technical_architect:1.0.0:content
            #       fragment:task:project_discovery:1.0.0:content
            frag_parts = name.split(":", 1)
            if len(frag_parts) != 2:
                raise ArtifactIdError(
                    f"Invalid fragment name format: {name}. "
                    f"Expected {{kind}}:{{id}} (e.g., role:technical_architect)"
                )
            frag_kind, frag_id = frag_parts

            if frag_kind == "role":
                if kind == "content":
                    return f"prompts/roles/{frag_id}/releases/{version}/role.prompt.txt"
                elif kind == "meta":
                    return f"prompts/roles/{frag_id}/releases/{version}/meta.yaml"
                else:
                    raise ArtifactIdError(f"Unknown artifact kind for role fragment: {kind}")
            elif frag_kind in ("task", "qa", "pgc", "questions", "reflection"):
                # These come from document type packages
                kind_to_file = {
                    "task": "prompts/task.prompt.txt",
                    "qa": "prompts/qa.prompt.txt",
                    "pgc": "prompts/pgc_context.prompt.txt",
                    "questions": "prompts/questions.prompt.txt",
                    "reflection": "prompts/reflection.prompt.txt",
                }
                if kind == "content":
                    return f"document_types/{frag_id}/releases/{version}/{kind_to_file[frag_kind]}"
                elif kind == "meta":
                    # Meta for doctype fragments stored alongside the prompt
                    return f"document_types/{frag_id}/releases/{version}/prompts/{frag_kind}.meta.yaml"
                else:
                    raise ArtifactIdError(f"Unknown artifact kind for {frag_kind} fragment: {kind}")
            else:
                raise ArtifactIdError(f"Unknown fragment kind: {frag_kind}")

        elif scope == "schema":
            # Standalone schema artifacts
            # e.g., schema:project_discovery:1.4.0:schema
            if kind != "schema":
                raise ArtifactIdError(f"Unknown artifact kind for schema: {kind}")
            return f"schemas/{name}/releases/{version}/schema.json"

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

        # Role prompts (both role: and fragment: formats)
        match = re.match(
            r"prompts/roles/([^/]+)/releases/([^/]+)/role\.prompt\.txt$",
            file_path
        )
        if match:
            return f"role:{match.group(1)}:{match.group(2)}:role_prompt"

        # Role meta.yaml
        match = re.match(
            r"prompts/roles/([^/]+)/releases/([^/]+)/meta\.yaml$",
            file_path
        )
        if match:
            return f"fragment:role:{match.group(1)}:{match.group(2)}:meta"

        # Templates
        match = re.match(
            r"prompts/templates/([^/]+)/releases/([^/]+)/template\.txt$",
            file_path
        )
        if match:
            return f"template:{match.group(1)}:{match.group(2)}:template"

        match = re.match(
            r"prompts/templates/([^/]+)/releases/([^/]+)/meta\.yaml$",
            file_path
        )
        if match:
            return f"template:{match.group(1)}:{match.group(2)}:meta"

        # Workflow definitions
        match = re.match(
            r"workflows/([^/]+)/releases/([^/]+)/definition\.json$",
            file_path
        )
        if match:
            return f"workflow:{match.group(1)}:{match.group(2)}:definition"

        # Standalone schemas
        match = re.match(
            r"schemas/([^/]+)/releases/([^/]+)/schema\.json$",
            file_path
        )
        if match:
            return f"schema:{match.group(1)}:{match.group(2)}:schema"

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

        # Validate workflow artifacts
        workflows_to_validate = set()
        for artifact_id in modified_artifacts:
            try:
                parsed = self._parse_artifact_id(artifact_id)
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
                file_path = self._artifact_id_to_path(artifact_id)
            except ArtifactIdError as e:
                raise ArtifactError(str(e))

        # Get diffs from git
        git_diffs = self._git.get_diff(file_path)

        # Convert to ArtifactDiff with content
        result = []
        for git_diff in git_diffs:
            # Try to map file path back to artifact ID
            mapped_artifact_id = self._path_to_artifact_id(git_diff.file_path)
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
            parsed = self._parse_artifact_id(artifact_id)
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
    # Orchestration Workflow Lifecycle
    # =========================================================================

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
        """
        Create a new orchestration workflow definition.

        Creates the directory structure, skeleton definition.json,
        and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            workflow_id: Workflow ID (snake_case)
            name: Display name (auto-generated from workflow_id if None)
            version: Initial version
            pow_class: Classification (reference, template, instance)
            derived_from: Source workflow reference {workflow_id, version}
            source_version: Version of source at fork time
            tags: Free-form classification tags

        Returns:
            Artifact ID for the new workflow
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Validate workflow_id
        if not re.match(r'^[a-z][a-z0-9_]*$', workflow_id):
            raise ArtifactError(
                f"Invalid workflow_id: '{workflow_id}'. "
                f"Must match pattern: ^[a-z][a-z0-9_]*$"
            )

        # Check if workflow already exists
        workflow_dir = self._git.config_path / "workflows" / workflow_id
        if workflow_dir.exists():
            raise ArtifactError(f"Workflow already exists: {workflow_id}")

        # Auto-generate display name
        if not name:
            name = workflow_id.replace('_', ' ').title()

        # Create directory structure and definition.json
        import json as _json
        from datetime import date

        release_dir = workflow_dir / "releases" / version
        release_dir.mkdir(parents=True, exist_ok=True)

        skeleton = {
            "schema_version": "workflow.v2",
            "workflow_id": workflow_id,
            "revision": f"wfrev_{date.today().isoformat().replace('-', '_')}_a",
            "effective_date": date.today().isoformat(),
            "name": name,
            "description": "",
            "pow_class": pow_class,
            "derived_from": derived_from,
            "source_version": source_version,
            "tags": tags or [],
            "scopes": {
                "project": {"parent": None}
            },
            "document_types": {},
            "entity_types": {},
            "steps": []
        }

        definition_path = release_dir / "definition.json"
        definition_path.write_text(
            _json.dumps(skeleton, indent=2),
            encoding="utf-8",
        )

        # Update active_releases.json
        self._update_active_releases(workflow_id, version)

        return f"workflow:{workflow_id}:{version}:definition"

    def delete_orchestration_workflow(
        self,
        workspace_id: str,
        workflow_id: str,
    ) -> None:
        """
        Delete an orchestration workflow.

        Removes the workflow directory and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            workflow_id: Workflow ID to delete
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Verify workflow exists
        workflow_dir = self._git.config_path / "workflows" / workflow_id
        if not workflow_dir.exists():
            raise ArtifactNotFoundError(f"Workflow not found: {workflow_id}")

        # Verify it's step-based (not graph-based)
        import json as _json
        import shutil

        # Find any definition.json to check format
        for def_file in workflow_dir.rglob("definition.json"):
            try:
                with open(def_file, "r", encoding="utf-8-sig") as f:
                    raw = _json.load(f)
                if "nodes" in raw and "edges" in raw:
                    raise ArtifactError(
                        f"Cannot delete graph-based workflow '{workflow_id}' "
                        f"via this endpoint. Use the document type workflow editor."
                    )
            except _json.JSONDecodeError:
                pass
            break

        # Remove directory tree
        shutil.rmtree(workflow_dir)

        # Update active_releases.json
        self._update_active_releases(workflow_id, None)

    def _update_active_releases(
        self,
        workflow_id: str,
        version: Optional[str],
    ) -> None:
        """
        Update active_releases.json for a workflow.

        Args:
            workflow_id: Workflow ID
            version: Version to set, or None to remove
        """
        import json as _json

        releases_path = self._git.config_path / "_active" / "active_releases.json"
        if not releases_path.exists():
            raise ArtifactError("active_releases.json not found")

        with open(releases_path, "r", encoding="utf-8-sig") as f:
            releases = _json.load(f)

        if "workflows" not in releases:
            releases["workflows"] = {}

        if version is None:
            releases["workflows"].pop(workflow_id, None)
        else:
            releases["workflows"][workflow_id] = version

        releases_path.write_text(
            _json.dumps(releases, indent=2) + "\n",
            encoding="utf-8",
        )

    # =========================================================================
    # Document Type Lifecycle
    # =========================================================================

    def create_document_type(
        self,
        workspace_id: str,
        doc_type_id: str,
        display_name: Optional[str] = None,
        version: str = "1.0.0",
        scope: str = "project",
        role_ref: str = "prompt:role:technical_architect:1.0.0",
    ) -> str:
        """
        Create a new document type definition (DCW).

        Creates the directory structure, skeleton package.yaml,
        empty prompt files, and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            doc_type_id: Document type ID (snake_case)
            display_name: Display name (auto-generated from doc_type_id if None)
            version: Initial version
            scope: Scope level (project, epic, etc.)
            role_ref: Reference to role prompt

        Returns:
            Artifact ID for the new document type
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Validate doc_type_id
        if not re.match(r'^[a-z][a-z0-9_]*$', doc_type_id):
            raise ArtifactError(
                f"Invalid doc_type_id: '{doc_type_id}'. "
                f"Must match pattern: ^[a-z][a-z0-9_]*$"
            )

        # Check if document type already exists
        doc_type_dir = self._git.config_path / "document_types" / doc_type_id
        if doc_type_dir.exists():
            raise ArtifactError(f"Document type already exists: {doc_type_id}")

        # Auto-generate display name
        if not display_name:
            display_name = doc_type_id.replace('_', ' ').title()

        # Create directory structure
        import json as _json

        release_dir = doc_type_dir / "releases" / version
        prompts_dir = release_dir / "prompts"
        schemas_dir = release_dir / "schemas"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        schemas_dir.mkdir(parents=True, exist_ok=True)

        # Create package.yaml skeleton
        package_yaml = f"""# Document Type Package Manifest
# Schema: ../../../schemas/registry/package.schema.json

doc_type_id: {doc_type_id}
display_name: {display_name}
version: {version}

description: >
  TODO: Add description for this document type.

# Classification (per ADR-044)
authority_level: descriptive
creation_mode: llm_generated
production_mode: generate
scope: {scope}

# Dependencies
required_inputs: []
optional_inputs: []

# Shared artifact references
role_prompt_ref: "{role_ref}"
template_ref: "prompt:template:document_generator:1.0.0"
qa_template_ref: "prompt:template:qa_evaluator:1.0.0"
pgc_template_ref: "prompt:template:pgc_clarifier:1.0.0"
schema_ref: "schema:{doc_type_id}:{version}"

# Packaged artifacts (relative paths)
artifacts:
  task_prompt: prompts/task.prompt.txt
  qa_prompt: prompts/qa.prompt.txt
  pgc_context: prompts/pgc_context.prompt.txt
  schema: schemas/output.schema.json

# Test artifacts
tests:
  fixtures: []
  golden_traces: []

# UI configuration
ui:
  icon: document
  category: general
  display_order: 100
"""
        (release_dir / "package.yaml").write_text(package_yaml, encoding="utf-8")

        # Create skeleton prompt files
        task_prompt = f"""# Task Prompt for {display_name}

You are producing a {display_name} document.

## Instructions

TODO: Add task instructions here.

## Output Requirements

Produce a structured JSON document following the output schema.
"""
        (prompts_dir / "task.prompt.txt").write_text(task_prompt, encoding="utf-8")

        qa_prompt = f"""# QA Prompt for {display_name}

Evaluate the {display_name} document for quality and completeness.

## Evaluation Criteria

TODO: Add evaluation criteria here.
"""
        (prompts_dir / "qa.prompt.txt").write_text(qa_prompt, encoding="utf-8")

        pgc_prompt = f"""# PGC Context for {display_name}

Context for pre-generation clarification.

## Areas to Clarify

TODO: Add clarification areas here.
"""
        (prompts_dir / "pgc_context.prompt.txt").write_text(pgc_prompt, encoding="utf-8")

        # Create skeleton schema
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"schema:{doc_type_id}:{version}",
            "title": display_name,
            "description": f"Output schema for {display_name}",
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title"
                },
                "content": {
                    "type": "string",
                    "description": "Main content"
                }
            },
            "required": ["title", "content"]
        }
        (schemas_dir / "output.schema.json").write_text(
            _json.dumps(schema, indent=2),
            encoding="utf-8",
        )

        # Update active_releases.json
        self._update_active_releases_for_doc_type(doc_type_id, version)

        return f"doctype:{doc_type_id}:{version}:package"

    def delete_document_type(
        self,
        workspace_id: str,
        doc_type_id: str,
    ) -> None:
        """
        Delete a document type definition.

        Removes the document type directory and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            doc_type_id: Document type ID to delete
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Verify document type exists
        doc_type_dir = self._git.config_path / "document_types" / doc_type_id
        if not doc_type_dir.exists():
            raise ArtifactNotFoundError(f"Document type not found: {doc_type_id}")

        import shutil

        # Remove directory tree
        shutil.rmtree(doc_type_dir)

        # Update active_releases.json
        self._update_active_releases_for_doc_type(doc_type_id, None)

    def _update_active_releases_for_doc_type(
        self,
        doc_type_id: str,
        version: Optional[str],
    ) -> None:
        """
        Update active_releases.json for a document type.

        Args:
            doc_type_id: Document type ID
            version: Version to set, or None to remove
        """
        import json as _json

        releases_path = self._git.config_path / "_active" / "active_releases.json"
        if not releases_path.exists():
            raise ArtifactError("active_releases.json not found")

        with open(releases_path, "r", encoding="utf-8-sig") as f:
            releases = _json.load(f)

        if "document_types" not in releases:
            releases["document_types"] = {}
        if "schemas" not in releases:
            releases["schemas"] = {}

        if version is None:
            releases["document_types"].pop(doc_type_id, None)
            releases["schemas"].pop(doc_type_id, None)
        else:
            releases["document_types"][doc_type_id] = version
            releases["schemas"][doc_type_id] = version

        releases_path.write_text(
            _json.dumps(releases, indent=2) + "\n",
            encoding="utf-8",
        )

    # =========================================================================
    # DCW Workflow Lifecycle (Graph-based workflows for document types)
    # =========================================================================

    def create_dcw_workflow(
        self,
        workspace_id: str,
        doc_type_id: str,
        version: str = "1.0.0",
    ) -> str:
        """
        Create a graph-based workflow definition for a document type.

        Creates the workflow directory structure with a skeleton definition.json
        containing PGC, generation, QA, remediation nodes and standard edges.

        Args:
            workspace_id: Workspace identifier
            doc_type_id: Document type ID (must exist)
            version: Initial version

        Returns:
            Artifact ID for the new workflow
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Validate doc_type_id format
        if not re.match(r'^[a-z][a-z0-9_]*$', doc_type_id):
            raise ArtifactError(
                f"Invalid doc_type_id: '{doc_type_id}'. "
                f"Must match pattern: ^[a-z][a-z0-9_]*$"
            )

        # Verify document type exists
        doc_type_dir = self._git.config_path / "document_types" / doc_type_id
        if not doc_type_dir.exists():
            raise ArtifactError(f"Document type not found: {doc_type_id}")

        # Check if workflow already exists
        workflow_dir = self._git.config_path / "workflows" / doc_type_id
        if workflow_dir.exists():
            raise ArtifactError(f"Workflow already exists: {doc_type_id}")

        # Create display name
        display_name = doc_type_id.replace('_', ' ').title()

        # Create directory structure and definition.json
        import json as _json
        from datetime import date

        release_dir = workflow_dir / "releases" / version
        release_dir.mkdir(parents=True, exist_ok=True)

        skeleton = {
            "$schema": "https://thecombine.ai/schemas/workflow-plan.v1.json",
            "workflow_id": doc_type_id,
            "version": version,
            "name": f"{display_name} Workflow",
            "description": f"Document creation workflow for {display_name}",
            "scope_type": "document",
            "document_type": doc_type_id,
            "thread_ownership": {
                "owns_thread": False,
                "thread_purpose": None
            },
            "entry_node_ids": ["pgc"],
            "nodes": [
                {
                    "node_id": "pgc",
                    "type": "pgc",
                    "description": f"Pre-generation clarification for {display_name}",
                    "task_ref": "clarification_questions_generator",
                    "includes": {},
                    "_position": {"x": 50, "y": 40}
                },
                {
                    "node_id": "generation",
                    "type": "task",
                    "description": f"Generate {display_name} document",
                    "task_ref": "document_generator",
                    "includes": {},
                    "produces": doc_type_id,
                    "_position": {"x": -220, "y": 235}
                },
                {
                    "node_id": "qa",
                    "type": "qa",
                    "description": f"QA evaluation for {display_name}",
                    "task_ref": f"tasks/{display_name} QA v1.0",
                    "requires_qa": True,
                    "qa_mode": "semantic",
                    "_position": {"x": 65, "y": 390}
                },
                {
                    "node_id": "remediation",
                    "type": "task",
                    "description": f"Rework {display_name} based on QA feedback",
                    "task_ref": "document_generator",
                    "includes": {},
                    "produces": doc_type_id,
                    "_position": {"x": 50, "y": 200}
                },
                {
                    "node_id": "end_complete",
                    "type": "end",
                    "description": f"{display_name} document ready",
                    "terminal_outcome": "stabilized",
                    "gate_outcome": "complete",
                    "_position": {"x": -160, "y": 800}
                },
                {
                    "node_id": "end_failed",
                    "type": "end",
                    "description": "Generation failed",
                    "terminal_outcome": "blocked",
                    "gate_outcome": "failed",
                    "_position": {"x": 190, "y": 800}
                }
            ],
            "edges": [
                {
                    "edge_id": "pgc_to_generation",
                    "from_node_id": "pgc",
                    "to_node_id": "generation",
                    "outcome": "success",
                    "label": "Clarification complete, proceed to generation",
                    "kind": "auto"
                },
                {
                    "edge_id": "pgc_needs_answers",
                    "from_node_id": "pgc",
                    "to_node_id": None,
                    "outcome": "needs_user_input",
                    "label": "User must answer clarification questions",
                    "kind": "auto",
                    "non_advancing": True
                },
                {
                    "edge_id": "generation_to_qa",
                    "from_node_id": "generation",
                    "to_node_id": "qa",
                    "outcome": "success",
                    "label": "Document generated, run QA",
                    "kind": "auto"
                },
                {
                    "edge_id": "generation_failed",
                    "from_node_id": "generation",
                    "to_node_id": "end_failed",
                    "outcome": "failed",
                    "label": "Document generation failed",
                    "kind": "auto"
                },
                {
                    "edge_id": "qa_pass",
                    "from_node_id": "qa",
                    "to_node_id": "end_complete",
                    "outcome": "success",
                    "label": "QA passed - document complete",
                    "kind": "auto"
                },
                {
                    "edge_id": "qa_fail_remediate",
                    "from_node_id": "qa",
                    "to_node_id": "remediation",
                    "outcome": "failed",
                    "label": "QA failed, remediate",
                    "kind": "auto",
                    "conditions": [{"type": "retry_count", "operator": "lt", "value": 2}]
                },
                {
                    "edge_id": "qa_fail_circuit_breaker",
                    "from_node_id": "qa",
                    "to_node_id": "end_failed",
                    "outcome": "failed",
                    "label": "QA failed, circuit breaker",
                    "kind": "auto",
                    "conditions": [{"type": "retry_count", "operator": "gte", "value": 2}]
                },
                {
                    "edge_id": "remediation_to_qa",
                    "from_node_id": "remediation",
                    "to_node_id": "qa",
                    "outcome": "success",
                    "label": "Remediation complete, re-run QA",
                    "kind": "auto"
                },
                {
                    "edge_id": "remediation_failed",
                    "from_node_id": "remediation",
                    "to_node_id": "end_failed",
                    "outcome": "failed",
                    "label": "Remediation failed",
                    "kind": "auto"
                }
            ],
            "governance": {
                "adr_references": [],
                "design_principles": [
                    "Auto-complete on QA pass",
                    "PGC clarification before generation"
                ],
                "circuit_breaker": {
                    "max_retries": 2,
                    "applies_to": ["qa", "remediation"],
                    "on_trip": "end_failed with internal error flag"
                }
            },
            "metadata": {
                "created_date": date.today().isoformat(),
                "updated_date": date.today().isoformat(),
                "changelog": [f"v{version}: Initial workflow created"]
            },
            "requires_inputs": []
        }

        definition_path = release_dir / "definition.json"
        definition_path.write_text(
            _json.dumps(skeleton, indent=2),
            encoding="utf-8",
        )

        # Update active_releases.json
        self._update_active_releases(doc_type_id, version)

        return f"workflow:{doc_type_id}:{version}:definition"

    # =========================================================================
    # Prompt Fragment Lifecycle (Role prompts)
    # =========================================================================

    def create_role_prompt(
        self,
        workspace_id: str,
        role_id: str,
        name: Optional[str] = None,
        version: str = "1.0.0",
    ) -> str:
        """
        Create a new role prompt.

        Creates the directory structure, skeleton role.prompt.txt,
        meta.yaml, and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            role_id: Role ID (snake_case)
            name: Display name (auto-generated if None)
            version: Initial version

        Returns:
            Artifact ID for the new role
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Validate role_id
        if not re.match(r'^[a-z][a-z0-9_]*$', role_id):
            raise ArtifactError(
                f"Invalid role_id: '{role_id}'. "
                f"Must match pattern: ^[a-z][a-z0-9_]*$"
            )

        # Check if role already exists
        role_dir = self._git.config_path / "prompts" / "roles" / role_id
        if role_dir.exists():
            raise ArtifactError(f"Role already exists: {role_id}")

        # Auto-generate display name
        if not name:
            name = role_id.replace('_', ' ').title()

        # Create directory structure
        import yaml as _yaml

        release_dir = role_dir / "releases" / version
        release_dir.mkdir(parents=True, exist_ok=True)

        # Create skeleton role prompt
        role_prompt = f"""# {name} Role Prompt

You are a {name.lower()}.

## Responsibilities

TODO: Define the role's responsibilities.

## Constraints

TODO: Define any constraints or guidelines.

## Output Style

TODO: Define the expected output style.
"""
        (release_dir / "role.prompt.txt").write_text(role_prompt, encoding="utf-8")

        # Create meta.yaml
        meta_content = _yaml.dump({
            "name": name,
            "intent": None,
            "tags": [],
        }, default_flow_style=False)
        (release_dir / "meta.yaml").write_text(meta_content, encoding="utf-8")

        # Update active_releases.json
        self._update_active_releases_for_role(role_id, version)

        return f"role:{role_id}:{version}:role_prompt"

    def _update_active_releases_for_role(
        self,
        role_id: str,
        version: Optional[str],
    ) -> None:
        """Update active_releases.json for a role."""
        import json as _json

        releases_path = self._git.config_path / "_active" / "active_releases.json"
        if not releases_path.exists():
            raise ArtifactError("active_releases.json not found")

        with open(releases_path, "r", encoding="utf-8-sig") as f:
            releases = _json.load(f)

        if "roles" not in releases:
            releases["roles"] = {}

        if version is None:
            releases["roles"].pop(role_id, None)
        else:
            releases["roles"][role_id] = version

        releases_path.write_text(
            _json.dumps(releases, indent=2) + "\n",
            encoding="utf-8",
        )

    # =========================================================================
    # Template Lifecycle
    # =========================================================================

    def create_template(
        self,
        workspace_id: str,
        template_id: str,
        name: Optional[str] = None,
        purpose: str = "general",
        version: str = "1.0.0",
    ) -> str:
        """
        Create a new template.

        Creates the directory structure, skeleton template.txt,
        meta.yaml, and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            template_id: Template ID (snake_case)
            name: Display name (auto-generated if None)
            purpose: Template purpose (document, qa, pgc, general)
            version: Initial version

        Returns:
            Artifact ID for the new template
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Validate template_id
        if not re.match(r'^[a-z][a-z0-9_]*$', template_id):
            raise ArtifactError(
                f"Invalid template_id: '{template_id}'. "
                f"Must match pattern: ^[a-z][a-z0-9_]*$"
            )

        # Check if template already exists
        template_dir = self._git.config_path / "prompts" / "templates" / template_id
        if template_dir.exists():
            raise ArtifactError(f"Template already exists: {template_id}")

        # Auto-generate display name
        if not name:
            name = template_id.replace('_', ' ').title()

        # Create directory structure
        import yaml as _yaml

        release_dir = template_dir / "releases" / version
        release_dir.mkdir(parents=True, exist_ok=True)

        # Create skeleton template
        template_content = f"""# {name} Template

$$ROLE_PROMPT

---

$$TASK_PROMPT

---

## Output Schema

$$OUTPUT_SCHEMA

---

Please produce a response conforming to the output schema.
"""
        (release_dir / "template.txt").write_text(template_content, encoding="utf-8")

        # Create meta.yaml
        meta_content = _yaml.dump({
            "name": name,
            "purpose": purpose,
            "use_case": None,
        }, default_flow_style=False)
        (release_dir / "meta.yaml").write_text(meta_content, encoding="utf-8")

        # Update active_releases.json
        self._update_active_releases_for_template(template_id, version)

        return f"template:{template_id}:{version}:template"

    def _update_active_releases_for_template(
        self,
        template_id: str,
        version: Optional[str],
    ) -> None:
        """Update active_releases.json for a template."""
        import json as _json

        releases_path = self._git.config_path / "_active" / "active_releases.json"
        if not releases_path.exists():
            raise ArtifactError("active_releases.json not found")

        with open(releases_path, "r", encoding="utf-8-sig") as f:
            releases = _json.load(f)

        if "templates" not in releases:
            releases["templates"] = {}

        if version is None:
            releases["templates"].pop(template_id, None)
        else:
            releases["templates"][template_id] = version

        releases_path.write_text(
            _json.dumps(releases, indent=2) + "\n",
            encoding="utf-8",
        )

    # =========================================================================
    # Standalone Schema Lifecycle
    # =========================================================================

    def create_standalone_schema(
        self,
        workspace_id: str,
        schema_id: str,
        title: Optional[str] = None,
        version: str = "1.0.0",
    ) -> str:
        """
        Create a new standalone schema.

        Creates the directory structure, skeleton schema.json,
        and updates active_releases.json.

        Args:
            workspace_id: Workspace identifier
            schema_id: Schema ID (snake_case)
            title: Schema title (auto-generated if None)
            version: Initial version

        Returns:
            Artifact ID for the new schema
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace not found: {workspace_id}")

        self._touch_workspace(workspace_id)

        # Validate schema_id
        if not re.match(r'^[a-z][a-z0-9_]*$', schema_id):
            raise ArtifactError(
                f"Invalid schema_id: '{schema_id}'. "
                f"Must match pattern: ^[a-z][a-z0-9_]*$"
            )

        # Check if schema already exists
        schema_dir = self._git.config_path / "schemas" / schema_id
        if schema_dir.exists():
            raise ArtifactError(f"Schema already exists: {schema_id}")

        # Auto-generate title
        if not title:
            title = schema_id.replace('_', ' ').title()

        # Create directory structure
        import json as _json

        release_dir = schema_dir / "releases" / version
        release_dir.mkdir(parents=True, exist_ok=True)

        # Create skeleton schema
        schema_content = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"schema:{schema_id}:{version}",
            "title": title,
            "description": f"Schema for {title}",
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Main content"
                }
            },
            "required": ["content"]
        }
        (release_dir / "schema.json").write_text(
            _json.dumps(schema_content, indent=2),
            encoding="utf-8",
        )

        # Update active_releases.json
        self._update_active_releases_for_schema(schema_id, version)

        return f"schema:{schema_id}:{version}:schema"

    def _update_active_releases_for_schema(
        self,
        schema_id: str,
        version: Optional[str],
    ) -> None:
        """Update active_releases.json for a standalone schema."""
        import json as _json

        releases_path = self._git.config_path / "_active" / "active_releases.json"
        if not releases_path.exists():
            raise ArtifactError("active_releases.json not found")

        with open(releases_path, "r", encoding="utf-8-sig") as f:
            releases = _json.load(f)

        if "schemas" not in releases:
            releases["schemas"] = {}

        if version is None:
            releases["schemas"].pop(schema_id, None)
        else:
            releases["schemas"][schema_id] = version

        releases_path.write_text(
            _json.dumps(releases, indent=2) + "\n",
            encoding="utf-8",
        )

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

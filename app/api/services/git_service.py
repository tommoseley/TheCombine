"""
Git Service for Admin Workbench.

Per ADR-044 Addendum A, Git operations are first-class UX primitives.
This service provides controlled Git operations for the Admin Workbench.
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default path to the Git repository root (TheCombine)
# combine-config is a subdirectory within this repo
DEFAULT_REPO_PATH = Path(__file__).parent.parent.parent.parent

# Path prefix for combine-config within the repo
COMBINE_CONFIG_PREFIX = "combine-config"

# Service account for Git commits
GIT_AUTHOR_NAME = "Combine Config Bot"
GIT_AUTHOR_EMAIL = "config-bot@thecombine.ai"


class GitServiceError(Exception):
    """Error during Git operation."""
    pass


class GitValidationError(GitServiceError):
    """Validation failed before Git operation."""
    pass


class GitConflictError(GitServiceError):
    """Git operation blocked due to conflict or invalid state."""
    pass


@dataclass
class GitStatus:
    """Current Git workspace status."""
    branch: str
    base_commit: str
    base_commit_short: str
    is_dirty: bool
    modified_files: List[str] = field(default_factory=list)
    added_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)


@dataclass
class GitDiff:
    """Diff information for a file."""
    file_path: str
    status: str  # M=modified, A=added, D=deleted
    diff_content: str
    additions: int = 0
    deletions: int = 0


@dataclass
class GitCommit:
    """Information about a Git commit."""
    commit_hash: str
    commit_hash_short: str
    author: str
    date: datetime
    message: str


@dataclass
class GitBranch:
    """Information about a Git branch."""
    name: str
    commit_hash: str
    is_current: bool
    is_remote: bool = False


class GitService:
    """
    Service for Git operations in the Admin Workbench.

    Operations are scoped to the combine-config directory within the main repository.
    Git operations are executed via subprocess for safety and isolation.
    """

    def __init__(self, repo_path: Optional[Path] = None, config_prefix: str = COMBINE_CONFIG_PREFIX):
        """
        Initialize the Git service.

        Args:
            repo_path: Path to the Git repository root.
            config_prefix: Path prefix for combine-config within the repo.
        """
        self.repo_path = repo_path or DEFAULT_REPO_PATH
        self.config_prefix = config_prefix

        if not self.repo_path.exists():
            raise GitServiceError(f"Repository path does not exist: {self.repo_path}")

        if not (self.repo_path / ".git").exists():
            raise GitServiceError(f"Not a Git repository: {self.repo_path}")

        # Verify combine-config directory exists
        self.config_path = self.repo_path / config_prefix
        if not self.config_path.exists():
            raise GitServiceError(f"Config directory does not exist: {self.config_path}")

    def _prefix_path(self, path: str) -> str:
        """Add combine-config prefix to a path if not already prefixed."""
        if path.startswith(self.config_prefix + "/") or path.startswith(self.config_prefix + "\\"):
            return path
        return f"{self.config_prefix}/{path}"

    def _strip_prefix(self, path: str) -> str:
        """Remove combine-config prefix from a path."""
        prefix = self.config_prefix + "/"
        if path.startswith(prefix):
            return path[len(prefix):]
        return path

    def _run_git(
        self,
        *args: str,
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a Git command.

        Args:
            *args: Git command arguments
            capture_output: Capture stdout/stderr
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result
        """
        cmd = ["git", *args]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=check,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": GIT_AUTHOR_NAME,
                    "GIT_AUTHOR_EMAIL": GIT_AUTHOR_EMAIL,
                    "GIT_COMMITTER_NAME": GIT_AUTHOR_NAME,
                    "GIT_COMMITTER_EMAIL": GIT_AUTHOR_EMAIL,
                },
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.error(f"stderr: {e.stderr}")
            raise GitServiceError(f"Git command failed: {e.stderr}")

    # =========================================================================
    # Status & Information
    # =========================================================================

    def get_status(self) -> GitStatus:
        """
        Get current Git workspace status.

        Returns:
            GitStatus with branch, commit, and file changes
            (filtered to combine-config directory only)
        """
        # Get current branch
        branch_result = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        branch = branch_result.stdout.strip()

        # Get current commit
        commit_result = self._run_git("rev-parse", "HEAD")
        base_commit = commit_result.stdout.strip()
        base_commit_short = base_commit[:7]

        # Get status (filtered to combine-config)
        status_result = self._run_git("status", "--porcelain", "--", self.config_prefix)

        modified_files = []
        added_files = []
        deleted_files = []
        untracked_files = []

        for line in status_result.stdout.strip().split("\n"):
            if not line:
                continue

            status_code = line[:2]
            file_path = line[3:]

            # Strip the combine-config prefix for display
            display_path = self._strip_prefix(file_path)

            if status_code.startswith("M") or status_code.endswith("M"):
                modified_files.append(display_path)
            elif status_code.startswith("A"):
                added_files.append(display_path)
            elif status_code.startswith("D"):
                deleted_files.append(display_path)
            elif status_code.startswith("?"):
                untracked_files.append(display_path)

        is_dirty = bool(modified_files or added_files or deleted_files or untracked_files)

        return GitStatus(
            branch=branch,
            base_commit=base_commit,
            base_commit_short=base_commit_short,
            is_dirty=is_dirty,
            modified_files=modified_files,
            added_files=added_files,
            deleted_files=deleted_files,
            untracked_files=untracked_files,
        )

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> List[GitDiff]:
        """
        Get diff for files in combine-config.

        Args:
            file_path: Specific file (relative to combine-config) or None for all
            staged: Show staged changes instead of unstaged

        Returns:
            List of GitDiff objects
        """
        # Build path argument - either specific file or all of combine-config
        if file_path:
            target_path = self._prefix_path(file_path)
        else:
            target_path = self.config_prefix

        # Get file-by-file diffs
        diff_args = ["diff", "--name-status"]
        if staged:
            diff_args.append("--staged")
        diff_args.extend(["--", target_path])

        name_status = self._run_git(*diff_args)

        diffs = []
        for line in name_status.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) >= 2:
                status = parts[0]
                path = parts[1]

                # Get individual file diff
                file_diff_args = ["diff"]
                if staged:
                    file_diff_args.append("--staged")
                file_diff_args.extend(["--", path])

                try:
                    file_diff = self._run_git(*file_diff_args)
                    diff_content = file_diff.stdout
                except GitServiceError:
                    diff_content = ""

                # Count additions/deletions
                additions = diff_content.count("\n+") - diff_content.count("\n+++")
                deletions = diff_content.count("\n-") - diff_content.count("\n---")

                # Strip prefix for display
                display_path = self._strip_prefix(path)

                diffs.append(GitDiff(
                    file_path=display_path,
                    status=status,
                    diff_content=diff_content,
                    additions=max(0, additions),
                    deletions=max(0, deletions),
                ))

        return diffs

    def get_file_content(self, file_path: str, ref: str = "HEAD") -> Optional[str]:
        """
        Get file content at a specific ref.

        Args:
            file_path: Path to file (relative to combine-config)
            ref: Git ref (commit, branch, tag)

        Returns:
            File content or None if not found
        """
        try:
            full_path = self._prefix_path(file_path)
            result = self._run_git("show", f"{ref}:{full_path}")
            return result.stdout
        except GitServiceError:
            return None

    # =========================================================================
    # Branch Operations
    # =========================================================================

    def list_branches(self, include_remote: bool = False) -> List[GitBranch]:
        """
        List all branches.

        Args:
            include_remote: Include remote branches

        Returns:
            List of GitBranch objects
        """
        args = ["branch", "--format=%(refname:short)|%(objectname:short)|%(HEAD)"]
        if include_remote:
            args.append("-a")

        result = self._run_git(*args)

        branches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) >= 3:
                name = parts[0]
                commit = parts[1]
                is_current = parts[2] == "*"
                is_remote = name.startswith("remotes/")

                branches.append(GitBranch(
                    name=name,
                    commit_hash=commit,
                    is_current=is_current,
                    is_remote=is_remote,
                ))

        return branches

    def create_branch(self, branch_name: str, base_ref: str = "HEAD") -> GitBranch:
        """
        Create a new branch.

        Args:
            branch_name: Name for new branch
            base_ref: Base commit/branch/tag

        Returns:
            Created GitBranch
        """
        # Validate branch name
        if not branch_name or " " in branch_name:
            raise GitValidationError(f"Invalid branch name: {branch_name}")

        self._run_git("checkout", "-b", branch_name, base_ref)

        commit_result = self._run_git("rev-parse", "--short", "HEAD")

        return GitBranch(
            name=branch_name,
            commit_hash=commit_result.stdout.strip(),
            is_current=True,
        )

    def checkout_branch(self, branch_name: str) -> None:
        """
        Switch to a branch.

        Args:
            branch_name: Branch to checkout
        """
        # Check for uncommitted changes
        status = self.get_status()
        if status.is_dirty:
            raise GitConflictError(
                "Cannot switch branches with uncommitted changes. "
                "Commit or discard changes first."
            )

        self._run_git("checkout", branch_name)

    # =========================================================================
    # Commit Operations
    # =========================================================================

    def stage_files(self, file_paths: List[str]) -> None:
        """
        Stage files for commit.

        Args:
            file_paths: List of file paths (relative to combine-config) to stage
        """
        if not file_paths:
            return

        full_paths = [self._prefix_path(p) for p in file_paths]
        self._run_git("add", *full_paths)

    def stage_all(self) -> None:
        """Stage all changes in combine-config."""
        self._run_git("add", "-A", self.config_prefix)

    def unstage_files(self, file_paths: List[str]) -> None:
        """
        Unstage files.

        Args:
            file_paths: List of file paths (relative to combine-config) to unstage
        """
        if not file_paths:
            return

        full_paths = [self._prefix_path(p) for p in file_paths]
        self._run_git("reset", "HEAD", "--", *full_paths)

    def commit(
        self,
        message: str,
        user_name: str,
        user_email: Optional[str] = None,
    ) -> GitCommit:
        """
        Create a commit.

        Args:
            message: Commit message
            user_name: User who initiated the commit (for Co-Authored-By)
            user_email: Optional user email

        Returns:
            Created GitCommit
        """
        if not message or not message.strip():
            raise GitValidationError("Commit message is required")

        # Build commit message with metadata
        full_message = message.strip()

        # Add Co-Authored-By trailer for traceability
        if user_email:
            full_message += f"\n\nCo-Authored-By: {user_name} <{user_email}>"
        else:
            full_message += f"\n\nInitiated-By: {user_name}"

        # Check if there are staged changes
        status_result = self._run_git("diff", "--staged", "--name-only")
        if not status_result.stdout.strip():
            raise GitValidationError("No staged changes to commit")

        # Create commit
        self._run_git("commit", "-m", full_message)

        # Get commit info
        return self.get_commit("HEAD")

    def get_commit(self, ref: str = "HEAD") -> GitCommit:
        """
        Get commit information.

        Args:
            ref: Git ref

        Returns:
            GitCommit object
        """
        format_str = "%H|%h|%an|%aI|%s"
        result = self._run_git("log", "-1", f"--format={format_str}", ref)

        parts = result.stdout.strip().split("|")
        if len(parts) >= 5:
            return GitCommit(
                commit_hash=parts[0],
                commit_hash_short=parts[1],
                author=parts[2],
                date=datetime.fromisoformat(parts[3]),
                message=parts[4],
            )

        raise GitServiceError(f"Could not parse commit: {ref}")

    def get_commit_history(
        self,
        path: Optional[str] = None,
        limit: int = 20,
    ) -> List[GitCommit]:
        """
        Get commit history for combine-config.

        Args:
            path: Optional path filter (relative to combine-config)
            limit: Maximum commits to return

        Returns:
            List of GitCommit objects
        """
        format_str = "%H|%h|%an|%aI|%s"
        args = ["log", f"--format={format_str}", f"-{limit}"]

        # Filter to combine-config path
        if path:
            args.extend(["--", self._prefix_path(path)])
        else:
            args.extend(["--", self.config_prefix])

        result = self._run_git(*args)

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) >= 5:
                commits.append(GitCommit(
                    commit_hash=parts[0],
                    commit_hash_short=parts[1],
                    author=parts[2],
                    date=datetime.fromisoformat(parts[3]),
                    message=parts[4],
                ))

        return commits

    # =========================================================================
    # Tag Operations
    # =========================================================================

    def create_tag(self, tag_name: str, message: Optional[str] = None) -> None:
        """
        Create a tag on the current commit.

        Args:
            tag_name: Tag name
            message: Optional tag message (creates annotated tag)
        """
        if message:
            self._run_git("tag", "-a", tag_name, "-m", message)
        else:
            self._run_git("tag", tag_name)

    def list_tags(self) -> List[str]:
        """
        List all tags.

        Returns:
            List of tag names
        """
        result = self._run_git("tag", "-l")
        return [t for t in result.stdout.strip().split("\n") if t]

    # =========================================================================
    # Active Release Operations
    # =========================================================================

    def update_active_release(
        self,
        doc_type_id: str,
        version: str,
        user_name: str,
        user_email: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> GitCommit:
        """
        Update the active release for a document type.

        Args:
            doc_type_id: Document type to update
            version: Version to activate
            user_name: User who initiated the change
            user_email: Optional user email
            commit_message: Optional custom commit message (for rollbacks)

        Returns:
            Commit for the active release change
        """
        import json

        active_releases_path = self.config_path / "_active" / "active_releases.json"

        if not active_releases_path.exists():
            raise GitServiceError("active_releases.json not found")

        # Read current active releases
        with open(active_releases_path, "r") as f:
            active_releases = json.load(f)

        # Update the document type version
        if "document_types" not in active_releases:
            active_releases["document_types"] = {}

        old_version = active_releases["document_types"].get(doc_type_id)
        active_releases["document_types"][doc_type_id] = version

        # Write back
        with open(active_releases_path, "w") as f:
            json.dump(active_releases, f, indent=2)
            f.write("\n")

        # Stage and commit (path is relative to combine-config)
        self.stage_files(["_active/active_releases.json"])

        # Use custom message or generate default
        if commit_message:
            message = commit_message
        else:
            message = f"release({doc_type_id}): Activate version {version}"
            if old_version:
                message += f" (was {old_version})"

        return self.commit(message, user_name, user_email)

    # =========================================================================
    # Discard Operations
    # =========================================================================

    def discard_changes(self, file_paths: Optional[List[str]] = None) -> None:
        """
        Discard uncommitted changes in combine-config.

        Args:
            file_paths: Specific files (relative to combine-config) or None for all
        """
        if file_paths:
            full_paths = [self._prefix_path(p) for p in file_paths]
            self._run_git("checkout", "--", *full_paths)
        else:
            self._run_git("checkout", "--", self.config_prefix)
            # Also remove untracked files in combine-config
            self._run_git("clean", "-fd", self.config_prefix)


# Module-level singleton
_service: Optional[GitService] = None


def get_git_service() -> GitService:
    """Get the singleton GitService instance."""
    global _service
    if _service is None:
        _service = GitService()
    return _service


def reset_git_service() -> None:
    """Reset the singleton (for testing)."""
    global _service
    _service = None

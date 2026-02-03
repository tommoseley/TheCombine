"""
Release Management Service.

Per ADR-044 WS-044-07, this service handles:
- Release lifecycle (Draft -> Staged -> Released)
- Instantaneous rollback via pointer change
- Audit trail for release changes
- Immutability enforcement for released versions
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.api.services.git_service import (
    GitService,
    GitServiceError,
    get_git_service,
)
from app.api.services.config_validator import (
    ConfigValidator,
    ValidationReport,
    get_config_validator,
)
from app.config.package_loader import (
    PackageLoader,
    get_package_loader,
    PackageNotFoundError,
    VersionNotFoundError,
)

logger = logging.getLogger(__name__)


class ReleaseState(str, Enum):
    """Release state per ADR-044."""
    DRAFT = "draft"        # Editable working state (uncommitted changes)
    STAGED = "staged"      # Frozen, validated candidate (committed, not active)
    RELEASED = "released"  # Immutable, active version (tagged + active pointer)


@dataclass
class ReleaseInfo:
    """Information about a release."""
    doc_type_id: str
    version: str
    state: ReleaseState
    is_active: bool
    commit_hash: Optional[str] = None
    commit_date: Optional[datetime] = None
    commit_author: Optional[str] = None
    commit_message: Optional[str] = None


@dataclass
class ReleaseHistoryEntry:
    """Entry in the release audit log."""
    doc_type_id: str
    action: str  # activated, deactivated, rolled_back
    version: str
    previous_version: Optional[str]
    commit_hash: str
    commit_date: datetime
    author: str
    message: str


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    doc_type_id: str
    rolled_back_from: str
    rolled_back_to: str
    commit_hash: str
    commit_message: str


class ReleaseServiceError(Exception):
    """Base exception for release service errors."""
    pass


class ImmutabilityViolationError(ReleaseServiceError):
    """Raised when attempting to modify a released version."""
    pass


class ValidationFailedError(ReleaseServiceError):
    """Raised when release validation fails."""
    def __init__(self, message: str, report: ValidationReport):
        super().__init__(message)
        self.report = report


class ReleaseService:
    """
    Manages document type releases.

    Key responsibilities:
    - Track release states (draft, staged, released)
    - Instantaneous rollback via active pointer change
    - Enforce immutability of released versions
    - Validate before activation
    - Provide audit trail
    """

    def __init__(
        self,
        git_service: Optional[GitService] = None,
        validator: Optional[ConfigValidator] = None,
        loader: Optional[PackageLoader] = None,
    ):
        self._git = git_service or get_git_service()
        self._validator = validator or get_config_validator()
        self._loader = loader or get_package_loader()

    # =========================================================================
    # Release Information
    # =========================================================================

    def get_release_info(self, doc_type_id: str, version: str) -> ReleaseInfo:
        """
        Get release information for a specific version.

        Args:
            doc_type_id: Document type identifier
            version: Version string

        Returns:
            ReleaseInfo with state and metadata
        """
        active = self._loader.get_active_releases()
        is_active = active.document_types.get(doc_type_id) == version

        # Determine state
        # Released = active and has commit
        # Staged = committed but not active
        # Draft = uncommitted changes (we can't easily detect this)

        # Check if version exists as a committed package
        try:
            package = self._loader.get_document_type(doc_type_id, version)

            # Get commit info for this version
            commit_info = self._get_version_commit(doc_type_id, version)

            if is_active:
                state = ReleaseState.RELEASED
            else:
                state = ReleaseState.STAGED

            return ReleaseInfo(
                doc_type_id=doc_type_id,
                version=version,
                state=state,
                is_active=is_active,
                commit_hash=commit_info.get("commit_hash") if commit_info else None,
                commit_date=commit_info.get("commit_date") if commit_info else None,
                commit_author=commit_info.get("author") if commit_info else None,
                commit_message=commit_info.get("message") if commit_info else None,
            )
        except (PackageNotFoundError, VersionNotFoundError):
            raise ReleaseServiceError(f"Version {version} not found for {doc_type_id}")

    def list_releases(self, doc_type_id: str) -> List[ReleaseInfo]:
        """
        List all releases for a document type.

        Args:
            doc_type_id: Document type identifier

        Returns:
            List of ReleaseInfo for all versions
        """
        versions = self._loader.list_document_type_versions(doc_type_id)
        return [self.get_release_info(doc_type_id, v) for v in versions]

    def get_active_version(self, doc_type_id: str) -> Optional[str]:
        """Get the currently active version for a document type."""
        active = self._loader.get_active_releases()
        return active.document_types.get(doc_type_id)

    # =========================================================================
    # Release Activation
    # =========================================================================

    def activate_release(
        self,
        doc_type_id: str,
        version: str,
        user_name: str,
        user_email: Optional[str] = None,
        skip_validation: bool = False,
    ) -> ReleaseInfo:
        """
        Activate a release version.

        Per ADR-044:
        - Cross-package compatibility validated before activation
        - Creates a commit updating active_releases.json

        Args:
            doc_type_id: Document type to activate
            version: Version to activate
            user_name: User performing the activation
            user_email: User's email (optional)
            skip_validation: Skip validation (NOT RECOMMENDED)

        Returns:
            ReleaseInfo for the activated version

        Raises:
            ValidationFailedError: If validation fails
        """
        # Validate before activation
        if not skip_validation:
            report = self._validator.validate_activation(doc_type_id, version)
            if not report.valid:
                raise ValidationFailedError(
                    f"Activation validation failed for {doc_type_id} v{version}",
                    report,
                )

        # Update active release via Git
        commit = self._git.update_active_release(
            doc_type_id=doc_type_id,
            version=version,
            user_name=user_name,
            user_email=user_email,
        )

        # Invalidate cache
        self._loader.invalidate_cache()

        logger.info(
            f"Activated {doc_type_id} v{version} by {user_name} "
            f"(commit: {commit.commit_hash_short})"
        )

        return ReleaseInfo(
            doc_type_id=doc_type_id,
            version=version,
            state=ReleaseState.RELEASED,
            is_active=True,
            commit_hash=commit.commit_hash,
            commit_date=commit.date,
            commit_author=commit.author,
            commit_message=commit.message,
        )

    # =========================================================================
    # Rollback
    # =========================================================================

    def rollback(
        self,
        doc_type_id: str,
        target_version: str,
        user_name: str,
        user_email: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> RollbackResult:
        """
        Rollback to a previous version.

        Per ADR-044:
        - Rollback is instantaneous (pointer change only)
        - Implemented as a single commit to active_releases.json

        Args:
            doc_type_id: Document type to rollback
            target_version: Version to rollback to
            user_name: User performing the rollback
            user_email: User's email (optional)
            reason: Reason for rollback (included in commit message)

        Returns:
            RollbackResult with details of the rollback
        """
        # Get current version
        current_version = self.get_active_version(doc_type_id)
        if current_version is None:
            raise ReleaseServiceError(f"No active version for {doc_type_id}")

        if current_version == target_version:
            raise ReleaseServiceError(
                f"{doc_type_id} is already at version {target_version}"
            )

        # Verify target version exists
        try:
            self._loader.get_document_type(doc_type_id, target_version)
        except (PackageNotFoundError, VersionNotFoundError):
            raise ReleaseServiceError(
                f"Target version {target_version} not found for {doc_type_id}"
            )

        # Build commit message
        message = f"Rollback {doc_type_id} from {current_version} to {target_version}"
        if reason:
            message += f"\n\nReason: {reason}"

        # Update active release
        commit = self._git.update_active_release(
            doc_type_id=doc_type_id,
            version=target_version,
            user_name=user_name,
            user_email=user_email,
            commit_message=message,
        )

        # Invalidate cache
        self._loader.invalidate_cache()

        logger.info(
            f"Rolled back {doc_type_id} from {current_version} to {target_version} "
            f"by {user_name} (commit: {commit.commit_hash_short})"
        )

        return RollbackResult(
            doc_type_id=doc_type_id,
            rolled_back_from=current_version,
            rolled_back_to=target_version,
            commit_hash=commit.commit_hash,
            commit_message=commit.message,
        )

    # =========================================================================
    # Release History (Audit Trail)
    # =========================================================================

    def get_release_history(
        self,
        doc_type_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReleaseHistoryEntry]:
        """
        Get release history (audit trail).

        Parses Git commit history for active_releases.json to build
        an audit trail of all release changes.

        Args:
            doc_type_id: Filter by document type (optional)
            limit: Maximum entries to return

        Returns:
            List of ReleaseHistoryEntry sorted by date (newest first)
        """
        # Get commit history for active_releases.json
        commits = self._git.get_commit_history(
            path="_active/active_releases.json",
            limit=limit * 2,  # Get extra in case of filtering
        )

        history = []
        previous_active: Dict[str, str] = {}

        # Process commits in reverse chronological order
        for commit in reversed(commits):
            # Get active_releases.json content at this commit
            content = self._git.get_file_content(
                "_active/active_releases.json",
                ref=commit.commit_hash,
            )
            if not content:
                continue

            try:
                data = json.loads(content)
                current_active = data.get("document_types", {})
            except json.JSONDecodeError:
                continue

            # Find changes from previous state
            for dt_id, version in current_active.items():
                if doc_type_id and dt_id != doc_type_id:
                    continue

                prev_version = previous_active.get(dt_id)

                if prev_version != version:
                    # Determine action type
                    if prev_version is None:
                        action = "activated"
                    elif "rollback" in commit.message.lower():
                        action = "rolled_back"
                    else:
                        action = "activated"

                    history.append(ReleaseHistoryEntry(
                        doc_type_id=dt_id,
                        action=action,
                        version=version,
                        previous_version=prev_version,
                        commit_hash=commit.commit_hash,
                        commit_date=commit.date,
                        author=commit.author,
                        message=commit.message,
                    ))

            # Check for deactivations
            for dt_id, version in previous_active.items():
                if doc_type_id and dt_id != doc_type_id:
                    continue
                if dt_id not in current_active:
                    history.append(ReleaseHistoryEntry(
                        doc_type_id=dt_id,
                        action="deactivated",
                        version=version,
                        previous_version=version,
                        commit_hash=commit.commit_hash,
                        commit_date=commit.date,
                        author=commit.author,
                        message=commit.message,
                    ))

            previous_active = current_active

        # Sort by date (newest first) and limit
        history.sort(key=lambda e: e.commit_date, reverse=True)
        return history[:limit]

    # =========================================================================
    # Immutability Enforcement
    # =========================================================================

    def check_immutability(
        self,
        doc_type_id: str,
        version: str,
    ) -> bool:
        """
        Check if a version can be modified.

        Per ADR-044: Released artifacts are immutable (no edits to released versions).

        A version is immutable if it is currently active.

        Args:
            doc_type_id: Document type identifier
            version: Version to check

        Returns:
            True if version is immutable, False if editable
        """
        active = self._loader.get_active_releases()
        return active.document_types.get(doc_type_id) == version

    def enforce_immutability(
        self,
        doc_type_id: str,
        version: str,
    ) -> None:
        """
        Enforce immutability rules.

        Raises ImmutabilityViolationError if the version is immutable.

        Args:
            doc_type_id: Document type identifier
            version: Version to check

        Raises:
            ImmutabilityViolationError: If version is immutable
        """
        if self.check_immutability(doc_type_id, version):
            raise ImmutabilityViolationError(
                f"Cannot modify {doc_type_id} v{version}: version is released and immutable. "
                f"Create a new version to make changes."
            )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_version_commit(
        self,
        doc_type_id: str,
        version: str,
    ) -> Optional[Dict[str, Any]]:
        """Get commit info for a specific version."""
        # Get commits affecting this package
        path = f"document_types/{doc_type_id}/releases/{version}"
        commits = self._git.get_commit_history(path=path, limit=1)

        if commits:
            commit = commits[0]
            return {
                "commit_hash": commit.commit_hash,
                "commit_date": commit.date,
                "author": commit.author,
                "message": commit.message,
            }
        return None


# Module-level singleton
_release_service: Optional[ReleaseService] = None


def get_release_service() -> ReleaseService:
    """Get the singleton ReleaseService instance."""
    global _release_service
    if _release_service is None:
        _release_service = ReleaseService()
    return _release_service


def reset_release_service() -> None:
    """Reset the singleton (for testing)."""
    global _release_service
    _release_service = None

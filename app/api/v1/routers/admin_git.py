"""
Admin Git API endpoints.

Per ADR-044 Addendum A, Git operations are first-class UX primitives.
These endpoints provide Git operations for the Admin Workbench.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.services.git_service import (
    GitService,
    GitServiceError,
    GitValidationError,
    GitConflictError,
    get_git_service,
)


router = APIRouter(prefix="/admin/git", tags=["admin-git"])


# ===========================================================================
# Request/Response Models
# ===========================================================================

class GitStatusResponse(BaseModel):
    """Git workspace status."""
    branch: str
    base_commit: str
    base_commit_short: str
    is_dirty: bool
    modified_files: List[str]
    added_files: List[str]
    deleted_files: List[str]
    untracked_files: List[str]
    total_changes: int


class GitDiffItem(BaseModel):
    """Single file diff."""
    file_path: str
    status: str
    diff_content: str
    additions: int
    deletions: int


class GitDiffResponse(BaseModel):
    """Diff response."""
    diffs: List[GitDiffItem]
    total_files: int
    total_additions: int
    total_deletions: int


class GitBranchItem(BaseModel):
    """Branch information."""
    name: str
    commit_hash: str
    is_current: bool
    is_remote: bool = False


class GitBranchListResponse(BaseModel):
    """List of branches."""
    branches: List[GitBranchItem]
    current_branch: str


class CreateBranchRequest(BaseModel):
    """Request to create a branch."""
    branch_name: str = Field(..., min_length=1, max_length=100)
    base_ref: str = Field(default="HEAD")


class CheckoutBranchRequest(BaseModel):
    """Request to checkout a branch."""
    branch_name: str


class StageFilesRequest(BaseModel):
    """Request to stage files."""
    file_paths: List[str]


class CommitRequest(BaseModel):
    """Request to create a commit."""
    message: str = Field(..., min_length=1, max_length=1000)
    user_name: str = Field(..., min_length=1)
    user_email: Optional[str] = None
    stage_all: bool = Field(default=False, description="Stage all changes before commit")


class GitCommitResponse(BaseModel):
    """Commit information."""
    commit_hash: str
    commit_hash_short: str
    author: str
    date: datetime
    message: str


class GitCommitHistoryResponse(BaseModel):
    """Commit history."""
    commits: List[GitCommitResponse]
    total: int


class ActivateReleaseRequest(BaseModel):
    """Request to activate a release."""
    doc_type_id: str
    version: str
    user_name: str
    user_email: Optional[str] = None


class DiscardChangesRequest(BaseModel):
    """Request to discard changes."""
    file_paths: Optional[List[str]] = None


class FileContentResponse(BaseModel):
    """File content at a ref."""
    file_path: str
    ref: str
    content: Optional[str]
    exists: bool


# ===========================================================================
# Status & Information Endpoints
# ===========================================================================

@router.get(
    "/status",
    response_model=GitStatusResponse,
    summary="Get Git status",
    description="Get current Git workspace status including branch, commit, and file changes.",
)
async def get_status(
    service: GitService = Depends(get_git_service),
) -> GitStatusResponse:
    """Get Git workspace status."""
    try:
        status = service.get_status()
        total_changes = (
            len(status.modified_files) +
            len(status.added_files) +
            len(status.deleted_files) +
            len(status.untracked_files)
        )
        return GitStatusResponse(
            branch=status.branch,
            base_commit=status.base_commit,
            base_commit_short=status.base_commit_short,
            is_dirty=status.is_dirty,
            modified_files=status.modified_files,
            added_files=status.added_files,
            deleted_files=status.deleted_files,
            untracked_files=status.untracked_files,
            total_changes=total_changes,
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.get(
    "/diff",
    response_model=GitDiffResponse,
    summary="Get diffs",
    description="Get diffs for modified files.",
)
async def get_diff(
    file_path: Optional[str] = None,
    staged: bool = False,
    service: GitService = Depends(get_git_service),
) -> GitDiffResponse:
    """Get file diffs."""
    try:
        diffs = service.get_diff(file_path, staged)
        total_additions = sum(d.additions for d in diffs)
        total_deletions = sum(d.deletions for d in diffs)
        return GitDiffResponse(
            diffs=[
                GitDiffItem(
                    file_path=d.file_path,
                    status=d.status,
                    diff_content=d.diff_content,
                    additions=d.additions,
                    deletions=d.deletions,
                )
                for d in diffs
            ],
            total_files=len(diffs),
            total_additions=total_additions,
            total_deletions=total_deletions,
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.get(
    "/file/{file_path:path}",
    response_model=FileContentResponse,
    summary="Get file content",
    description="Get file content at a specific Git ref.",
)
async def get_file_content(
    file_path: str,
    ref: str = "HEAD",
    service: GitService = Depends(get_git_service),
) -> FileContentResponse:
    """Get file content at ref."""
    try:
        content = service.get_file_content(file_path, ref)
        return FileContentResponse(
            file_path=file_path,
            ref=ref,
            content=content,
            exists=content is not None,
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


# ===========================================================================
# Branch Endpoints
# ===========================================================================

@router.get(
    "/branches",
    response_model=GitBranchListResponse,
    summary="List branches",
    description="List all Git branches.",
)
async def list_branches(
    include_remote: bool = False,
    service: GitService = Depends(get_git_service),
) -> GitBranchListResponse:
    """List branches."""
    try:
        branches = service.list_branches(include_remote)
        current = next((b.name for b in branches if b.is_current), "unknown")
        return GitBranchListResponse(
            branches=[
                GitBranchItem(
                    name=b.name,
                    commit_hash=b.commit_hash,
                    is_current=b.is_current,
                    is_remote=b.is_remote,
                )
                for b in branches
            ],
            current_branch=current,
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.post(
    "/branches",
    response_model=GitBranchItem,
    summary="Create branch",
    description="Create a new branch for editing.",
    status_code=status.HTTP_201_CREATED,
)
async def create_branch(
    request: CreateBranchRequest,
    service: GitService = Depends(get_git_service),
) -> GitBranchItem:
    """Create a new branch."""
    try:
        branch = service.create_branch(request.branch_name, request.base_ref)
        return GitBranchItem(
            name=branch.name,
            commit_hash=branch.commit_hash,
            is_current=branch.is_current,
        )
    except GitValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "VALIDATION_ERROR", "message": str(e)},
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.post(
    "/checkout",
    summary="Checkout branch",
    description="Switch to a different branch. Requires clean working directory.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def checkout_branch(
    request: CheckoutBranchRequest,
    service: GitService = Depends(get_git_service),
) -> None:
    """Checkout a branch."""
    try:
        service.checkout_branch(request.branch_name)
    except GitConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "UNCOMMITTED_CHANGES", "message": str(e)},
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


# ===========================================================================
# Staging Endpoints
# ===========================================================================

@router.post(
    "/stage",
    summary="Stage files",
    description="Stage files for commit.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def stage_files(
    request: StageFilesRequest,
    service: GitService = Depends(get_git_service),
) -> None:
    """Stage files."""
    try:
        service.stage_files(request.file_paths)
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.post(
    "/stage-all",
    summary="Stage all changes",
    description="Stage all modified, added, and deleted files.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def stage_all(
    service: GitService = Depends(get_git_service),
) -> None:
    """Stage all changes."""
    try:
        service.stage_all()
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.post(
    "/unstage",
    summary="Unstage files",
    description="Unstage files from the staging area.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unstage_files(
    request: StageFilesRequest,
    service: GitService = Depends(get_git_service),
) -> None:
    """Unstage files."""
    try:
        service.unstage_files(request.file_paths)
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


# ===========================================================================
# Commit Endpoints
# ===========================================================================

@router.post(
    "/commit",
    response_model=GitCommitResponse,
    summary="Create commit",
    description="Create a Git commit with staged changes.",
    status_code=status.HTTP_201_CREATED,
)
async def create_commit(
    request: CommitRequest,
    service: GitService = Depends(get_git_service),
) -> GitCommitResponse:
    """Create a commit."""
    try:
        if request.stage_all:
            service.stage_all()

        commit = service.commit(
            message=request.message,
            user_name=request.user_name,
            user_email=request.user_email,
        )
        return GitCommitResponse(
            commit_hash=commit.commit_hash,
            commit_hash_short=commit.commit_hash_short,
            author=commit.author,
            date=commit.date,
            message=commit.message,
        )
    except GitValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "VALIDATION_ERROR", "message": str(e)},
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


@router.get(
    "/commits",
    response_model=GitCommitHistoryResponse,
    summary="Get commit history",
    description="Get commit history, optionally filtered by path.",
)
async def get_commit_history(
    path: Optional[str] = None,
    limit: int = 20,
    service: GitService = Depends(get_git_service),
) -> GitCommitHistoryResponse:
    """Get commit history."""
    try:
        commits = service.get_commit_history(path, limit)
        return GitCommitHistoryResponse(
            commits=[
                GitCommitResponse(
                    commit_hash=c.commit_hash,
                    commit_hash_short=c.commit_hash_short,
                    author=c.author,
                    date=c.date,
                    message=c.message,
                )
                for c in commits
            ],
            total=len(commits),
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


# ===========================================================================
# Release Activation Endpoint
# ===========================================================================

@router.post(
    "/activate-release",
    response_model=GitCommitResponse,
    summary="Activate release",
    description="Update active_releases.json to activate a new version.",
    status_code=status.HTTP_201_CREATED,
)
async def activate_release(
    request: ActivateReleaseRequest,
    service: GitService = Depends(get_git_service),
) -> GitCommitResponse:
    """Activate a release version."""
    try:
        commit = service.update_active_release(
            doc_type_id=request.doc_type_id,
            version=request.version,
            user_name=request.user_name,
            user_email=request.user_email,
        )
        return GitCommitResponse(
            commit_hash=commit.commit_hash,
            commit_hash_short=commit.commit_hash_short,
            author=commit.author,
            date=commit.date,
            message=commit.message,
        )
    except GitValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "VALIDATION_ERROR", "message": str(e)},
        )
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )


# ===========================================================================
# Discard Changes Endpoint
# ===========================================================================

@router.post(
    "/discard",
    summary="Discard changes",
    description="Discard uncommitted changes. WARNING: This is destructive.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def discard_changes(
    request: DiscardChangesRequest,
    service: GitService = Depends(get_git_service),
) -> None:
    """Discard uncommitted changes."""
    try:
        service.discard_changes(request.file_paths)
    except GitServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GIT_ERROR", "message": str(e)},
        )

"""
Admin Workspaces API endpoints.

Per ADR-044 WS-044-03, these endpoints provide workspace-scoped
editing operations for configuration artifacts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceDirtyError,
    ArtifactError,
    ArtifactNotFoundError,
    ArtifactIdError,
    get_workspace_service,
)


router = APIRouter(prefix="/admin/workspaces", tags=["admin-workspaces"])


# ===========================================================================
# Request/Response Models
# ===========================================================================

class Tier1ResultModel(BaseModel):
    """Single tier 1 validation result."""
    rule_id: str
    status: str
    message: Optional[str] = None
    artifact_id: Optional[str] = None


class Tier1ReportModel(BaseModel):
    """Tier 1 validation report."""
    passed: bool
    results: List[Tier1ResultModel]


class WorkspaceStateResponse(BaseModel):
    """Workspace state response."""
    workspace_id: str
    user_id: str
    branch: str
    base_commit: str
    is_dirty: bool
    modified_artifacts: List[str]
    modified_files: List[str]
    tier1: Tier1ReportModel
    last_touched: datetime
    expires_at: datetime


class CreateWorkspaceResponse(BaseModel):
    """Response for workspace creation."""
    workspace_id: str
    branch: str
    base_commit: str


class ArtifactContentResponse(BaseModel):
    """Artifact content response."""
    artifact_id: str
    content: str
    version: str


class WriteArtifactRequest(BaseModel):
    """Request to write artifact content."""
    content: str = Field(..., description="New artifact content")


class WriteArtifactResponse(BaseModel):
    """Response for artifact write."""
    success: bool
    tier1: Tier1ReportModel


class PreviewProvenanceModel(BaseModel):
    """Provenance information for preview."""
    role: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")
    package: Optional[str] = None

    model_config = {"populate_by_name": True}


class PreviewResponse(BaseModel):
    """Preview response with resolved prompt."""
    resolved_prompt: str
    provenance: PreviewProvenanceModel


class CommitRequest(BaseModel):
    """Request to commit changes."""
    message: str = Field(..., min_length=1, max_length=1000)


class CommitResponse(BaseModel):
    """Response for commit."""
    commit_hash: str
    commit_hash_short: str
    message: str


# ===========================================================================
# Helper: Get User from Request
# ===========================================================================

def _get_user_info(request: Request) -> Dict[str, Any]:
    """
    Extract user info from request.

    For now, uses a placeholder. In production, this would
    come from the auth session.
    """
    # TODO: Get real user from session/auth
    # For now, use a placeholder
    user = getattr(request.state, "user", None)
    if user:
        return {
            "user_id": str(user.id) if hasattr(user, "id") else "unknown",
            "user_name": user.name if hasattr(user, "name") else "Admin User",
        }

    # Fallback for development
    return {
        "user_id": "dev-user",
        "user_name": "Development User",
    }


# ===========================================================================
# Workspace Lifecycle Endpoints
# ===========================================================================

@router.get(
    "/current",
    response_model=WorkspaceStateResponse,
    summary="Get current workspace",
    description="Get the current workspace for the authenticated user.",
    responses={
        404: {"description": "No workspace exists for this user"},
    },
)
async def get_current_workspace(
    request: Request,
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceStateResponse:
    """Get current workspace for user."""
    user_info = _get_user_info(request)
    user_id = user_info["user_id"]

    state = service.get_current_workspace(user_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NO_WORKSPACE",
                "message": "No active workspace for this user",
            },
        )

    return _state_to_response(state)


@router.post(
    "",
    response_model=CreateWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace",
    description="Create a new workspace for the authenticated user.",
    responses={
        409: {"description": "User already has an active workspace"},
    },
)
async def create_workspace(
    request: Request,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateWorkspaceResponse:
    """Create a new workspace."""
    user_info = _get_user_info(request)
    user_id = user_info["user_id"]

    try:
        state = service.create_workspace(user_id)
    except WorkspaceError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "WORKSPACE_EXISTS",
                "message": str(e),
            },
        )

    return CreateWorkspaceResponse(
        workspace_id=state.workspace_id,
        branch=state.branch,
        base_commit=state.base_commit,
    )


@router.get(
    "/{workspace_id}/state",
    response_model=WorkspaceStateResponse,
    summary="Get workspace state",
    description="Get current state of a workspace including git status and validation.",
    responses={
        404: {"description": "Workspace not found"},
    },
)
async def get_workspace_state(
    workspace_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceStateResponse:
    """Get workspace state."""
    try:
        state = service.get_workspace_state(workspace_id)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )

    return _state_to_response(state)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Close workspace",
    description="Close and clean up a workspace.",
    responses={
        404: {"description": "Workspace not found"},
        409: {"description": "Workspace has uncommitted changes"},
    },
)
async def close_workspace(
    workspace_id: str,
    force: bool = Query(False, description="Close even if dirty"),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    """Close workspace."""
    try:
        service.close_workspace(workspace_id, force=force)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except WorkspaceDirtyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "WORKSPACE_DIRTY",
                "message": str(e),
            },
        )


# ===========================================================================
# Artifact Endpoints
# ===========================================================================

@router.get(
    "/{workspace_id}/artifacts/{artifact_id:path}",
    response_model=ArtifactContentResponse,
    summary="Get artifact content",
    description="Get the content of an artifact.",
    responses={
        404: {"description": "Workspace or artifact not found"},
        400: {"description": "Invalid artifact ID"},
    },
)
async def get_artifact(
    workspace_id: str,
    artifact_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
) -> ArtifactContentResponse:
    """Get artifact content."""
    try:
        content = service.get_artifact(workspace_id, artifact_id)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except ArtifactNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ARTIFACT_NOT_FOUND",
                "message": str(e),
            },
        )
    except ArtifactIdError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_ARTIFACT_ID",
                "message": str(e),
            },
        )

    return ArtifactContentResponse(
        artifact_id=content.artifact_id,
        content=content.content,
        version=content.version,
    )


@router.put(
    "/{workspace_id}/artifacts/{artifact_id:path}",
    response_model=WriteArtifactResponse,
    summary="Write artifact content",
    description="Write new content to an artifact. Auto-saves to filesystem.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid artifact ID"},
    },
)
async def write_artifact(
    workspace_id: str,
    artifact_id: str,
    body: WriteArtifactRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> WriteArtifactResponse:
    """Write artifact content."""
    try:
        tier1 = service.write_artifact(workspace_id, artifact_id, body.content)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactIdError, ArtifactError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "ARTIFACT_ERROR",
                "message": str(e),
            },
        )

    return WriteArtifactResponse(
        success=True,
        tier1=Tier1ReportModel(
            passed=tier1.passed,
            results=[
                Tier1ResultModel(
                    rule_id=r.rule_id,
                    status=r.status,
                    message=r.message,
                    artifact_id=r.artifact_id,
                )
                for r in tier1.results
            ],
        ),
    )


@router.get(
    "/{workspace_id}/preview/{artifact_id:path}",
    response_model=PreviewResponse,
    summary="Get artifact preview",
    description="Get resolved preview of a prompt artifact.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid artifact or preview failed"},
    },
)
async def get_preview(
    workspace_id: str,
    artifact_id: str,
    mode: str = Query("execution", description="Preview mode"),
    service: WorkspaceService = Depends(get_workspace_service),
) -> PreviewResponse:
    """Get artifact preview."""
    try:
        preview = service.get_preview(workspace_id, artifact_id, mode)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except ArtifactError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "PREVIEW_ERROR",
                "message": str(e),
            },
        )

    return PreviewResponse(
        resolved_prompt=preview.resolved_prompt,
        provenance=PreviewProvenanceModel(
            role=preview.provenance.role,
            schema=preview.provenance.schema,
            package=preview.provenance.package,
        ),
    )


# ===========================================================================
# Commit Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/commit",
    response_model=CommitResponse,
    summary="Commit changes",
    description="Commit all changes in the workspace.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Validation failed or no changes"},
    },
)
async def commit_changes(
    workspace_id: str,
    body: CommitRequest,
    request: Request,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CommitResponse:
    """Commit changes."""
    user_info = _get_user_info(request)

    try:
        result = service.commit(
            workspace_id=workspace_id,
            message=body.message,
            actor_name=user_info["user_name"],
            actor_id=user_info["user_id"],
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except WorkspaceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "COMMIT_FAILED",
                "message": str(e),
            },
        )

    return CommitResponse(
        commit_hash=result.commit_hash,
        commit_hash_short=result.commit_hash_short,
        message=result.message,
    )


@router.post(
    "/{workspace_id}/discard",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Discard changes",
    description="Discard all uncommitted changes in the workspace.",
    responses={
        404: {"description": "Workspace not found"},
    },
)
async def discard_changes(
    workspace_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    """Discard changes."""
    try:
        service.discard(workspace_id)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except WorkspaceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DISCARD_FAILED",
                "message": str(e),
            },
        )


# ===========================================================================
# Helper Functions
# ===========================================================================

def _state_to_response(state) -> WorkspaceStateResponse:
    """Convert WorkspaceState to response model."""
    return WorkspaceStateResponse(
        workspace_id=state.workspace_id,
        user_id=state.user_id,
        branch=state.branch,
        base_commit=state.base_commit,
        is_dirty=state.is_dirty,
        modified_artifacts=state.modified_artifacts,
        modified_files=state.modified_files,
        tier1=Tier1ReportModel(
            passed=state.tier1.passed,
            results=[
                Tier1ResultModel(
                    rule_id=r.rule_id,
                    status=r.status,
                    message=r.message,
                    artifact_id=r.artifact_id,
                )
                for r in state.tier1.results
            ],
        ),
        last_touched=state.last_touched,
        expires_at=state.expires_at,
    )

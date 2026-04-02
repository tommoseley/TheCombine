"""
Workspace lifecycle routes: open, close, state, discard, commit.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceDirtyError,
    get_workspace_service,
)
from app.api.v1.routers.admin_workspaces_common import (
    CommitRequest,
    CommitResponse,
    CreateWorkspaceResponse,
    WorkspaceStateResponse,
    get_user_info,
    state_to_response,
)


router = APIRouter(tags=["admin-workspaces"])


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
    user_info = get_user_info(request)
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

    return state_to_response(state)


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

    return state_to_response(state)


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
    user_info = get_user_info(request)

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

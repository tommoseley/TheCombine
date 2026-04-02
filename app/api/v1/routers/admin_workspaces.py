"""
Admin Workspaces API endpoints.

Per ADR-044 WS-044-03, these endpoints provide workspace-scoped
editing operations for configuration artifacts.

This module composes sub-routers for lifecycle, artifact, and scaffold
operations. All endpoint paths are preserved via prefix-free sub-routers.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceError,
    get_workspace_service,
)
from app.api.v1.routers.admin_workspaces_common import (
    CreateWorkspaceResponse,
    get_user_info,
)
from app.api.v1.routers.admin_workspaces_lifecycle import router as lifecycle_router
from app.api.v1.routers.admin_workspaces_artifacts import router as artifacts_router
from app.api.v1.routers.admin_workspaces_scaffold import router as scaffold_router


router = APIRouter(prefix="/admin/workspaces", tags=["admin-workspaces"])


# create_workspace lives here (not in sub-router) because its path is ""
# which FastAPI rejects on prefix-free sub-routers.
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
    user_info = get_user_info(request)
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


router.include_router(lifecycle_router)
router.include_router(artifacts_router)
router.include_router(scaffold_router)

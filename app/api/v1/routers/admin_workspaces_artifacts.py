"""
Artifact CRUD routes: get, write, diff, preview.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    ArtifactError,
    ArtifactNotFoundError,
    ArtifactIdError,
    get_workspace_service,
)
from app.api.v1.routers.admin_workspaces_common import (
    ArtifactContentResponse,
    ArtifactDiffModel,
    DiffResponse,
    PreviewProvenanceModel,
    PreviewResponse,
    Tier1ReportModel,
    Tier1ResultModel,
    WriteArtifactRequest,
    WriteArtifactResponse,
)


router = APIRouter(tags=["admin-workspaces"])


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
    except ArtifactError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "ARTIFACT_ERROR",
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
    "/{workspace_id}/diff",
    response_model=DiffResponse,
    summary="Get workspace diff",
    description="Get diff for all changes in the workspace.",
    responses={
        404: {"description": "Workspace not found"},
    },
)
async def get_diff(
    workspace_id: str,
    artifact_id: Optional[str] = Query(None, description="Specific artifact ID"),
    service: WorkspaceService = Depends(get_workspace_service),
) -> DiffResponse:
    """Get diff for workspace changes."""
    try:
        diffs = service.get_diff(workspace_id, artifact_id)
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

    return DiffResponse(
        diffs=[
            ArtifactDiffModel(
                artifact_id=d.artifact_id,
                file_path=d.file_path,
                status=d.status,
                old_content=d.old_content,
                new_content=d.new_content,
                diff_content=d.diff_content,
                additions=d.additions,
                deletions=d.deletions,
            )
            for d in diffs
        ],
        total=len(diffs),
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

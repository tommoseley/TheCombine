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


class CreateOrchestrationWorkflowRequest(BaseModel):
    """Request to create an orchestration workflow."""
    workflow_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')
    pow_class: str = Field("template", pattern=r'^(reference|template|instance)$')
    derived_from: Optional[Dict[str, str]] = None
    source_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CreateOrchestrationWorkflowResponse(BaseModel):
    """Response for orchestration workflow creation."""
    workflow_id: str
    version: str
    artifact_id: str


class CreateDocumentTypeRequest(BaseModel):
    """Request to create a document type (DCW)."""
    doc_type_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    display_name: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')
    scope: str = Field("project", pattern=r'^[a-z][a-z0-9_]*$')
    role_ref: str = Field("prompt:role:technical_architect:1.0.0")


class CreateDocumentTypeResponse(BaseModel):
    """Response for document type creation."""
    doc_type_id: str
    version: str
    artifact_id: str


class CreateDcwWorkflowRequest(BaseModel):
    """Request to create a DCW workflow for an existing document type."""
    doc_type_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateDcwWorkflowResponse(BaseModel):
    """Response for DCW workflow creation."""
    doc_type_id: str
    version: str
    artifact_id: str


class CreateRolePromptRequest(BaseModel):
    """Request to create a role prompt."""
    role_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateRolePromptResponse(BaseModel):
    """Response for role prompt creation."""
    role_id: str
    version: str
    artifact_id: str


class CreateTemplateRequest(BaseModel):
    """Request to create a template."""
    template_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, max_length=200)
    purpose: str = Field("general", pattern=r'^(document|qa|pgc|general)$')
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateTemplateResponse(BaseModel):
    """Response for template creation."""
    template_id: str
    version: str
    artifact_id: str


class CreateSchemaRequest(BaseModel):
    """Request to create a standalone schema."""
    schema_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    title: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateSchemaResponse(BaseModel):
    """Response for schema creation."""
    schema_id: str
    version: str
    artifact_id: str


class ArtifactDiffModel(BaseModel):
    """Diff for a single artifact."""
    artifact_id: str
    file_path: str
    status: str  # M=modified, A=added, D=deleted
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff_content: str
    additions: int = 0
    deletions: int = 0


class DiffResponse(BaseModel):
    """Response for diff endpoint."""
    diffs: List[ArtifactDiffModel]
    total: int


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
# Orchestration Workflow Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/orchestration-workflows",
    response_model=CreateOrchestrationWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create orchestration workflow",
    description="Create a new step-based orchestration workflow definition.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid workflow ID or workflow already exists"},
    },
)
async def create_orchestration_workflow(
    workspace_id: str,
    body: CreateOrchestrationWorkflowRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateOrchestrationWorkflowResponse:
    """Create a new orchestration workflow."""
    try:
        artifact_id = service.create_orchestration_workflow(
            workspace_id=workspace_id,
            workflow_id=body.workflow_id,
            name=body.name,
            version=body.version,
            pow_class=body.pow_class,
            derived_from=body.derived_from,
            source_version=body.source_version,
            tags=body.tags,
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactError, ArtifactIdError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "WORKFLOW_ERROR",
                "message": str(e),
            },
        )

    return CreateOrchestrationWorkflowResponse(
        workflow_id=body.workflow_id,
        version=body.version,
        artifact_id=artifact_id,
    )


@router.delete(
    "/{workspace_id}/orchestration-workflows/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete orchestration workflow",
    description="Delete a step-based orchestration workflow definition.",
    responses={
        404: {"description": "Workspace or workflow not found"},
        400: {"description": "Cannot delete graph-based workflow"},
    },
)
async def delete_orchestration_workflow(
    workspace_id: str,
    workflow_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    """Delete an orchestration workflow."""
    try:
        service.delete_orchestration_workflow(
            workspace_id=workspace_id,
            workflow_id=workflow_id,
        )
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
                "error_code": "WORKFLOW_NOT_FOUND",
                "message": str(e),
            },
        )
    except ArtifactError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "WORKFLOW_ERROR",
                "message": str(e),
            },
        )


# ===========================================================================
# Document Type Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/document-types",
    response_model=CreateDocumentTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create document type",
    description="Create a new document type definition (DCW).",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid doc_type_id or document type already exists"},
    },
)
async def create_document_type(
    workspace_id: str,
    body: CreateDocumentTypeRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateDocumentTypeResponse:
    """Create a new document type."""
    try:
        artifact_id = service.create_document_type(
            workspace_id=workspace_id,
            doc_type_id=body.doc_type_id,
            display_name=body.display_name,
            version=body.version,
            scope=body.scope,
            role_ref=body.role_ref,
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactError, ArtifactIdError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DOCUMENT_TYPE_ERROR",
                "message": str(e),
            },
        )

    return CreateDocumentTypeResponse(
        doc_type_id=body.doc_type_id,
        version=body.version,
        artifact_id=artifact_id,
    )


@router.delete(
    "/{workspace_id}/document-types/{doc_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document type",
    description="Delete a document type definition (DCW).",
    responses={
        404: {"description": "Workspace or document type not found"},
    },
)
async def delete_document_type(
    workspace_id: str,
    doc_type_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    """Delete a document type."""
    try:
        service.delete_document_type(
            workspace_id=workspace_id,
            doc_type_id=doc_type_id,
        )
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
                "error_code": "DOCUMENT_TYPE_NOT_FOUND",
                "message": str(e),
            },
        )
    except ArtifactError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DOCUMENT_TYPE_ERROR",
                "message": str(e),
            },
        )


# ===========================================================================
# DCW Workflow Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/dcw-workflows",
    response_model=CreateDcwWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create DCW workflow",
    description="Create a graph-based workflow definition for an existing document type.",
    responses={
        404: {"description": "Workspace or document type not found"},
        400: {"description": "Invalid doc_type_id or workflow already exists"},
    },
)
async def create_dcw_workflow(
    workspace_id: str,
    body: CreateDcwWorkflowRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateDcwWorkflowResponse:
    """Create a DCW workflow for an existing document type."""
    try:
        artifact_id = service.create_dcw_workflow(
            workspace_id=workspace_id,
            doc_type_id=body.doc_type_id,
            version=body.version,
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactError, ArtifactIdError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DCW_WORKFLOW_ERROR",
                "message": str(e),
            },
        )

    return CreateDcwWorkflowResponse(
        doc_type_id=body.doc_type_id,
        version=body.version,
        artifact_id=artifact_id,
    )


# ===========================================================================
# Role Prompt Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/role-prompts",
    response_model=CreateRolePromptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role prompt",
    description="Create a new role prompt definition.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid role_id or role already exists"},
    },
)
async def create_role_prompt(
    workspace_id: str,
    body: CreateRolePromptRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateRolePromptResponse:
    """Create a new role prompt."""
    try:
        artifact_id = service.create_role_prompt(
            workspace_id=workspace_id,
            role_id=body.role_id,
            name=body.name,
            version=body.version,
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactError, ArtifactIdError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "ROLE_PROMPT_ERROR",
                "message": str(e),
            },
        )

    return CreateRolePromptResponse(
        role_id=body.role_id,
        version=body.version,
        artifact_id=artifact_id,
    )


# ===========================================================================
# Template Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/templates",
    response_model=CreateTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template",
    description="Create a new template definition.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid template_id or template already exists"},
    },
)
async def create_template(
    workspace_id: str,
    body: CreateTemplateRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateTemplateResponse:
    """Create a new template."""
    try:
        artifact_id = service.create_template(
            workspace_id=workspace_id,
            template_id=body.template_id,
            name=body.name,
            purpose=body.purpose,
            version=body.version,
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactError, ArtifactIdError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "TEMPLATE_ERROR",
                "message": str(e),
            },
        )

    return CreateTemplateResponse(
        template_id=body.template_id,
        version=body.version,
        artifact_id=artifact_id,
    )


# ===========================================================================
# Standalone Schema Endpoints
# ===========================================================================

@router.post(
    "/{workspace_id}/schemas",
    response_model=CreateSchemaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create schema",
    description="Create a new standalone schema definition.",
    responses={
        404: {"description": "Workspace not found"},
        400: {"description": "Invalid schema_id or schema already exists"},
    },
)
async def create_schema(
    workspace_id: str,
    body: CreateSchemaRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> CreateSchemaResponse:
    """Create a new standalone schema."""
    try:
        artifact_id = service.create_standalone_schema(
            workspace_id=workspace_id,
            schema_id=body.schema_id,
            title=body.title,
            version=body.version,
        )
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKSPACE_NOT_FOUND",
                "message": str(e),
            },
        )
    except (ArtifactError, ArtifactIdError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "SCHEMA_ERROR",
                "message": str(e),
            },
        )

    return CreateSchemaResponse(
        schema_id=body.schema_id,
        version=body.version,
        artifact_id=artifact_id,
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

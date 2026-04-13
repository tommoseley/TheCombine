"""
Scaffolding routes: create/delete workflow, doc type, schema, template, role, DCW.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.services.workspace_service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    ArtifactError,
    ArtifactNotFoundError,
    ArtifactIdError,
    get_workspace_service,
)
from app.api.v1.routers.admin_workspaces_common import (
    CreateDcwWorkflowRequest,
    CreateDcwWorkflowResponse,
    CreateDocumentTypeRequest,
    CreateDocumentTypeResponse,
    CreateOrchestrationWorkflowRequest,
    CreateOrchestrationWorkflowResponse,
    CreateRolePromptRequest,
    CreateRolePromptResponse,
    CreateSchemaRequest,
    CreateSchemaResponse,
    CreateTemplateRequest,
    CreateTemplateResponse,
)


router = APIRouter(tags=["admin-workspaces"])


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

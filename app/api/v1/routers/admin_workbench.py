"""
Admin Workbench API endpoints.

Per ADR-044, these endpoints provide read access to Git-canonical
configuration from combine-config/.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.services.admin_workbench_service import (
    AdminWorkbenchService,
    get_admin_workbench_service,
)
from app.config.package_loader import (
    PackageNotFoundError,
    VersionNotFoundError,
)


router = APIRouter(prefix="/admin/workbench", tags=["admin-workbench"])


# ===========================================================================
# Response Models
# ===========================================================================

class DocumentTypeSummary(BaseModel):
    """Summary of a document type for list responses."""
    doc_type_id: str
    display_name: str
    active_version: Optional[str] = None
    authority_level: Optional[str] = None
    creation_mode: Optional[str] = None
    scope: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None


class DocumentTypeListResponse(BaseModel):
    """Response for list document types endpoint."""
    document_types: List[DocumentTypeSummary]
    total: int


class DocumentTypeDetail(BaseModel):
    """Full document type details."""
    doc_type_id: str
    display_name: str
    version: str
    description: str
    authority_level: str
    creation_mode: str
    production_mode: Optional[str] = None
    scope: str
    required_inputs: List[str] = Field(default_factory=list)
    optional_inputs: List[str] = Field(default_factory=list)
    creates_children: List[str] = Field(default_factory=list)
    parent_doc_type: Optional[str] = None
    role_prompt_ref: Optional[str] = None
    template_ref: Optional[str] = None
    qa_template_ref: Optional[str] = None
    pgc_template_ref: Optional[str] = None
    schema_ref: Optional[str] = None
    workflow_ref: Optional[str] = None
    requires_pgc: bool
    is_llm_generated: bool
    artifacts: Dict[str, Optional[str]]
    ui: Dict[str, Any]


class DocumentTypeVersionsResponse(BaseModel):
    """Response for document type versions endpoint."""
    doc_type_id: str
    versions: List[str]
    active_version: Optional[str] = None


class RoleSummary(BaseModel):
    """Summary of a role for list responses."""
    role_id: str
    active_version: Optional[str] = None
    content_preview: Optional[str] = None
    error: Optional[str] = None


class RoleListResponse(BaseModel):
    """Response for list roles endpoint."""
    roles: List[RoleSummary]
    total: int


class RoleDetail(BaseModel):
    """Full role details."""
    role_id: str
    version: str
    content: str


class TemplateSummary(BaseModel):
    """Summary of a template for list responses."""
    template_id: str
    active_version: Optional[str] = None
    content_preview: Optional[str] = None
    error: Optional[str] = None


class TemplateListResponse(BaseModel):
    """Response for list templates endpoint."""
    templates: List[TemplateSummary]
    total: int


class TemplateDetail(BaseModel):
    """Full template details."""
    template_id: str
    version: str
    content: str


class WorkflowPlanSummary(BaseModel):
    """Summary of a workflow plan for list responses."""
    workflow_id: str
    name: str
    active_version: Optional[str] = None
    description: Optional[str] = None
    node_count: int = 0
    edge_count: int = 0
    error: Optional[str] = None


class WorkflowPlanListResponse(BaseModel):
    """Response for list workflows endpoint."""
    workflows: List[WorkflowPlanSummary]
    total: int


class WorkflowPlanDetail(BaseModel):
    """Full workflow plan details."""
    workflow_id: str
    version: str
    definition: Dict[str, Any]


class OrchestrationWorkflowSummary(BaseModel):
    """Summary of a project orchestration workflow (step-based)."""
    workflow_id: str
    name: str
    active_version: Optional[str] = None
    description: Optional[str] = None
    step_count: int = 0
    schema_version: str = "workflow.v1"
    error: Optional[str] = None


class OrchestrationWorkflowListResponse(BaseModel):
    """Response for list orchestration workflows endpoint."""
    workflows: List[OrchestrationWorkflowSummary]
    total: int


class SchemaSummary(BaseModel):
    """Summary of a standalone schema for list responses."""
    schema_id: str
    active_version: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None


class SchemaListResponse(BaseModel):
    """Response for list schemas endpoint."""
    schemas: List[SchemaSummary]
    total: int


class StandaloneSchemaDetail(BaseModel):
    """Full standalone schema details."""
    schema_id: str
    version: str
    content: Dict[str, Any]


class ActiveReleasesResponse(BaseModel):
    """Response for active releases endpoint."""
    document_types: Dict[str, str]
    roles: Dict[str, str]
    templates: Dict[str, str]
    schemas: Dict[str, str] = Field(default_factory=dict)
    workflows: Dict[str, str]


class PromptContentResponse(BaseModel):
    """Response for prompt content endpoints."""
    doc_type_id: str
    version: str
    content: Optional[str] = None


class SchemaResponse(BaseModel):
    """Response for schema endpoint."""
    doc_type_id: str
    version: str
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")

    model_config = {"populate_by_name": True}


class AssembledPromptResponse(BaseModel):
    """Response for assembled prompt endpoint."""
    doc_type_id: str
    version: str
    prompt: Optional[str] = None


# ===========================================================================
# Document Type Endpoints
# ===========================================================================

@router.get(
    "/document-types",
    response_model=DocumentTypeListResponse,
    summary="List document types",
    description="List all available document types with summary info.",
)
async def list_document_types(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> DocumentTypeListResponse:
    """List all document types."""
    summaries = service.list_document_types()
    return DocumentTypeListResponse(
        document_types=[DocumentTypeSummary(**s) for s in summaries],
        total=len(summaries),
    )


@router.get(
    "/document-types/{doc_type_id}",
    response_model=DocumentTypeDetail,
    summary="Get document type",
    description="Get full details of a document type.",
    responses={
        404: {"description": "Document type not found"},
    },
)
async def get_document_type(
    doc_type_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> DocumentTypeDetail:
    """Get document type details."""
    try:
        details = service.get_document_type(doc_type_id, version)
        return DocumentTypeDetail(**details)
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_TYPE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/document-types/{doc_type_id}/versions",
    response_model=DocumentTypeVersionsResponse,
    summary="List document type versions",
    description="List all available versions of a document type.",
)
async def list_document_type_versions(
    doc_type_id: str,
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> DocumentTypeVersionsResponse:
    """List versions of a document type."""
    versions = service.get_document_type_versions(doc_type_id)
    active = service.get_active_releases()
    return DocumentTypeVersionsResponse(
        doc_type_id=doc_type_id,
        versions=versions,
        active_version=active["document_types"].get(doc_type_id),
    )


@router.get(
    "/document-types/{doc_type_id}/task-prompt",
    response_model=PromptContentResponse,
    summary="Get task prompt",
    description="Get the task prompt content for a document type.",
    responses={
        404: {"description": "Document type not found"},
    },
)
async def get_task_prompt(
    doc_type_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> PromptContentResponse:
    """Get task prompt content."""
    try:
        content = service.get_task_prompt(doc_type_id, version)
        details = service.get_document_type(doc_type_id, version)
        return PromptContentResponse(
            doc_type_id=doc_type_id,
            version=details["version"],
            content=content,
        )
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_TYPE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/document-types/{doc_type_id}/schema",
    response_model=SchemaResponse,
    summary="Get output schema",
    description="Get the output schema for a document type.",
    responses={
        404: {"description": "Document type not found"},
    },
)
async def get_schema(
    doc_type_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> SchemaResponse:
    """Get output schema."""
    try:
        schema = service.get_schema(doc_type_id, version)
        details = service.get_document_type(doc_type_id, version)
        return SchemaResponse(
            doc_type_id=doc_type_id,
            version=details["version"],
            schema=schema,
        )
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_TYPE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/document-types/{doc_type_id}/pgc-context",
    response_model=PromptContentResponse,
    summary="Get PGC context",
    description="Get the PGC context content for a document type.",
    responses={
        404: {"description": "Document type not found"},
    },
)
async def get_pgc_context(
    doc_type_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> PromptContentResponse:
    """Get PGC context content."""
    try:
        content = service.get_pgc_context(doc_type_id, version)
        details = service.get_document_type(doc_type_id, version)
        return PromptContentResponse(
            doc_type_id=doc_type_id,
            version=details["version"],
            content=content,
        )
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_TYPE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/document-types/{doc_type_id}/assembled-prompt",
    response_model=AssembledPromptResponse,
    summary="Get assembled prompt",
    description="Get the fully assembled prompt (role + task + schema) for a document type.",
    responses={
        404: {"description": "Document type not found"},
    },
)
async def get_assembled_prompt(
    doc_type_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> AssembledPromptResponse:
    """Get assembled prompt."""
    try:
        prompt = service.assemble_prompt(doc_type_id, version)
        details = service.get_document_type(doc_type_id, version)
        return AssembledPromptResponse(
            doc_type_id=doc_type_id,
            version=details["version"],
            prompt=prompt,
        )
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_TYPE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


# ===========================================================================
# Role Endpoints
# ===========================================================================

@router.get(
    "/roles",
    response_model=RoleListResponse,
    summary="List roles",
    description="List all available role prompts.",
)
async def list_roles(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> RoleListResponse:
    """List all roles."""
    summaries = service.list_roles()
    return RoleListResponse(
        roles=[RoleSummary(**s) for s in summaries],
        total=len(summaries),
    )


@router.get(
    "/roles/{role_id}",
    response_model=RoleDetail,
    summary="Get role",
    description="Get full details of a role prompt.",
    responses={
        404: {"description": "Role not found"},
    },
)
async def get_role(
    role_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> RoleDetail:
    """Get role details."""
    try:
        details = service.get_role(role_id, version)
        return RoleDetail(**details)
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ROLE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


# ===========================================================================
# Template Endpoints
# ===========================================================================

@router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="List templates",
    description="List all available templates.",
)
async def list_templates(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> TemplateListResponse:
    """List all templates."""
    summaries = service.list_templates()
    return TemplateListResponse(
        templates=[TemplateSummary(**s) for s in summaries],
        total=len(summaries),
    )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateDetail,
    summary="Get template",
    description="Get full details of a template.",
    responses={
        404: {"description": "Template not found"},
    },
)
async def get_template(
    template_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> TemplateDetail:
    """Get template details."""
    try:
        details = service.get_template(template_id, version)
        return TemplateDetail(**details)
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "TEMPLATE_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


# ===========================================================================
# Schema Endpoints
# ===========================================================================

@router.get(
    "/schemas",
    response_model=SchemaListResponse,
    summary="List standalone schemas",
    description="List all available standalone schemas.",
)
async def list_schemas(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> SchemaListResponse:
    """List all standalone schemas."""
    summaries = service.list_schemas()
    return SchemaListResponse(
        schemas=[SchemaSummary(**s) for s in summaries],
        total=len(summaries),
    )


@router.get(
    "/schemas/{schema_id}",
    response_model=StandaloneSchemaDetail,
    summary="Get standalone schema",
    description="Get a standalone schema's content.",
    responses={
        404: {"description": "Schema not found"},
    },
)
async def get_standalone_schema(
    schema_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> StandaloneSchemaDetail:
    """Get standalone schema details."""
    try:
        details = service.get_standalone_schema(schema_id, version)
        return StandaloneSchemaDetail(**details)
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "SCHEMA_NOT_FOUND", "message": str(e)},
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VERSION_NOT_FOUND", "message": str(e)},
        )


# ===========================================================================
# Workflow Endpoints
# ===========================================================================

@router.get(
    "/workflows",
    response_model=WorkflowPlanListResponse,
    summary="List workflow plans",
    description="List all available workflow plans (ADR-039 graph-based format).",
)
async def list_workflows(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> WorkflowPlanListResponse:
    """List all workflow plans."""
    summaries = service.list_workflows()
    return WorkflowPlanListResponse(
        workflows=[WorkflowPlanSummary(**s) for s in summaries],
        total=len(summaries),
    )


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowPlanDetail,
    summary="Get workflow plan",
    description="Get full details of a workflow plan.",
    responses={
        404: {"description": "Workflow not found"},
    },
)
async def get_workflow(
    workflow_id: str,
    version: Optional[str] = Query(None, description="Specific version (default: active)"),
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> WorkflowPlanDetail:
    """Get workflow plan details."""
    try:
        details = service.get_workflow(workflow_id, version)
        return WorkflowPlanDetail(**details)
    except PackageNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "WORKFLOW_NOT_FOUND", "message": str(e)},
        )


# ===========================================================================
# Orchestration Workflow Endpoints
# ===========================================================================

@router.get(
    "/orchestration-workflows",
    response_model=OrchestrationWorkflowListResponse,
    summary="List orchestration workflows",
    description="List project orchestration workflows (step-based format).",
)
async def list_orchestration_workflows(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> OrchestrationWorkflowListResponse:
    """List project orchestration workflows."""
    summaries = service.list_orchestration_workflows()
    return OrchestrationWorkflowListResponse(
        workflows=[OrchestrationWorkflowSummary(**s) for s in summaries],
        total=len(summaries),
    )


# ===========================================================================
# Active Releases Endpoint
# ===========================================================================

@router.get(
    "/active-releases",
    response_model=ActiveReleasesResponse,
    summary="Get active releases",
    description="Get the current active release pointers.",
)
async def get_active_releases(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> ActiveReleasesResponse:
    """Get active releases."""
    active = service.get_active_releases()
    return ActiveReleasesResponse(**active)


# ===========================================================================
# Cache Management Endpoint
# ===========================================================================

@router.post(
    "/cache/invalidate",
    summary="Invalidate cache",
    description="Invalidate the package loader cache to reload from disk.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def invalidate_cache(
    service: AdminWorkbenchService = Depends(get_admin_workbench_service),
) -> None:
    """Invalidate cache."""
    service.invalidate_cache()

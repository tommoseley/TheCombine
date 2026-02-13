"""Workflow definition endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_workflow_registry
from app.api.v1.schemas import (
    WorkflowListResponse,
    WorkflowSummary,
    WorkflowDetail,
    ScopeResponse,
    DocumentTypeResponse,
    EntityTypeResponse,
    StepSummary,
    ErrorResponse,
)
from app.domain.workflow import WorkflowRegistry, WorkflowNotFoundError


router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get(
    "",
    response_model=WorkflowListResponse,
    summary="List available workflows",
    description="Returns all loaded workflow definitions.",
)
async def list_workflows(
    registry: WorkflowRegistry = Depends(get_workflow_registry),
) -> WorkflowListResponse:
    """List all available workflow definitions."""
    workflows = []
    for wf_id in registry.list_ids():
        workflow = registry.get(wf_id)
        workflows.append(WorkflowSummary(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            revision=workflow.revision,
            effective_date=workflow.effective_date,
            step_count=len(workflow.steps),
        ))
    
    return WorkflowListResponse(
        workflows=workflows,
        total=len(workflows),
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetail,
    summary="Get workflow definition",
    description="Returns full details of a specific workflow.",
    responses={
        404: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def get_workflow(
    workflow_id: str,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
) -> WorkflowDetail:
    """Get a specific workflow definition by ID."""
    try:
        workflow = registry.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKFLOW_NOT_FOUND",
                "message": f"Workflow '{workflow_id}' not found",
            },
        )
    
    # Convert to response model
    scopes = {
        scope_id: ScopeResponse(name=scope_id, parent=scope.parent)
        for scope_id, scope in workflow.scopes.items()
    }
    
    doc_types = {
        dt_id: DocumentTypeResponse(
            name=dt.name,
            scope=dt.scope,
            acceptance_required=dt.acceptance_required or False,
            accepted_by=dt.accepted_by or [],
        )
        for dt_id, dt in workflow.document_types.items()
    }
    
    entity_types = {
        et_id: EntityTypeResponse(
            name=et.name,
            parent_doc_type=et.parent_doc_type,
            creates_scope=et.creates_scope,
        )
        for et_id, et in workflow.entity_types.items()
    }
    
    steps = [
        StepSummary(
            step_id=step.step_id,
            scope=step.scope,
            role=step.role,
            produces=step.produces,
            is_iteration=step.is_iteration,
        )
        for step in workflow.steps
    ]
    
    return WorkflowDetail(
        workflow_id=workflow.workflow_id,
        name=workflow.name,
        description=workflow.description,
        schema_version=workflow.schema_version,
        revision=workflow.revision,
        effective_date=workflow.effective_date,
        scopes=scopes,
        document_types=doc_types,
        entity_types=entity_types,
        steps=steps,
    )


@router.get(
    "/{workflow_id}/steps/{step_id}/schema",
    summary="Get step output schema",
    description="Returns the JSON schema for a step's output document.",
    responses={
        200: {"description": "JSON schema for the step output"},
        404: {"model": ErrorResponse, "description": "Workflow or step not found"},
    },
)
async def get_step_schema(
    workflow_id: str,
    step_id: str,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
):
    """Get the output schema for a specific workflow step."""
    try:
        workflow = registry.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKFLOW_NOT_FOUND",
                "message": f"Workflow '{workflow_id}' not found",
            },
        )
    
    # Find the step
    step = None
    for s in workflow.steps:
        if s.step_id == step_id:
            step = s
            break
    
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "STEP_NOT_FOUND",
                "message": f"Step '{step_id}' not found in workflow '{workflow_id}'",
            },
        )
    
    # Get the document type produced by this step
    doc_type = step.produces
    if not doc_type or doc_type not in workflow.document_types:
        return {"type": "object", "description": f"Output for step {step_id}"}
    
    # Return a basic schema structure
    doc_config = workflow.document_types[doc_type]
    return {
        "type": "object",
        "title": doc_config.name,
        "description": f"Output schema for {doc_config.name}",
        "properties": {},
    }

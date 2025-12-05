"""Pipeline lifecycle endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

# from app.orchestrator_api.main import get_orchestrator
from app.orchestrator_api.dependencies import require_api_key, get_orchestrator
from app.orchestrator_api.schemas.requests import PipelineStartRequest
from app.orchestrator_api.schemas.responses import (
    PipelineCreatedResponse,
    PipelineStatusResponse,
    PhaseAdvancedResponse,
    ErrorResponse
)
from app.orchestrator_api.services.pipeline_service import PipelineService
from workforce.utils.errors import InvalidStateTransitionError

router = APIRouter()


@router.post(
    "",  # POST /pipelines
    response_model=PipelineCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    dependencies=[Depends(require_api_key)]
)
async def create_pipeline(request: PipelineStartRequest):
    """
    Create a new pipeline for an Epic.
    
    Creates pipeline record in database (source of truth),
    returns pipeline ID for subsequent operations.
    
    Requires authentication.
    """
    orchestrator = get_orchestrator()
    service = PipelineService(orchestrator)
    
    try:
        response = service.start_pipeline(
            epic_id=request.epic_id,
            initial_context=request.initial_context
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Failed to create pipeline: {str(e)}"
            }
        )


@router.get(
    "/{pipeline_id}",  # GET /pipelines/{pipeline_id}
    response_model=PipelineStatusResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_pipeline(pipeline_id: str):
    """
    Get current status of a pipeline.
    
    Returns complete pipeline state including artifacts,
    phase history, and metadata.
    
    No authentication required for read operations.
    """
    orchestrator = get_orchestrator()
    service = PipelineService(orchestrator)
    
    status_response = service.get_status(pipeline_id)
    if not status_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Pipeline not found: {pipeline_id}"
            }
        )
    
    return status_response


@router.post(
    "/{pipeline_id}/advance",  # POST /pipelines/{pipeline_id}/advance
    response_model=PhaseAdvancedResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    },
    dependencies=[Depends(require_api_key)]
)
async def advance_pipeline(pipeline_id: str):
    """
    Advance pipeline to next phase in sequence.
    
    Validates transition is legal, updates state in database,
    records transition in audit log.
    
    Requires authentication.
    """
    orchestrator = get_orchestrator()
    service = PipelineService(orchestrator)
    
    try:
        response = service.advance_phase(pipeline_id)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": str(e)
            }
        )
    except InvalidStateTransitionError as e:
        # Get current pipeline state for error details
        status_response = service.get_status(pipeline_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "invalid_transition",
                "message": str(e),
                "details": {
                    "current_phase": status_response.current_phase if status_response else "unknown"
                }
            }
        )
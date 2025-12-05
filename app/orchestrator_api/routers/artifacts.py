"""Artifact submission endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.orchestrator_api.dependencies import require_api_key
from app.orchestrator_api.schemas.requests import ArtifactSubmissionRequest
from app.orchestrator_api.schemas.responses import ArtifactSubmittedResponse, ErrorResponse
from app.orchestrator_api.services.artifact_service import ArtifactService, ArtifactValidationError
from app.orchestrator_api.dependencies import require_api_key  # ← No change neededvvvvvvvvvvvvvv

router = APIRouter()


@router.post(
    "/{pipeline_id}/artifacts",  # POST /pipelines/{pipeline_id}/artifacts
    response_model=ArtifactSubmittedResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    },
    dependencies=[Depends(require_api_key)]
)
async def submit_artifact(pipeline_id: str, artifact_request: ArtifactSubmissionRequest, request: Request):
    """
    Submit artifact for a pipeline phase.
    
    Validates:
    - Pipeline exists
    - Phase is valid enum value
    - Phase matches current pipeline phase
    - Artifact type correct for phase
    - Payload conforms to schema
    - Artifact epicId matches pipeline epic_id
    
    Requires authentication.
    """
    service = ArtifactService()
    
    # Get request ID for error responses
    request_id = getattr(request.state, "request_id", None)
    
    try:
        response = service.submit_artifact(
            pipeline_id=pipeline_id,
            phase=artifact_request.phase,
            mentor_role=artifact_request.mentor_role,
            artifact_type=artifact_request.artifact_type,
            payload=artifact_request.payload
        )
        return response
    
    except ValueError as e:
        # Pipeline not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": str(e),
                "request_id": request_id
            }
        )
    
    except ArtifactValidationError as e:
        # Validation failed
        if "phase" in e.message.lower():
            # Phase mismatch
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "phase_mismatch",
                    "message": e.message,
                    "details": e.details,
                    "request_id": request_id
                }
            )
        else:
            # Schema validation failed
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "validation_failed",
                    "message": e.message,
                    "details": e.details,
                    "request_id": request_id
                }
            )
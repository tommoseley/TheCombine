"""Administrative endpoints: reset, canon inspection."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.orchestrator_api.dependencies import require_api_key, get_orchestrator
from app.orchestrator_api.dependencies import require_api_key
from app.orchestrator_api.schemas.responses import ResetResponse, CanonVersionResponse, ErrorResponse
from app.orchestrator_api.services.reset_service import ResetService


router = APIRouter()


@router.post(
    "/reset",
    response_model=ResetResponse,
    responses={
        409: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    },
    dependencies=[Depends(require_api_key)]
)
async def reset_orchestrator():
    """
    Reset Orchestrator state with guardrails.
    
    Behavior (MVP):
    - Reloads canon from disk
    - Clears Orchestrator's in-memory cache
    - PRESERVES all persisted data (pipelines, artifacts, transitions)
    - Counts in-flight pipelines and warns
    - Blocked in critical phases if ALLOW_RESET_IN_CRITICAL_PHASES=false
    
    Requires authentication.
    """
    orchestrator = get_orchestrator()
    service = ResetService(orchestrator)
    
    result = service.perform_reset()
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "reset_blocked",
                "message": result.reason
            }
        )
    
    return result


@router.get(
    "/canon/version",
    response_model=CanonVersionResponse
)
async def get_canon_version():
    """
    Get current canon version and metadata.
    
    Returns PIPELINE_FLOW_VERSION, load timestamp,
    source path, and file size.
    
    No authentication required.
    """
    orchestrator = get_orchestrator()
    canon_manager = orchestrator.canon_manager
    
    version = canon_manager.version_store.get_current_version()
    loaded_at = canon_manager.version_store.get_loaded_at()
    content = canon_manager.version_store.get_current_content()
    
    # Get source path from canon loader
    # Note: This is simplified - actual implementation would track source path
    source_path = "workforce/canon/pipeline_flow.md"
    file_size_bytes = len(content) if content else 0
    
    return CanonVersionResponse(
        version=str(version),
        loaded_at=loaded_at,
        source_path=source_path,
        file_size_bytes=file_size_bytes
    )
"""
Admin Release Management API endpoints.

Per ADR-044 WS-044-07, these endpoints provide:
- Release lifecycle management (Draft -> Staged -> Released)
- Instantaneous rollback via pointer change
- Audit trail for release changes
- Immutability enforcement for released versions
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.services.release_service import (
    ReleaseService,
    ReleaseInfo,
    ReleaseState,
    ReleaseHistoryEntry,
    RollbackResult,
    ReleaseServiceError,
    ImmutabilityViolationError,
    ValidationFailedError,
    get_release_service,
)


router = APIRouter(prefix="/admin/releases", tags=["admin-releases"])


# ===========================================================================
# Response Models
# ===========================================================================

class ReleaseInfoResponse(BaseModel):
    """Release information response."""
    doc_type_id: str
    version: str
    state: str
    is_active: bool
    commit_hash: Optional[str] = None
    commit_date: Optional[datetime] = None
    commit_author: Optional[str] = None
    commit_message: Optional[str] = None


class ReleaseListResponse(BaseModel):
    """List of releases response."""
    doc_type_id: str
    releases: List[ReleaseInfoResponse]
    active_version: Optional[str] = None
    total: int


class ReleaseHistoryEntryResponse(BaseModel):
    """Release history entry response."""
    doc_type_id: str
    action: str
    version: str
    previous_version: Optional[str] = None
    commit_hash: str
    commit_date: datetime
    author: str
    message: str


class ReleaseHistoryResponse(BaseModel):
    """Release history response."""
    entries: List[ReleaseHistoryEntryResponse]
    total: int


class ActivateReleaseRequest(BaseModel):
    """Request to activate a release."""
    version: str
    user_name: str
    user_email: Optional[str] = None
    skip_validation: bool = Field(
        default=False,
        description="Skip validation (NOT RECOMMENDED)",
    )


class RollbackRequest(BaseModel):
    """Request to rollback a release."""
    target_version: str
    user_name: str
    user_email: Optional[str] = None
    reason: Optional[str] = Field(
        None,
        description="Reason for rollback (included in audit trail)",
    )


class RollbackResponse(BaseModel):
    """Rollback result response."""
    doc_type_id: str
    rolled_back_from: str
    rolled_back_to: str
    commit_hash: str
    commit_message: str


class ImmutabilityCheckResponse(BaseModel):
    """Immutability check response."""
    doc_type_id: str
    version: str
    is_immutable: bool
    reason: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error details."""
    rule_id: str
    severity: str
    message: str
    file_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ActivationValidationResponse(BaseModel):
    """Response when activation fails validation."""
    error_code: str
    message: str
    valid: bool
    error_count: int
    errors: List[ValidationErrorResponse]


# ===========================================================================
# Global History Endpoint (must be before /{doc_type_id} routes)
# ===========================================================================

@router.get(
    "/history/all",
    response_model=ReleaseHistoryResponse,
    summary="Get all release history",
    description="Get audit trail of all release changes across all document types.",
)
async def get_all_release_history(
    limit: int = Query(default=50, ge=1, le=200),
    service: ReleaseService = Depends(get_release_service),
) -> ReleaseHistoryResponse:
    """Get release history for all document types."""
    history = service.get_release_history(doc_type_id=None, limit=limit)
    return ReleaseHistoryResponse(
        entries=[
            ReleaseHistoryEntryResponse(
                doc_type_id=e.doc_type_id,
                action=e.action,
                version=e.version,
                previous_version=e.previous_version,
                commit_hash=e.commit_hash,
                commit_date=e.commit_date,
                author=e.author,
                message=e.message,
            )
            for e in history
        ],
        total=len(history),
    )


# ===========================================================================
# Release Information Endpoints
# ===========================================================================

@router.get(
    "/{doc_type_id}",
    response_model=ReleaseListResponse,
    summary="List releases",
    description="List all releases for a document type.",
)
async def list_releases(
    doc_type_id: str,
    service: ReleaseService = Depends(get_release_service),
) -> ReleaseListResponse:
    """List all releases for a document type."""
    try:
        releases = service.list_releases(doc_type_id)
        active_version = service.get_active_version(doc_type_id)

        return ReleaseListResponse(
            doc_type_id=doc_type_id,
            releases=[
                ReleaseInfoResponse(
                    doc_type_id=r.doc_type_id,
                    version=r.version,
                    state=r.state.value,
                    is_active=r.is_active,
                    commit_hash=r.commit_hash,
                    commit_date=r.commit_date,
                    commit_author=r.commit_author,
                    commit_message=r.commit_message,
                )
                for r in releases
            ],
            active_version=active_version,
            total=len(releases),
        )
    except ReleaseServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "RELEASE_ERROR", "message": str(e)},
        )


# ===========================================================================
# Doc Type-Specific Routes (must be BEFORE /{doc_type_id}/{version})
# ===========================================================================

@router.get(
    "/{doc_type_id}/history",
    response_model=ReleaseHistoryResponse,
    summary="Get release history",
    description="Get audit trail of release changes for a document type.",
)
async def get_release_history(
    doc_type_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ReleaseService = Depends(get_release_service),
) -> ReleaseHistoryResponse:
    """Get release history for a document type."""
    history = service.get_release_history(doc_type_id=doc_type_id, limit=limit)
    return ReleaseHistoryResponse(
        entries=[
            ReleaseHistoryEntryResponse(
                doc_type_id=e.doc_type_id,
                action=e.action,
                version=e.version,
                previous_version=e.previous_version,
                commit_hash=e.commit_hash,
                commit_date=e.commit_date,
                author=e.author,
                message=e.message,
            )
            for e in history
        ],
        total=len(history),
    )


# ===========================================================================
# Release Activation Endpoints
# ===========================================================================

@router.post(
    "/{doc_type_id}/activate",
    response_model=ReleaseInfoResponse,
    summary="Activate release",
    description="Activate a release version. Validates cross-package dependencies first.",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ActivationValidationResponse,
            "description": "Validation failed",
        },
    },
)
async def activate_release(
    doc_type_id: str,
    request: ActivateReleaseRequest,
    service: ReleaseService = Depends(get_release_service),
) -> ReleaseInfoResponse:
    """Activate a release version."""
    try:
        info = service.activate_release(
            doc_type_id=doc_type_id,
            version=request.version,
            user_name=request.user_name,
            user_email=request.user_email,
            skip_validation=request.skip_validation,
        )
        return ReleaseInfoResponse(
            doc_type_id=info.doc_type_id,
            version=info.version,
            state=info.state.value,
            is_active=info.is_active,
            commit_hash=info.commit_hash,
            commit_date=info.commit_date,
            commit_author=info.commit_author,
            commit_message=info.commit_message,
        )
    except ValidationFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_FAILED",
                "message": str(e),
                "valid": False,
                "error_count": len(e.report.errors),
                "errors": [
                    {
                        "rule_id": err.rule_id,
                        "severity": err.severity.value,
                        "message": err.message,
                        "file_path": err.file_path,
                        "details": err.details,
                    }
                    for err in e.report.errors
                ],
            },
        )
    except ReleaseServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "RELEASE_ERROR", "message": str(e)},
        )


# ===========================================================================
# Rollback Endpoints
# ===========================================================================

@router.post(
    "/{doc_type_id}/rollback",
    response_model=RollbackResponse,
    summary="Rollback release",
    description="Rollback to a previous release version. Instantaneous via pointer change.",
    status_code=status.HTTP_201_CREATED,
)
async def rollback_release(
    doc_type_id: str,
    request: RollbackRequest,
    service: ReleaseService = Depends(get_release_service),
) -> RollbackResponse:
    """Rollback to a previous version."""
    try:
        result = service.rollback(
            doc_type_id=doc_type_id,
            target_version=request.target_version,
            user_name=request.user_name,
            user_email=request.user_email,
            reason=request.reason,
        )
        return RollbackResponse(
            doc_type_id=result.doc_type_id,
            rolled_back_from=result.rolled_back_from,
            rolled_back_to=result.rolled_back_to,
            commit_hash=result.commit_hash,
            commit_message=result.commit_message,
        )
    except ReleaseServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ROLLBACK_ERROR", "message": str(e)},
        )


# ===========================================================================
# Version-Specific Routes (AFTER fixed-suffix routes)
# ===========================================================================

@router.get(
    "/{doc_type_id}/{version}",
    response_model=ReleaseInfoResponse,
    summary="Get release info",
    description="Get information about a specific release version.",
)
async def get_release_info(
    doc_type_id: str,
    version: str,
    service: ReleaseService = Depends(get_release_service),
) -> ReleaseInfoResponse:
    """Get release information for a specific version."""
    try:
        info = service.get_release_info(doc_type_id, version)
        return ReleaseInfoResponse(
            doc_type_id=info.doc_type_id,
            version=info.version,
            state=info.state.value,
            is_active=info.is_active,
            commit_hash=info.commit_hash,
            commit_date=info.commit_date,
            commit_author=info.commit_author,
            commit_message=info.commit_message,
        )
    except ReleaseServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "RELEASE_NOT_FOUND", "message": str(e)},
        )


# ===========================================================================
# Immutability Check Endpoints
# ===========================================================================

@router.get(
    "/{doc_type_id}/{version}/immutability",
    response_model=ImmutabilityCheckResponse,
    summary="Check immutability",
    description="Check if a release version is immutable (cannot be modified).",
)
async def check_immutability(
    doc_type_id: str,
    version: str,
    service: ReleaseService = Depends(get_release_service),
) -> ImmutabilityCheckResponse:
    """Check if a version is immutable."""
    is_immutable = service.check_immutability(doc_type_id, version)
    return ImmutabilityCheckResponse(
        doc_type_id=doc_type_id,
        version=version,
        is_immutable=is_immutable,
        reason="Version is currently active and released" if is_immutable else None,
    )

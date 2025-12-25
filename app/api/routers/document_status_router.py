"""
Document Status API Endpoints (ADR-007)

Provides endpoints for:
- GET /projects/{project_id}/document-statuses - Sidebar status list
- POST /documents/{document_id}/accept - Accept a document
- POST /documents/{document_id}/reject - Reject a document
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.models.document import Document
from app.api.models.document_type import DocumentType
from app.api.services.document_status_service import (
    document_status_service,
    DocumentStatus,
)

router = APIRouter(tags=["documents"])


# =============================================================================
# SCHEMAS
# =============================================================================

class DocumentStatusResponse(BaseModel):
    """Single document status for API response."""
    doc_type_id: str
    document_id: Optional[str] = None
    title: str
    icon: str
    readiness: str
    acceptance_state: Optional[str] = None
    subtitle: Optional[str] = None
    can_build: bool
    can_rebuild: bool
    can_accept: bool
    can_reject: bool
    can_use_as_input: bool
    missing_inputs: List[str] = Field(default_factory=list)
    display_order: int = 0

    class Config:
        from_attributes = True


class ProjectDocumentStatusesResponse(BaseModel):
    """Response for project document statuses endpoint."""
    project_id: str
    documents: List[DocumentStatusResponse]


class AcceptDocumentRequest(BaseModel):
    """Request body for accepting a document."""
    accepted_by: str = Field(..., min_length=1, max_length=128)


class AcceptDocumentResponse(BaseModel):
    """Response after accepting a document."""
    document_id: str
    accepted_at: datetime
    accepted_by: str


class RejectDocumentRequest(BaseModel):
    """Request body for rejecting a document."""
    rejected_by: str = Field(..., min_length=1, max_length=128)
    reason: Optional[str] = Field(None, max_length=2000)


class RejectDocumentResponse(BaseModel):
    """Response after rejecting a document."""
    document_id: str
    rejected_at: datetime
    rejected_by: str
    reason: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "/projects/{project_id}/document-statuses",
    response_model=ProjectDocumentStatusesResponse,
    summary="Get document statuses for project sidebar",
    description="""
    Returns status for all document types in a project, ordered for sidebar display.
    
    Each document status includes:
    - **readiness**: ready, stale, blocked, or waiting
    - **acceptance_state**: accepted, needs_acceptance, rejected, or null
    - **subtitle**: Contextual hint (e.g., "Needs acceptance (PM)")
    - **can_*** flags: Action enablement for UI buttons
    - **missing_inputs**: List of blocking dependencies (when blocked)
    """
)
async def get_project_document_statuses(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ProjectDocumentStatusesResponse:
    """Get all document statuses for a project."""
    
    statuses = await document_status_service.get_project_document_statuses(db, project_id)
    
    return ProjectDocumentStatusesResponse(
        project_id=str(project_id),
        documents=[
            DocumentStatusResponse(**s.to_dict())
            for s in statuses
        ]
    )


@router.post(
    "/documents/{document_id}/accept",
    response_model=AcceptDocumentResponse,
    summary="Accept a document",
    description="""
    Mark a document as accepted by the responsible role.
    
    Requirements:
    - Document must exist
    - Document type must have acceptance_required = true
    - Clears any previous rejection
    
    This enables the document to be used as input for downstream documents.
    """
)
async def accept_document(
    document_id: UUID,
    request: AcceptDocumentRequest,
    db: AsyncSession = Depends(get_db)
) -> AcceptDocumentResponse:
    """Accept a document."""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get document type to verify acceptance is required
    result = await db.execute(
        select(DocumentType).where(DocumentType.doc_type_id == document.doc_type_id)
    )
    doc_type = result.scalar_one_or_none()
    
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document type configuration not found"
        )
    
    if not doc_type.acceptance_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document type '{doc_type.doc_type_id}' does not require acceptance"
        )
    
    # Update document
    now = datetime.now(timezone.utc)
    document.accepted_at = now
    document.accepted_by = request.accepted_by
    # Clear any rejection
    document.rejected_at = None
    document.rejected_by = None
    document.rejection_reason = None
    
    await db.commit()
    await db.refresh(document)
    
    return AcceptDocumentResponse(
        document_id=str(document.id),
        accepted_at=document.accepted_at,
        accepted_by=document.accepted_by
    )


@router.post(
    "/documents/{document_id}/reject",
    response_model=RejectDocumentResponse,
    summary="Reject a document",
    description="""
    Mark a document as rejected with optional reason.
    
    Requirements:
    - Document must exist
    - Document type must have acceptance_required = true
    - Clears any previous acceptance
    
    This prevents the document from being used as input for downstream documents
    until changes are made and it is re-accepted.
    """
)
async def reject_document(
    document_id: UUID,
    request: RejectDocumentRequest,
    db: AsyncSession = Depends(get_db)
) -> RejectDocumentResponse:
    """Reject a document."""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get document type to verify acceptance is required
    result = await db.execute(
        select(DocumentType).where(DocumentType.doc_type_id == document.doc_type_id)
    )
    doc_type = result.scalar_one_or_none()
    
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document type configuration not found"
        )
    
    if not doc_type.acceptance_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document type '{doc_type.doc_type_id}' does not require acceptance"
        )
    
    # Update document
    now = datetime.now(timezone.utc)
    document.rejected_at = now
    document.rejected_by = request.rejected_by
    document.rejection_reason = request.reason
    # Clear any acceptance
    document.accepted_at = None
    document.accepted_by = None
    
    await db.commit()
    await db.refresh(document)
    
    return RejectDocumentResponse(
        document_id=str(document.id),
        rejected_at=document.rejected_at,
        rejected_by=document.rejected_by,
        reason=document.rejection_reason
    )


@router.delete(
    "/documents/{document_id}/acceptance",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear acceptance/rejection state",
    description="""
    Reset a document's acceptance state to needs_acceptance.
    
    Useful when:
    - Document has been significantly modified
    - Re-review is required
    - Previous decision needs to be reconsidered
    """
)
async def clear_acceptance(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Clear acceptance/rejection state."""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Clear all acceptance state
    document.accepted_at = None
    document.accepted_by = None
    document.rejected_at = None
    document.rejected_by = None
    document.rejection_reason = None
    
    await db.commit()
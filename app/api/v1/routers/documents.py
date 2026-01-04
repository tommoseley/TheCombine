"""V1 Documents API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.persistence import (
    DocumentRepository,
    InMemoryDocumentRepository,
    StoredDocument,
    DocumentStatus,
)


router = APIRouter(prefix="/documents", tags=["documents"])


# Module-level repository for dependency injection
_document_repo: Optional[DocumentRepository] = None


def get_document_repository() -> DocumentRepository:
    """Get document repository instance."""
    global _document_repo
    if _document_repo is None:
        _document_repo = InMemoryDocumentRepository()
    return _document_repo


def set_document_repository(repo: DocumentRepository) -> None:
    """Set document repository (for testing/configuration)."""
    global _document_repo
    _document_repo = repo


def reset_document_repository() -> None:
    """Reset to default repository (for testing)."""
    global _document_repo
    _document_repo = None


# Response Models
class DocumentSummary(BaseModel):
    """Brief document info for list responses."""
    document_id: UUID
    document_type: str
    title: str
    version: int
    status: str
    is_latest: bool
    created_at: datetime
    updated_at: datetime


class DocumentDetail(BaseModel):
    """Full document response."""
    document_id: UUID
    document_type: str
    scope_type: str
    scope_id: str
    version: int
    title: str
    content: Dict[str, Any]
    status: str
    summary: Optional[str] = None
    is_latest: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    created_by_step: Optional[str] = None
    execution_id: Optional[UUID] = None


class DocumentListResponse(BaseModel):
    """Response for list documents endpoint."""
    documents: List[DocumentSummary]
    total: int


class DocumentVersionSummary(BaseModel):
    """Summary of a document version."""
    version: int
    document_id: UUID
    created_at: datetime
    is_latest: bool


class DocumentVersionsResponse(BaseModel):
    """Response for document versions endpoint."""
    document_type: str
    versions: List[DocumentVersionSummary]
    total: int


def _to_summary(doc: StoredDocument) -> DocumentSummary:
    """Convert StoredDocument to DocumentSummary."""
    return DocumentSummary(
        document_id=doc.document_id,
        document_type=doc.document_type,
        title=doc.title,
        version=doc.version,
        status=doc.status.value,
        is_latest=doc.is_latest,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _to_detail(doc: StoredDocument) -> DocumentDetail:
    """Convert StoredDocument to DocumentDetail."""
    return DocumentDetail(
        document_id=doc.document_id,
        document_type=doc.document_type,
        scope_type=doc.scope_type,
        scope_id=doc.scope_id,
        version=doc.version,
        title=doc.title,
        content=doc.content,
        status=doc.status.value,
        summary=doc.summary,
        is_latest=doc.is_latest,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        created_by=doc.created_by,
        created_by_step=doc.created_by_step,
        execution_id=doc.execution_id,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List documents with optional filters.",
)
async def list_documents(
    scope_type: Optional[str] = Query(None, description="Filter by scope type"),
    scope_id: Optional[str] = Query(None, description="Filter by scope ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentListResponse:
    """List documents with optional filters."""
    if scope_type and scope_id:
        documents = await repo.list_by_scope(scope_type, scope_id, document_type)
    else:
        # Without scope filter, return empty for now
        documents = []
    
    summaries = [_to_summary(d) for d in documents]
    return DocumentListResponse(documents=summaries, total=len(summaries))


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document",
    description="Get full document details by ID.",
    responses={
        404: {"description": "Document not found"},
    },
)
async def get_document(
    document_id: UUID,
    repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentDetail:
    """Get a specific document by ID."""
    doc = await repo.get(document_id)
    
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "DOCUMENT_NOT_FOUND",
                "message": f"Document not found: {document_id}",
            },
        )
    
    return _to_detail(doc)


@router.get(
    "/by-scope/{scope_type}/{scope_id}/{document_type}",
    response_model=DocumentDetail,
    summary="Get document by scope and type",
    description="Get the latest document of a type in a scope.",
    responses={
        404: {"description": "Document not found"},
    },
)
async def get_document_by_scope(
    scope_type: str,
    scope_id: str,
    document_type: str,
    version: Optional[int] = Query(None, description="Specific version (default: latest)"),
    repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentDetail:
    """Get document by scope and type."""
    doc = await repo.get_by_scope_type(scope_type, scope_id, document_type, version)
    
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "DOCUMENT_NOT_FOUND",
                "message": f"Document not found: {document_type} in {scope_type}/{scope_id}",
            },
        )
    
    return _to_detail(doc)


@router.get(
    "/by-scope/{scope_type}/{scope_id}/{document_type}/versions",
    response_model=DocumentVersionsResponse,
    summary="Get document versions",
    description="Get all versions of a document type in a scope.",
)
async def get_document_versions(
    scope_type: str,
    scope_id: str,
    document_type: str,
    repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentVersionsResponse:
    """Get all versions of a document."""
    documents = await repo.list_by_scope(scope_type, scope_id, document_type)
    
    versions = [
        DocumentVersionSummary(
            version=doc.version,
            document_id=doc.document_id,
            created_at=doc.created_at,
            is_latest=doc.is_latest,
        )
        for doc in sorted(documents, key=lambda d: d.version, reverse=True)
    ]
    
    return DocumentVersionsResponse(
        document_type=document_type,
        versions=versions,
        total=len(versions),
    )

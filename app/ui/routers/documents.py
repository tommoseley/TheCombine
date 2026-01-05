"""Document pages for UI."""

from typing import Optional
from uuid import UUID

from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.persistence import (
    DocumentRepository,
    InMemoryDocumentRepository,
    StoredDocument,
)


router = APIRouter(prefix="/admin", tags=["admin-documents"], dependencies=[Depends(require_admin)])

templates = Jinja2Templates(directory="app/ui/templates")


# Module-level repository
_document_repo: Optional[DocumentRepository] = None


def get_document_repo() -> DocumentRepository:
    """Get document repository."""
    global _document_repo
    if _document_repo is None:
        _document_repo = InMemoryDocumentRepository()
    return _document_repo


def set_document_repo(repo: DocumentRepository) -> None:
    """Set document repository (for testing)."""
    global _document_repo
    _document_repo = repo


def reset_document_repo() -> None:
    """Reset document repository."""
    global _document_repo
    _document_repo = None


@router.get("/documents", response_class=HTMLResponse)
async def documents_list(
    request: Request,
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    repo: DocumentRepository = Depends(get_document_repo),
):
    """Render documents list page."""
    documents = []
    
    if scope_type and scope_id:
        docs = await repo.list_by_scope(scope_type, scope_id, document_type)
        documents = [
            {
                "document_id": str(d.document_id),
                "document_type": d.document_type,
                "title": d.title,
                "version": d.version,
                "status": d.status.value,
                "is_latest": d.is_latest,
                "created_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else None,
                "updated_at": d.updated_at.strftime("%Y-%m-%d %H:%M") if d.updated_at else None,
            }
            for d in docs
        ]
    
    return templates.TemplateResponse(
        request,
        "pages/documents/list.html",
        {
            "active_page": "documents",
            "documents": documents,
            "filters": {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "document_type": document_type,
            },
        },
    )


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail(
    request: Request,
    document_id: str,
    repo: DocumentRepository = Depends(get_document_repo),
):
    """Render document detail page."""
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "documents",
                "error_code": 400,
                "error_message": "Invalid document ID format",
            },
            status_code=400,
        )
    
    doc = await repo.get(doc_uuid)
    
    if doc is None:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "documents",
                "error_code": 404,
                "error_message": f"Document '{document_id}' not found",
            },
            status_code=404,
        )
    
    document = {
        "document_id": str(doc.document_id),
        "document_type": doc.document_type,
        "scope_type": doc.scope_type,
        "scope_id": doc.scope_id,
        "title": doc.title,
        "version": doc.version,
        "status": doc.status.value,
        "is_latest": doc.is_latest,
        "content": doc.content,
        "summary": doc.summary,
        "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else None,
        "updated_at": doc.updated_at.strftime("%Y-%m-%d %H:%M:%S") if doc.updated_at else None,
        "created_by": doc.created_by,
        "created_by_step": doc.created_by_step,
    }
    
    return templates.TemplateResponse(
        request,
        "pages/documents/detail.html",
        {
            "active_page": "documents",
            "document": document,
        },
    )


@router.get("/documents/{document_id}/versions", response_class=HTMLResponse)
async def document_versions(
    request: Request,
    document_id: str,
    repo: DocumentRepository = Depends(get_document_repo),
):
    """Render document versions page."""
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "documents",
                "error_code": 400,
                "error_message": "Invalid document ID format",
            },
            status_code=400,
        )
    
    doc = await repo.get(doc_uuid)
    
    if doc is None:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "documents",
                "error_code": 404,
                "error_message": f"Document '{document_id}' not found",
            },
            status_code=404,
        )
    
    # Get all versions
    all_docs = await repo.list_by_scope(doc.scope_type, doc.scope_id, doc.document_type)
    
    versions = [
        {
            "document_id": str(d.document_id),
            "version": d.version,
            "is_latest": d.is_latest,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else None,
            "created_by": d.created_by,
        }
        for d in sorted(all_docs, key=lambda x: x.version, reverse=True)
    ]
    
    return templates.TemplateResponse(
        request,
        "pages/documents/versions.html",
        {
            "active_page": "documents",
            "document": {
                "document_id": str(doc.document_id),
                "document_type": doc.document_type,
                "title": doc.title,
            },
            "versions": versions,
        },
    )

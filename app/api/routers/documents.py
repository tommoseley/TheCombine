"""
Documents API Routes - Unified endpoint for building any document type.

Uses the new document-centric model with:
- Documents (space_type + space_id ownership)
- Document Relations (requires, derived_from)
- Document Types registry

Week 2 (ADR-010): Integrated correlation_id for LLM execution logging.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.services.document_builder import DocumentBuilder
from app.domain.registry.loader import (
    list_document_types,
    get_document_config,
    DocumentNotFoundError,
)
from app.domain.handlers import get_handler, HandlerNotFoundError

# Import services
from app.api.services.role_prompt_service import RolePromptService
from app.api.services.document_service import DocumentService
from app.core.dependencies import get_llm_execution_logger
from app.domain.services.llm_execution_logger import LLMExecutionLogger

router = APIRouter(prefix="/api/documents", tags=["documents"])


# =============================================================================
# PROMPT SERVICE ADAPTER
# =============================================================================

class PromptServiceAdapter:
    """
    Adapts RolePromptService to DocumentBuilder's PromptServiceProtocol.
    """
    
    def __init__(self, role_prompt_service: RolePromptService):
        self.svc = role_prompt_service
    
    async def get_prompt_for_role_task(
        self,
        role_name: str,
        task_name: str
    ) -> tuple[str, str, Dict[str, Any]]:
        """Get prompt for a role/task combination."""
        composed = await self.svc.get_role_task(role_name, task_name)
        
        if not composed:
            raise ValueError(f"No prompt found for {role_name}/{task_name}")
        
        prompt_text, prompt_id = await self.svc.build_prompt(role_name, task_name)
        
        schema = composed.expected_schema or {}
        
        return prompt_text, str(prompt_id), schema


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class BuildDocumentRequest(BaseModel):
    """Request to build a document."""
    user_query: Optional[str] = Field(None, description="User's description or request")
    project_description: Optional[str] = Field(None, description="Project description")
    model: Optional[str] = Field(None, description="Model override")
    max_tokens: Optional[int] = Field(4096, description="Max tokens for generation")
    temperature: Optional[float] = Field(0.7, description="Temperature for generation")


class DocumentTypeResponse(BaseModel):
    """Document type information."""
    doc_type_id: str
    name: str
    description: Optional[str]
    category: str
    icon: str
    scope: str
    required_inputs: list[str]
    optional_inputs: list[str]
    can_build: bool = False
    missing_deps: list[str] = []


class BuildResultResponse(BaseModel):
    """Build result response."""
    success: bool
    doc_type_id: str
    document_id: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    tokens: Optional[dict] = None


class DocumentResponse(BaseModel):
    """Document response."""
    id: str
    space_type: str
    space_id: str
    doc_type_id: str
    version: int
    title: str
    status: str
    is_stale: bool
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    """Document detail with content and relations."""
    content: dict
    summary: Optional[str]
    builder_metadata: Optional[dict]
    requires: list[dict] = []
    derived_from: list[dict] = []
    required_by: list[dict] = []
    derivatives: list[dict] = []


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_document_builder(
    request: Request,  # ADR-010: Extract correlation_id
    db: AsyncSession = Depends(get_db),
    llm_logger: LLMExecutionLogger = Depends(get_llm_execution_logger),  # ADR-010
) -> DocumentBuilder:
    """
    Create DocumentBuilder with injected dependencies.
    
    Week 2: Extracts correlation_id from request.state (set by RequestIDMiddleware).
    ADR-010: Injects LLMExecutionLogger for telemetry.
    """
    role_prompt_service = RolePromptService(db)
    prompt_adapter = PromptServiceAdapter(role_prompt_service)
    document_service = DocumentService(db)
    
    # Extract correlation_id from request state (set by middleware)
    correlation_id = getattr(request.state, "correlation_id", None)
    
    return DocumentBuilder(
        db=db,
        prompt_service=prompt_adapter,
        document_service=document_service,
        correlation_id=correlation_id,  # ADR-010: Pass for telemetry
        llm_logger=llm_logger,  # ADR-010: Injected logger
    )

async def get_document_service(
    db: AsyncSession = Depends(get_db)
) -> DocumentService:
    """Get DocumentService."""
    return DocumentService(db)


# =============================================================================
# DOCUMENT TYPE ROUTES
# =============================================================================

@router.get("/types", response_model=list[DocumentTypeResponse])
async def list_types(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
):
    """List all available document types."""
    from app.domain.registry.loader import list_by_category
    
    if category:
        types = await list_by_category(db, category=category)
    else:
        types = await list_document_types(db)
    
    return [
        DocumentTypeResponse(
            doc_type_id=t["doc_type_id"],
            name=t["name"],
            description=t.get("description"),
            category=t["category"],
            icon=t.get("icon", "file"),
            scope=t.get("scope", "project"),
            required_inputs=t.get("required_inputs", []),
            optional_inputs=t.get("optional_inputs", []),
        )
        for t in types
    ]


@router.get("/types/{doc_type_id}", response_model=DocumentTypeResponse)
async def get_type(
    doc_type_id: str,
    space_type: str = Query(..., description="Space type: project, organization, team"),
    space_id: UUID = Query(..., description="Space UUID"),
    db: AsyncSession = Depends(get_db),
    builder: DocumentBuilder = Depends(get_document_builder),
):
    """Get document type with buildability check for a specific space."""
    try:
        config = await get_document_config(db, doc_type_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document type '{doc_type_id}' not found")
    
    can_build, missing = await builder.can_build(doc_type_id, space_type, space_id)
    
    return DocumentTypeResponse(
        doc_type_id=config["doc_type_id"],
        name=config["name"],
        description=config.get("description"),
        category=config["category"],
        icon=config.get("icon", "file"),
        scope=config.get("scope", "project"),
        required_inputs=config.get("required_inputs", []),
        optional_inputs=config.get("optional_inputs", []),
        can_build=can_build,
        missing_deps=missing
    )


# =============================================================================
# BUILD ROUTES
# =============================================================================

@router.post("/build/{doc_type_id}", response_model=BuildResultResponse, deprecated=True)
async def build_document(
    doc_type_id: str,
    request: BuildDocumentRequest,
    space_type: str = Query(..., description="Space type: project, organization, team"),
    space_id: UUID = Query(..., description="Space UUID"),
    builder: DocumentBuilder = Depends(get_document_builder),
):
    """
    Build a document synchronously.
    
    DEPRECATED: Use POST /api/commands/documents/{doc_type_id}/build instead.
    Phase 7 (WS-DOCUMENT-SYSTEM-CLEANUP): This route will be removed.
    """
    result = await builder.build(
        doc_type_id=doc_type_id,
        space_type=space_type,
        space_id=space_id,
        inputs={
            "user_query": request.user_query,
            "project_description": request.project_description,
        },
        options={
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return BuildResultResponse(
        success=result.success,
        doc_type_id=result.doc_type_id,
        document_id=result.document_id,
        title=result.title,
        error=result.error,
        tokens=result.tokens,
    )


@router.post("/build/{doc_type_id}/stream")
async def build_document_stream(
    doc_type_id: str,
    request: BuildDocumentRequest,
    space_type: str = Query(..., description="Space type: project, organization, team"),
    space_id: UUID = Query(..., description="Space UUID"),
    builder: DocumentBuilder = Depends(get_document_builder),
):
    """
    Build a document with streaming progress updates.
    
    Returns Server-Sent Events with progress updates.
    
    Week 2: LLM execution is logged to llm_run table for telemetry and replay.
    """
    return StreamingResponse(
        builder.build_stream(
            doc_type_id=doc_type_id,
            space_type=space_type,
            space_id=space_id,
            inputs={
                "user_query": request.user_query,
                "project_description": request.project_description,
            },
            options={
                "model": request.model,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# =============================================================================
# DOCUMENT CRUD ROUTES
# =============================================================================

@router.get("/space/{space_type}/{space_id}", response_model=list[DocumentResponse])
async def list_documents(
    space_type: str,
    space_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status"),
    doc_service: DocumentService = Depends(get_document_service),
):
    """List all documents in a space."""
    docs = await doc_service.list_by_space(
        space_type=space_type,
        space_id=space_id,
        status=status,
    )
    
    return [
        DocumentResponse(
            id=str(doc.id),
            space_type=doc.space_type,
            space_id=str(doc.space_id),
            doc_type_id=doc.doc_type_id,
            version=doc.version,
            title=doc.title,
            status=doc.status,
            is_stale=doc.is_stale,
            created_at=doc.created_at.isoformat(),
        )
        for doc in docs
    ]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    doc_service: DocumentService = Depends(get_document_service),
):
    """Get a document by ID with relations."""
    doc = await doc_service.get_by_id(document_id, include_relations=True)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get relations
    relations = await doc_service.get_relations(document_id)
    
    def relation_to_dict(rel, doc_attr):
        target = getattr(rel, doc_attr, None)
        return {
            "id": str(rel.id),
            "relation_type": rel.relation_type,
            "document_id": str(target.id) if target else None,
            "document_title": target.title if target else None,
            "document_type": target.doc_type_id if target else None,
            "pinned_version": rel.pinned_version,
        }
    
    return DocumentDetailResponse(
        id=str(doc.id),
        space_type=doc.space_type,
        space_id=str(doc.space_id),
        doc_type_id=doc.doc_type_id,
        version=doc.version,
        title=doc.title,
        status=doc.status,
        is_stale=doc.is_stale,
        created_at=doc.created_at.isoformat(),
        content=doc.content,
        summary=doc.summary,
        builder_metadata=doc.builder_metadata,
        requires=[relation_to_dict(r, "to_document") for r in relations["outgoing"] if r.relation_type == "requires"],
        derived_from=[relation_to_dict(r, "to_document") for r in relations["outgoing"] if r.relation_type == "derived_from"],
        required_by=[relation_to_dict(r, "from_document") for r in relations["incoming"] if r.relation_type == "requires"],
        derivatives=[relation_to_dict(r, "from_document") for r in relations["incoming"] if r.relation_type == "derived_from"],
    )


@router.get("/{document_id}/render")
async def render_document(
    document_id: UUID,
    doc_service: DocumentService = Depends(get_document_service),
    db: AsyncSession = Depends(get_db),
):
    """Render a document to HTML."""
    doc = await doc_service.get_by_id(document_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get handler for this document type
    try:
        config = await get_document_config(db, doc.doc_type_id)
        handler = get_handler(config["handler_id"])
        html = handler.render(doc.content)
        
        return {"html": html}
    except (DocumentNotFoundError, HandlerNotFoundError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/mark-stale", deprecated=True)
async def mark_stale(
    document_id: UUID,
    doc_service: DocumentService = Depends(get_document_service),
):
    """Mark a document and its derivatives as stale."""
    count = await doc_service.mark_downstream_stale(document_id)
    return {"marked_stale": count}


@router.post("/{document_id}/clear-stale")
async def clear_stale(
    document_id: UUID,
    doc_service: DocumentService = Depends(get_document_service),
):
    """Clear the stale flag on a document."""
    await doc_service.clear_stale(document_id)
    return {"status": "cleared"}


@router.get("/space/{space_type}/{space_id}/stale", response_model=list[DocumentResponse])
async def list_stale_documents(
    space_type: str,
    space_id: UUID,
    doc_service: DocumentService = Depends(get_document_service),
):
    """List all stale documents in a space."""
    docs = await doc_service.get_stale_documents(space_type, space_id)
    
    return [
        DocumentResponse(
            id=str(doc.id),
            space_type=doc.space_type,
            space_id=str(doc.space_id),
            doc_type_id=doc.doc_type_id,
            version=doc.version,
            title=doc.title,
            status=doc.status,
            is_stale=doc.is_stale,
            created_at=doc.created_at.isoformat(),
        )
        for doc in docs
    ]


@router.get("/{document_id}/check-updates")
async def check_standard_updates(
    document_id: UUID,
    doc_service: DocumentService = Depends(get_document_service),
):
    """Check if any org standards this document requires have newer versions."""
    updates = await doc_service.check_standard_updates(document_id)
    return {"updates_available": updates}
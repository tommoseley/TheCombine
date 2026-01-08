"""
Composer preview routes for ADR-034 Document Composition.

Provides preview endpoints for document composition:
- Preview compiled prompt for a document definition
- Preview RenderModel structure for sample data

Per ADR-034 and WS-ADR-034-POC:
- Both endpoints return data-only (no HTML anywhere)
- Authentication: admin required (future)
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService
from app.domain.services.prompt_assembler import (
    PromptAssembler,
    AssembledPrompt,
    DocDefNotFoundError as PromptDocDefNotFoundError,
    ComponentNotFoundError as PromptComponentNotFoundError,
)
from app.domain.services.render_model_builder import (
    RenderModelBuilder,
    RenderModel,
    RenderBlock,
    DocDefNotFoundError as RenderDocDefNotFoundError,
    ComponentNotFoundError as RenderComponentNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/composer", tags=["composer"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RenderPreviewRequest(BaseModel):
    """Request body for render preview endpoint."""
    document_data: Dict[str, Any]


class AssembledPromptResponse(BaseModel):
    """Response for prompt preview endpoint."""
    document_def_id: str
    header: Dict[str, Any]
    component_bullets: list[str]
    component_ids: list[str]
    schema_bundle: Dict[str, Any]
    bundle_sha256: str
    formatted_prompt: str  # Convenience: pre-formatted prompt text
    
    model_config = ConfigDict(from_attributes=True)


class RenderBlockResponse(BaseModel):
    """Response model for a single RenderBlock."""
    type: str
    key: str
    data: Dict[str, Any]
    context: Dict[str, Any] | None = None


class RenderModelResponse(BaseModel):
    """Response for render preview endpoint."""
    document_def_id: str
    blocks: list[RenderBlockResponse]
    metadata: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Preview Endpoints
# =============================================================================

@router.get(
    "/preview/prompt/{document_def_id:path}",
    response_model=AssembledPromptResponse,
    summary="Preview compiled prompt for a document definition",
)
async def preview_prompt(
    document_def_id: str,
    db: AsyncSession = Depends(get_db),
) -> AssembledPromptResponse:
    """
    Preview the compiled prompt for a document definition.
    
    Assembles the prompt from the document definition and its component specs,
    including:
    - Header (role, constraints)
    - Component bullets (deduplicated, ordered)
    - Schema bundle
    - SHA256 hash
    
    Returns data-only JSON (no HTML).
    
    Args:
        document_def_id: Document definition ID (e.g., docdef:EpicBacklog:1.0.0)
        
    Returns:
        AssembledPromptResponse with all prompt assembly results
    """
    # Build services
    docdef_service = DocumentDefinitionService(db)
    component_service = ComponentRegistryService(db)
    schema_service = SchemaRegistryService(db)
    
    assembler = PromptAssembler(
        docdef_service=docdef_service,
        component_service=component_service,
        schema_service=schema_service,
    )
    
    try:
        assembled = await assembler.assemble(document_def_id)
        formatted = assembler.format_prompt_text(assembled)
        
        return AssembledPromptResponse(
            document_def_id=assembled.document_def_id,
            header=assembled.header,
            component_bullets=assembled.component_bullets,
            component_ids=assembled.component_ids,
            schema_bundle=assembled.schema_bundle,
            bundle_sha256=assembled.bundle_sha256,
            formatted_prompt=formatted,
        )
        
    except PromptDocDefNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PromptComponentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/preview/render/{document_def_id:path}",
    response_model=RenderModelResponse,
    summary="Preview RenderModel for sample data",
)
async def preview_render(
    document_def_id: str,
    request: RenderPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> RenderModelResponse:
    """
    Preview the RenderModel for a document definition with sample data.
    
    Builds RenderBlocks from the document definition sections,
    resolving data from the provided sample document.
    
    Returns data-only JSON (no HTML).
    
    Args:
        document_def_id: Document definition ID (e.g., docdef:EpicBacklog:1.0.0)
        request: Request body with document_data
        
    Returns:
        RenderModelResponse with all blocks and metadata
    """
    # Build services
    docdef_service = DocumentDefinitionService(db)
    component_service = ComponentRegistryService(db)
    
    builder = RenderModelBuilder(
        docdef_service=docdef_service,
        component_service=component_service,
    )
    
    try:
        render_model = await builder.build(
            document_def_id=document_def_id,
            document_data=request.document_data,
        )
        
        # Convert to response model
        blocks = [
            RenderBlockResponse(
                type=block.type,
                key=block.key,
                data=block.data,
                context=block.context,
            )
            for block in render_model.blocks
        ]
        
        return RenderModelResponse(
            document_def_id=render_model.document_def_id,
            blocks=blocks,
            metadata=render_model.metadata,
        )
        
    except RenderDocDefNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RenderComponentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


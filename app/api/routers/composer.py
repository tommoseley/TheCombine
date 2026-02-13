"""
Composer Preview API routes for ADR-034.

Provides preview endpoints for document composition:
- Preview compiled prompt for a document definition
- Preview RenderModel for sample data

Both endpoints return data-only (no HTML).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

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
# Response Models (Pydantic)
# =============================================================================

class PromptPreviewResponse(BaseModel):
    """Response for prompt preview endpoint."""
    document_def_id: str
    header: Dict[str, Any]
    component_bullets: List[str]
    component_ids: List[str]
    schema_bundle: Dict[str, Any]
    bundle_sha256: str
    formatted_prompt: str  # Bonus: include formatted text


class RenderBlockResponse(BaseModel):
    """Single render block in response."""
    type: str
    key: str
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class RenderPreviewResponse(BaseModel):
    """Response for render preview endpoint."""
    document_def_id: str
    blocks: List[RenderBlockResponse]
    metadata: Dict[str, Any]


class RenderPreviewRequest(BaseModel):
    """Request body for render preview endpoint."""
    document_data: Dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/preview/prompt/{document_def_id}", response_model=PromptPreviewResponse)
async def preview_prompt(
    document_def_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Preview compiled prompt for a document definition.
    
    Returns AssembledPrompt as JSON with:
    - document_def_id
    - header (role, constraints)
    - component_bullets (concatenated from all components)
    - component_ids (for audit)
    - schema_bundle (resolved schemas)
    - bundle_sha256
    - formatted_prompt (ready-to-use text)
    
    **Admin only** (authentication to be added).
    """
    logger.info(f"[ADR-034] Prompt preview requested for: {document_def_id}")
    
    # Create services
    docdef_service = DocumentDefinitionService(db)
    component_service = ComponentRegistryService(db)
    schema_service = SchemaRegistryService(db)
    
    # Create assembler
    assembler = PromptAssembler(
        docdef_service=docdef_service,
        component_service=component_service,
        schema_service=schema_service,
    )
    
    try:
        # Assemble prompt
        assembled = await assembler.assemble(document_def_id)
        
        # Format prompt text
        formatted = assembler.format_prompt_text(assembled)
        
        logger.info(
            f"[ADR-034] Prompt preview complete: {len(assembled.component_bullets)} bullets, "
            f"{len(assembled.component_ids)} components"
        )
        
        return PromptPreviewResponse(
            document_def_id=assembled.document_def_id,
            header=assembled.header,
            component_bullets=assembled.component_bullets,
            component_ids=assembled.component_ids,
            schema_bundle=assembled.schema_bundle,
            bundle_sha256=assembled.bundle_sha256,
            formatted_prompt=formatted,
        )
        
    except PromptDocDefNotFoundError as e:
        logger.warning(f"[ADR-034] Document definition not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PromptComponentNotFoundError as e:
        logger.warning(f"[ADR-034] Component not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[ADR-034] Prompt preview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prompt assembly failed: {str(e)}")


@router.post("/preview/render/{document_def_id}", response_model=RenderPreviewResponse)
async def preview_render(
    document_def_id: str,
    request: RenderPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Preview RenderModel for a document definition with sample data.
    
    Request body:
    - document_data: Sample document data to render
    
    Returns RenderModel as JSON with:
    - document_def_id
    - blocks (array of RenderBlock with type, key, data, context)
    - metadata
    
    **No HTML is returned** - data only per ADR-033.
    
    **Admin only** (authentication to be added).
    """
    logger.info(f"[ADR-034] Render preview requested for: {document_def_id}")
    
    # Create services
    docdef_service = DocumentDefinitionService(db)
    component_service = ComponentRegistryService(db)
    
    # Create builder
    builder = RenderModelBuilder(
        docdef_service=docdef_service,
        component_service=component_service,
    )
    
    try:
        # Build render model
        render_model = await builder.build(
            document_def_id=document_def_id,
            document_data=request.document_data,
        )
        
        # Convert to response format
        blocks = [
            RenderBlockResponse(
                type=block.type,
                key=block.key,
                data=block.data,
                context=block.context,
            )
            for block in render_model.blocks
        ]
        
        logger.info(
            f"[ADR-034] Render preview complete: {len(blocks)} blocks"
        )
        
        return RenderPreviewResponse(
            document_def_id=render_model.document_def_id,
            blocks=blocks,
            metadata=render_model.metadata,
        )
        
    except RenderDocDefNotFoundError as e:
        logger.warning(f"[ADR-034] Document definition not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RenderComponentNotFoundError as e:
        logger.warning(f"[ADR-034] Component not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[ADR-034] Render preview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Render model build failed: {str(e)}")

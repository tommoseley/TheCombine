"""
Document Viewer routes for The Combine UI.

Per DOCUMENT_VIEWER_CONTRACT v1.0:
- Generic viewer that renders any document type
- Uses RenderModelV1 structure with nested sections
- Fragment-based rendering via component bindings
- Graceful degradation for unknown/missing components

Routes:
- GET /view/{document_type}?params - Render stored document
- POST /view/{document_type}/preview - Render preview from request body
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService
from app.api.services.fragment_registry_service import FragmentRegistryService
from app.domain.services.render_model_builder import (
    RenderModelBuilder,
    RenderModel,
    RenderSection,
    RenderBlock,
    DocDefNotFoundError,
    ComponentNotFoundError,
)
from ..shared import templates


logger = logging.getLogger(__name__)

router = APIRouter(tags=["viewer"])


# =============================================================================
# Request Models
# =============================================================================

class ViewerPreviewRequest(BaseModel):
    """Request body for preview endpoint."""
    document_data: Dict[str, Any]
    title: Optional[str] = None
    subtitle: Optional[str] = None


# =============================================================================
# Fragment Rendering Support
# =============================================================================

class FragmentRenderer:
    """
    Renders blocks using fragment bindings.
    
    Per DOCUMENT_VIEWER_CONTRACT v1.0:
    - Resolves component by block.type (schema_id)
    - Gets fragment_id from component.view_bindings.web
    - Renders fragment with block context
    - Returns placeholder on any failure
    """
    
    def __init__(
        self,
        component_service: ComponentRegistryService,
        fragment_service: FragmentRegistryService,
    ):
        self.component_service = component_service
        self.fragment_service = fragment_service
        self._fragment_cache: Dict[str, str] = {}
        self._component_cache: Dict[str, Any] = {}
    
    async def preload(self, render_model: RenderModel) -> None:
        """Preload all fragments needed for this render model."""
        schema_ids = set()
        for section in render_model.sections:
            for block in section.blocks:
                schema_ids.add(block.type)
        
        for schema_id in schema_ids:
            await self._resolve_fragment(schema_id)
    
    async def _resolve_fragment(self, schema_id: str) -> Optional[str]:
        """Resolve fragment markup for a schema_id."""
        if schema_id in self._fragment_cache:
            return self._fragment_cache[schema_id]
        
        try:
            # Get component by schema_id
            # schema_id format: "schema:XxxV1"
            # component lookup expects schema_id directly
            components = await self.component_service.list_all()
            component = None
            for c in components:
                if c.schema_id == schema_id:
                    component = c
                    break
            
            if not component:
                logger.warning(f"No component found for schema_id: {schema_id}")
                self._fragment_cache[schema_id] = None
                return None
            
            self._component_cache[schema_id] = component
            
            # Get fragment_id from web bindings
            view_bindings = component.view_bindings or {}
            web_binding = view_bindings.get("web", {})
            fragment_id = web_binding.get("fragment_id")
            
            if not fragment_id:
                logger.warning(f"No web fragment binding for component: {component.component_id}")
                self._fragment_cache[schema_id] = None
                return None
            
            # Get fragment markup
            fragment = await self.fragment_service.get_fragment(fragment_id)
            if not fragment:
                logger.warning(f"Fragment not found: {fragment_id}")
                self._fragment_cache[schema_id] = None
                return None
            
            self._fragment_cache[schema_id] = fragment.fragment_markup
            return fragment.fragment_markup
            
        except Exception as e:
            logger.error(f"Error resolving fragment for {schema_id}: {e}")
            self._fragment_cache[schema_id] = None
            return None
    
    def render_block(self, block: RenderBlock) -> str:
        """
        Render a single block to HTML.
        
        Returns placeholder HTML on any failure.
        """
        schema_id = block.type
        markup = self._fragment_cache.get(schema_id)
        
        if markup is None:
            # Unknown block placeholder
            return self._render_placeholder(
                "Unsupported block",
                f"type: {block.type}",
                f"key: {block.key}",
            )
        
        try:
            # Compile and render fragment using shared templates env
            template = templates.env.from_string(markup)
            return template.render(block=block, item=block.data)
        except Exception as e:
            logger.error(f"Fragment render error for {block.key}: {e}")
            component = self._component_cache.get(schema_id)
            fragment_id = "unknown"
            if component:
                web_binding = (component.view_bindings or {}).get("web", {})
                fragment_id = web_binding.get("fragment_id", "unknown")
            
            return self._render_placeholder(
                "Fragment render error",
                f"fragment: {fragment_id}",
                f"key: {block.key}",
            )
    
    def _render_placeholder(self, title: str, *details: str) -> str:
        """Render a graceful degradation placeholder."""
        detail_html = "".join(f'<div class="text-xs text-gray-500">{d}</div>' for d in details)
        return f'''
        <div class="border border-amber-300 bg-amber-50 rounded p-3 my-2">
            <div class="text-sm font-medium text-amber-800">{title}</div>
            {detail_html}
        </div>
        '''


# =============================================================================
# Viewer Routes
# =============================================================================

@router.get("/view/{document_type}", response_class=HTMLResponse)
async def view_document(
    request: Request,
    document_type: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Render a stored document.
    
    Per DOCUMENT_VIEWER_CONTRACT v1.0:
    - Resolves document_type to latest accepted docdef
    - Loads stored document by type + params
    - Builds RenderModel and renders via fragments
    
    Args:
        document_type: Short name (e.g., "EpicDetailView")
        Query params: Document-specific params (e.g., epic_id=EPIC-001)
    """
    # TODO: Implement stored document lookup
    # For now, return 501 Not Implemented
    # This will be completed when we have stored documents
    
    logger.warning(f"Stored document view not yet implemented: {document_type}")
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Stored document view not yet implemented. Use POST /view/{document_type}/preview instead.",
    )


@router.post("/view/{document_type}/preview", response_class=HTMLResponse)
async def preview_document(
    request: Request,
    document_type: str,
    body: ViewerPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Render a document preview.
    
    Per DOCUMENT_VIEWER_CONTRACT v1.0:
    - Builds RenderModel from provided data
    - Renders via fragment bindings
    - No persistence required
    
    Args:
        document_type: Short name (e.g., "StorySummaryView")
        body: Request body with document_data
    """
    # Build services
    docdef_service = DocumentDefinitionService(db)
    component_service = ComponentRegistryService(db)
    schema_service = SchemaRegistryService(db)
    fragment_service = FragmentRegistryService(db)
    
    # Build RenderModel
    builder = RenderModelBuilder(
        docdef_service=docdef_service,
        component_service=component_service,
        schema_service=schema_service,
    )
    
    try:
        render_model = await builder.build(
            document_def_id=document_type,  # Builder handles short name
            document_data=body.document_data,
            title=body.title,
            subtitle=body.subtitle,
        )
    except DocDefNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ComponentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    # Preload fragments
    fragment_renderer = FragmentRenderer(
        component_service=component_service,
        fragment_service=fragment_service,
    )
    await fragment_renderer.preload(render_model)
    
    # Check if HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"
    
    # Render template
    context = {
        "request": request,
        "render_model": render_model,
        "fragment_renderer": fragment_renderer,
    }
    
    if is_htmx:
        return templates.TemplateResponse(
            "public/partials/_document_viewer.html",
            context,
        )
    else:
        return templates.TemplateResponse(
            "public/pages/document_viewer_page.html",
            context,
        )



"""
RenderModelBuilder for ADR-034 Document Composition.

Builds RenderModels from document definitions and document data.
Channel-neutral - produces data structures, not channel-specific output.

Per D6: Lives in app/domain/services/ (not web/bff) because it produces
data structures. Channel-specific rendering happens downstream.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService


logger = logging.getLogger(__name__)


class RenderModelError(Exception):
    """Base exception for render model building errors."""
    pass


class DocDefNotFoundError(RenderModelError):
    """Raised when document definition is not found."""
    pass


class ComponentNotFoundError(RenderModelError):
    """Raised when a component is not found."""
    pass


class InvalidPointerError(RenderModelError):
    """Raised when a JSON pointer cannot be resolved."""
    pass


@dataclass
class RenderBlock:
    """
    A single renderable block in a RenderModel.
    
    Per ADR-034:
    - type: canonical schema id (e.g., "schema:OpenQuestionV1")
    - key: unique key within document
    - data: validated block data
    - context: optional parent-supplied metadata
    """
    type: str      # canonical schema id, e.g., "schema:OpenQuestionV1"
    key: str       # unique key within document
    data: Dict[str, Any]  # validated block data
    context: Optional[Dict[str, Any]] = None  # parent-supplied metadata


@dataclass
class RenderModel:
    """
    Complete render model for a document.
    
    Contains all RenderBlocks organized by document definition sections.
    """
    document_def_id: str
    blocks: List[RenderBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RenderModelBuilder:
    """
    Builds RenderModels from document definitions and document data.
    
    Per ADR-034 and WS-ADR-034-POC:
    - Loads document definition by exact ID
    - For each section (ordered):
      - Resolves component spec to get schema_id
      - Based on shape (single, list, nested_list):
        - Creates RenderBlock(s) with type = schema_id
      - For nested_list: source_pointer and context are evaluated
        relative to each parent object, not from document root
    - Returns data-only RenderModel (no HTML)
    """
    
    def __init__(
        self,
        docdef_service: DocumentDefinitionService,
        component_service: ComponentRegistryService,
    ):
        self.docdef_service = docdef_service
        self.component_service = component_service
    
    async def build(
        self,
        document_def_id: str,
        document_data: Dict[str, Any],
    ) -> RenderModel:
        """
        Build a RenderModel from document definition and data.
        
        Algorithm:
        1. Load document definition by exact id
        2. For each section (ordered by 'order' field):
           - Resolve component spec to get schema_id
           - Based on shape:
             - single: Resolve source_pointer from root, create one RenderBlock
             - list: Resolve source_pointer from root, iterate array, create RenderBlock per item
             - nested_list: Iterate repeat_over array; for each parent object,
               resolve source_pointer relative to that parent, create RenderBlock per item
           - Set RenderBlock.type = component's schema_id
           - Set RenderBlock.key = {section_id}:{index}
           - Attach context by resolving context pointers relative to parent object
        3. Return RenderModel with all blocks
        
        Args:
            document_def_id: Exact document definition ID
            document_data: Document data to render
            
        Returns:
            RenderModel with all blocks (data-only, no HTML)
            
        Raises:
            DocDefNotFoundError: If document definition not found
            ComponentNotFoundError: If any component not found
        """
        # 1. Load document definition
        docdef = await self.docdef_service.get(document_def_id)
        if not docdef:
            raise DocDefNotFoundError(f"Document definition not found: {document_def_id}")
        
        # Build render model
        render_model = RenderModel(
            document_def_id=document_def_id,
            metadata={
                "section_count": len(docdef.sections or []),
            },
        )
        
        # 2. Process sections in order
        sections = docdef.sections or []
        sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
        
        for section in sorted_sections:
            section_blocks = await self._process_section(
                section=section,
                document_data=document_data,
            )
            render_model.blocks.extend(section_blocks)
        
        logger.info(
            f"Built RenderModel for {document_def_id}: "
            f"blocks={len(render_model.blocks)}"
        )
        
        return render_model
    
    async def _process_section(
        self,
        section: Dict[str, Any],
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        """
        Process a single section and return RenderBlocks.
        
        Args:
            section: Section definition from docdef
            document_data: Full document data
            
        Returns:
            List of RenderBlock for this section
        """
        section_id = section.get("section_id", "unknown")
        component_id = section.get("component_id")
        shape = section.get("shape", "single")
        source_pointer = section.get("source_pointer", "")
        repeat_over = section.get("repeat_over")
        context_mapping = section.get("context", {})
        
        # Resolve component to get schema_id
        component = await self.component_service.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        
        schema_id = component.schema_id  # e.g., "schema:OpenQuestionV1"
        
        blocks = []
        
        if shape == "single":
            # Single item at source_pointer
            data = self._resolve_pointer(document_data, source_pointer)
            if data is not None:
                blocks.append(RenderBlock(
                    type=schema_id,
                    key=f"{section_id}:0",
                    data=data if isinstance(data, dict) else {"value": data},
                    context=None,
                ))
        
        elif shape == "list":
            # Array at source_pointer
            items = self._resolve_pointer(document_data, source_pointer)
            if items and isinstance(items, list):
                for idx, item in enumerate(items):
                    item_data = item if isinstance(item, dict) else {"value": item}
                    blocks.append(RenderBlock(
                        type=schema_id,
                        key=f"{section_id}:{idx}",
                        data=item_data,
                        context=None,
                    ))
        
        elif shape == "nested_list":
            # Iterate repeat_over, then resolve source_pointer relative to each parent
            if not repeat_over:
                logger.warning(f"nested_list shape requires repeat_over: {section_id}")
                return blocks
            
            parents = self._resolve_pointer(document_data, repeat_over)
            if not parents or not isinstance(parents, list):
                return blocks
            
            block_idx = 0
            for parent_idx, parent in enumerate(parents):
                if not isinstance(parent, dict):
                    continue
                
                # Resolve source_pointer RELATIVE to parent object
                items = self._resolve_pointer(parent, source_pointer)
                if not items or not isinstance(items, list):
                    continue
                
                # Build context from parent
                context = self._build_context(parent, context_mapping)
                
                for item_idx, item in enumerate(items):
                    item_data = item if isinstance(item, dict) else {"value": item}
                    blocks.append(RenderBlock(
                        type=schema_id,
                        key=f"{section_id}:{parent_idx}:{item_idx}",
                        data=item_data,
                        context=context,
                    ))
                    block_idx += 1
        
        return blocks
    
    def _resolve_pointer(
        self,
        data: Dict[str, Any],
        pointer: str,
    ) -> Any:
        """
        Resolve a JSON pointer against data.
        
        Args:
            data: Data object to resolve against
            pointer: JSON pointer (e.g., "/epics", "/open_questions")
            
        Returns:
            Resolved value or None if not found
        """
        if not pointer or pointer == "/":
            return data
        
        # Remove leading slash and split
        parts = pointer.lstrip("/").split("/")
        
        current = data
        for part in parts:
            if not part:
                continue
            
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx]
                except (ValueError, IndexError):
                    return None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _build_context(
        self,
        parent: Dict[str, Any],
        context_mapping: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """
        Build context dict by resolving pointers relative to parent.
        
        Per ADR-034-A.4: Context pointers are evaluated relative to
        each repeated parent object, not from document root.
        
        Args:
            parent: Parent object to resolve against
            context_mapping: Dict of {context_key: pointer}
            
        Returns:
            Context dict or None if no mapping
        """
        if not context_mapping:
            return None
        
        context = {}
        for key, pointer in context_mapping.items():
            value = self._resolve_pointer(parent, pointer)
            if value is not None:
                context[key] = value
        
        return context if context else None

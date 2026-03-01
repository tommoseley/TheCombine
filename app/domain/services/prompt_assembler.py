"""
PromptAssembler for ADR-034 Document Composition.

Mechanically assembles LLM prompts from document definitions and component specs.
Runs server-side in the orchestrator/LLM request construction path.

Per D2:
- Reads docdef + component specs from DB
- Outputs: resolved schema bundle, compiled prompt bullets, document-level header
- Logs: docdef_id, component_ids, bundle_sha256 (ADR-010 alignment)
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService
from app.domain.services.prompt_assembler_pure import (
    collect_ordered_component_ids,
    dedupe_bullets,
    compute_bundle_sha256,
    format_prompt_text as pure_format_prompt_text,
)


logger = logging.getLogger(__name__)


class PromptAssemblyError(Exception):
    """Base exception for prompt assembly errors."""
    pass


class DocDefNotFoundError(PromptAssemblyError):
    """Raised when document definition is not found."""
    pass


class ComponentNotFoundError(PromptAssemblyError):
    """Raised when a component is not found."""
    pass


class SchemaNotFoundError(PromptAssemblyError):
    """Raised when a schema is not found."""
    pass


@dataclass
class AssembledPrompt:
    """
    Result of prompt assembly.
    
    Contains all information needed to construct an LLM prompt
    for generating a document of a specific type.
    """
    document_def_id: str
    header: Dict[str, Any]  # role, constraints from docdef
    component_bullets: List[str]  # concatenated from all components
    component_ids: List[str]  # for logging/audit
    schema_bundle: Dict[str, Any]  # resolved schema bundle (always included)
    bundle_sha256: str


class PromptAssembler:
    """
    Assembles LLM prompts from document definitions and component specs.
    
    Per ADR-034 and WS-ADR-034-POC:
    - Loads document definition by exact ID
    - Collects unique component_ids from sections (preserves section order)
    - Resolves each component spec
    - Concatenates generation_guidance.bullets (preserves order, dedupes exact duplicates)
    - Resolves schema bundle from component schemas (always included)
    - Logs assembly metadata per ADR-010
    """
    
    def __init__(
        self,
        docdef_service: DocumentDefinitionService,
        component_service: ComponentRegistryService,
        schema_service: Optional[SchemaRegistryService] = None,
    ):
        self.docdef_service = docdef_service
        self.component_service = component_service
        self.schema_service = schema_service
    
    async def assemble(self, document_def_id: str) -> AssembledPrompt:
        """
        Assemble a prompt from a document definition.
        
        Algorithm:
        1. Load document definition by exact id
        2. Collect unique component_ids from sections (preserve section order)
        3. Resolve each component spec
        4. Concatenate generation_guidance.bullets:
           - Preserve section order
           - Preserve bullet order within each component
           - Dedupe exact duplicates only, keeping first occurrence
        5. Resolve schema bundle from component schemas (always included)
        6. Compute bundle_sha256
        7. Return AssembledPrompt
        
        Args:
            document_def_id: Exact document definition ID
            
        Returns:
            AssembledPrompt with all assembly results
            
        Raises:
            DocDefNotFoundError: If document definition not found
            ComponentNotFoundError: If any component not found
        """
        # 1. Load document definition
        docdef = await self.docdef_service.get(document_def_id)
        if not docdef:
            raise DocDefNotFoundError(f"Document definition not found: {document_def_id}")
        
        # 2. Collect unique component_ids from sections (preserve section order)
        sections = docdef.sections or []
        ordered_component_ids = collect_ordered_component_ids(sections)
        
        # 3. Resolve each component spec
        components = []
        for comp_id in ordered_component_ids:
            component = await self.component_service.get(comp_id)
            if not component:
                raise ComponentNotFoundError(f"Component not found: {comp_id}")
            components.append(component)
        
        # 4. Concatenate bullets (preserve order, dedupe exact duplicates)
        components_guidance = [
            component.generation_guidance or {} for component in components
        ]
        all_bullets = dedupe_bullets(components_guidance)
        
        # 5. Resolve schema bundle from component schemas
        schema_bundle = await self._build_schema_bundle(components)
        
        # 6. Compute bundle SHA256
        bundle_sha256 = compute_bundle_sha256(schema_bundle)
        
        # 7. Build header from docdef
        header = docdef.prompt_header or {}
        
        # Log assembly per ADR-010
        logger.info(
            f"Assembled prompt for {document_def_id}: "
            f"components={ordered_component_ids}, "
            f"bullets={len(all_bullets)}, "
            f"bundle_sha256={bundle_sha256}"
        )
        
        return AssembledPrompt(
            document_def_id=document_def_id,
            header=header,
            component_bullets=all_bullets,
            component_ids=ordered_component_ids,
            schema_bundle=schema_bundle,
            bundle_sha256=bundle_sha256,
        )
    
    async def _build_schema_bundle(
        self,
        components: List[Any],
    ) -> Dict[str, Any]:
        """
        Build schema bundle from component schemas.
        
        Note: Schema bundle is built from component schemas, not from
        document_schema_id. This allows prompt assembly without a full
        document schema (nullable for MVP).
        
        Args:
            components: List of ComponentArtifact
            
        Returns:
            Schema bundle dict with all referenced schemas
        """
        bundle = {
            "schemas": {},
            "component_schemas": [],
        }
        
        for component in components:
            schema_id = component.schema_id
            bundle["component_schemas"].append(schema_id)
            
            # Try to resolve full schema if schema service available
            if self.schema_service:
                # Extract base schema_id without 'schema:' prefix if present
                lookup_id = schema_id
                if schema_id.startswith("schema:"):
                    lookup_id = schema_id[7:]  # Remove 'schema:' prefix
                
                schema = await self.schema_service.get_by_id(lookup_id)
                if schema and schema.schema_json:
                    bundle["schemas"][schema_id] = schema.schema_json
        
        return bundle
    
    def format_prompt_text(self, assembled: AssembledPrompt) -> str:
        """
        Format assembled prompt as LLM-ready text.

        Delegates to pure format_prompt_text function.
        """
        return pure_format_prompt_text(
            header=assembled.header,
            component_bullets=assembled.component_bullets,
            component_ids=assembled.component_ids,
            bundle_sha256=assembled.bundle_sha256,
        )


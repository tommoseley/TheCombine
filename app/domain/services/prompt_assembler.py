"""
PromptAssembler for ADR-034 Document Composition.

Mechanically assembles LLM prompts from document definitions and component specs.
Runs server-side in the orchestrator/LLM request construction path.

Per D2:
- Reads docdef + component specs from DB
- Outputs: resolved schema bundle, compiled prompt bullets, document-level header
- Logs: docdef_id, component_ids, bundle_sha256 (ADR-010 alignment)
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService


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
        # Sort by order field
        sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
        
        seen_component_ids = set()
        ordered_component_ids = []
        for section in sorted_sections:
            comp_id = section.get("component_id")
            if comp_id and comp_id not in seen_component_ids:
                seen_component_ids.add(comp_id)
                ordered_component_ids.append(comp_id)
        
        # 3. Resolve each component spec
        components = []
        for comp_id in ordered_component_ids:
            component = await self.component_service.get(comp_id)
            if not component:
                raise ComponentNotFoundError(f"Component not found: {comp_id}")
            components.append(component)
        
        # 4. Concatenate bullets (preserve order, dedupe exact duplicates)
        all_bullets = []
        seen_bullets = set()
        for component in components:
            guidance = component.generation_guidance or {}
            bullets = guidance.get("bullets", [])
            for bullet in bullets:
                if bullet not in seen_bullets:
                    seen_bullets.add(bullet)
                    all_bullets.append(bullet)
        
        # 5. Resolve schema bundle from component schemas
        schema_bundle = await self._build_schema_bundle(components)
        
        # 6. Compute bundle SHA256
        bundle_json = json.dumps(schema_bundle, sort_keys=True, separators=(',', ':'))
        bundle_sha256 = f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"
        
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
        
        Creates a structured prompt with:
        - Role context from header
        - Constraints from header
        - Generation bullets from components
        - Schema information
        
        Args:
            assembled: AssembledPrompt from assemble()
            
        Returns:
            Formatted prompt string
        """
        lines = []
        
        # Role
        role = assembled.header.get("role", "")
        if role:
            lines.append(role)
            lines.append("")
        
        # Constraints
        constraints = assembled.header.get("constraints", [])
        if constraints:
            lines.append("## Constraints")
            for constraint in constraints:
                lines.append(f"- {constraint}")
            lines.append("")
        
        # Generation guidance bullets
        if assembled.component_bullets:
            lines.append("## Generation Guidelines")
            for bullet in assembled.component_bullets:
                lines.append(f"- {bullet}")
            lines.append("")
        
        # Schema reference
        lines.append(f"## Schema Bundle")
        lines.append(f"SHA256: {assembled.bundle_sha256}")
        lines.append(f"Components: {', '.join(assembled.component_ids)}")
        
        return "\n".join(lines)


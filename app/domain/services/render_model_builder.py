"""
RenderModelBuilder for ADR-034 Document Composition.

Builds RenderModels from document definitions and document data.
Channel-neutral - produces data structures, not channel-specific output.

Per D6: Lives in app/domain/services/ (not web/bff) because it produces
data structures. Channel-specific rendering happens downstream.
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


# =============================================================================
# FROZEN DERIVATION RULES
# =============================================================================
# These are mechanical, deterministic helpers for derived view fields.
# Changes require governance approval. See docs/governance/DERIVED_FIELDS.md
# =============================================================================

def derive_risk_level(risks: List[Dict[str, Any]]) -> str:
    """
    Derive aggregate risk level from a list of risks.
    
    FROZEN RULE (2026-01-08):
    - If any risk has likelihood="high" ? "high"
    - Else if any risk has likelihood="medium" ? "medium"  
    - Else ? "low"
    
    Args:
        risks: List of RiskV1-shaped dicts with optional 'likelihood' field
        
    Returns:
        One of: "high", "medium", "low"
    """
    if not risks:
        return "low"
    
    likelihoods = [r.get("likelihood", "low") for r in risks if isinstance(r, dict)]
    
    if "high" in likelihoods:
        return "high"
    elif "medium" in likelihoods:
        return "medium"
    else:
        return "low"


def derive_integration_surface(obj: Dict[str, Any]) -> str:
    """
    Derive integration surface indicator from architecture data.
    
    FROZEN RULE (2026-01-08):
    - If external_integrations count > 0 ? "external"
    - Else ? "none"
    
    Args:
        obj: Architecture data object with optional 'external_integrations' field
        
    Returns:
        One of: "external", "none"
    """
    integrations = obj.get("external_integrations", [])
    # Handle both flat list and container form
    if isinstance(integrations, dict):
        integrations = integrations.get("items", [])
    
    if integrations and len(integrations) > 0:
        return "external"
    return "none"


def derive_complexity_level(obj: Dict[str, Any]) -> str:
    """
    Derive complexity indicator from architecture data.
    
    FROZEN RULE (2026-01-08):
    total = |systems_touched| + |key_interfaces| + |dependencies| + |external_integrations|
    - 0-3 ? "low"
    - 4-7 ? "medium"
    - 8+ ? "high"
    
    Args:
        obj: Architecture data object
        
    Returns:
        One of: "low", "medium", "high"
    """
    def safe_len(field_name: str) -> int:
        val = obj.get(field_name, [])
        # Handle container form {"items": [...]}
        if isinstance(val, dict):
            val = val.get("items", [])
        if isinstance(val, list):
            return len(val)
        return 0
    
    total = (
        safe_len("systems_touched") +
        safe_len("key_interfaces") +
        safe_len("dependencies") +
        safe_len("external_integrations")
    )
    
    if total <= 3:
        return "low"
    elif total <= 7:
        return "medium"
    else:
        return "high"


# Registry of allowed derivation functions (frozen)
DERIVATION_FUNCTIONS = {
    "risk_level": derive_risk_level,
    "integration_surface": derive_integration_surface,
    "complexity_level": derive_complexity_level,
}


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
    - key: unique key within document (format: section_id:index)
    - data: validated block data
    - context: optional parent-supplied metadata
    """
    type: str      # canonical schema id, e.g., "schema:OpenQuestionV1"
    key: str       # unique key within document
    data: Dict[str, Any]  # validated block data
    context: Optional[Dict[str, Any]] = None  # parent-supplied metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "type": self.type,
            "key": self.key,
            "data": self.data,
        }
        if self.context:
            result["context"] = self.context
        return result


@dataclass
class RenderSection:
    """
    A section containing blocks in a RenderModel.

    Per DOCUMENT_VIEWER_CONTRACT v1.0:
    - section_id: stable identifier
    - title: display title (from docdef, not data)
    - order: numeric ordering
    - description: optional description
    - blocks: list of RenderBlock
    - viewer_tab: tab grouping ("overview", "details", or "both")
    - sidecar_max_items: optional limit for sidecar view
    """
    section_id: str
    title: str
    order: int
    blocks: List[RenderBlock] = field(default_factory=list)
    description: Optional[str] = None
    viewer_tab: str = "details"  # Default per WS-DOCUMENT-VIEWER-TABS
    sidecar_max_items: Optional[int] = None  # Max items to show in sidecar view

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "section_id": self.section_id,
            "title": self.title,
            "order": self.order,
            "blocks": [b.to_dict() for b in self.blocks],
            "viewer_tab": self.viewer_tab,
        }
        if self.description:
            result["description"] = self.description
        if self.sidecar_max_items is not None:
            result["sidecar_max_items"] = self.sidecar_max_items
        return result


@dataclass
class RenderModel:
    """
    Complete render model for a document.
    
    Per DOCUMENT_VIEWER_CONTRACT v1.0:
    - render_model_version: "1.0"
    - schema_id: "schema:RenderModelV1"
    - schema_bundle_sha256: hash of schema bundle
    - document_id: stable identifier
    - document_type: short name (e.g., "DocumentDetailView")
    - title: display title
    - sections: list of RenderSection (ordered)
    - metadata: section_count and other metadata
    """
    render_model_version: str
    schema_id: str
    document_id: str
    document_type: str
    title: str
    sections: List[RenderSection] = field(default_factory=list)
    schema_bundle_sha256: str = ""
    subtitle: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy field for backward compatibility during migration
    # TODO: Remove after all consumers updated
    @property
    def blocks(self) -> List[RenderBlock]:
        """Flat list of all blocks (legacy compatibility)."""
        result = []
        for section in self.sections:
            result.extend(section.blocks)
        return result
    
    @property
    def document_def_id(self) -> str:
        """Legacy accessor for document_type."""
        return f"docdef:{self.document_type}:1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "render_model_version": self.render_model_version,
            "schema_id": self.schema_id,
            "schema_bundle_sha256": self.schema_bundle_sha256,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "title": self.title,
            "sections": [s.to_dict() for s in self.sections if s.blocks],  # Omit empty sections
            "metadata": self.metadata,
        }
        if self.subtitle:
            result["subtitle"] = self.subtitle
        return result


class RenderModelBuilder:
    """
    Builds RenderModels from document definitions and document data.
    
    Per DOCUMENT_VIEWER_CONTRACT v1.0:
    - Loads document definition by exact ID or short name
    - For each section (ordered):
      - Resolves component spec to get schema_id
      - Creates RenderBlock(s) based on shape semantics
      - Groups blocks under RenderSection
    - Returns data-only RenderModel with nested sections structure
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
    
    async def build(
        self,
        document_def_id: str,
        document_data: Dict[str, Any],
        document_id: Optional[str] = None,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
    ) -> RenderModel:
        """
        Build a RenderModel from document definition and data.
        
        Per DOCUMENT_VIEWER_CONTRACT v1.0:
        - Emits nested sections[] structure
        - Populates all envelope fields
        - Empty sections are omitted in output
        
        Args:
            document_def_id: Exact document definition ID (e.g., docdef:DocumentDetailView:1.0.0)
                            or short name (e.g., DocumentDetailView)
            document_data: Document data to render
            document_id: Optional document ID (computed if not provided)
            title: Optional title override
            subtitle: Optional subtitle
            
        Returns:
            RenderModel with nested sections (data-only, no HTML)
            
        Raises:
            DocDefNotFoundError: If document definition not found
            ComponentNotFoundError: If any component not found
        """
        # Resolve short name to full docdef ID if needed
        if not document_def_id.startswith("docdef:"):
            document_def_id = f"docdef:{document_def_id}:1.0.0"
        
        # 1. Load document definition
        docdef = await self.docdef_service.get(document_def_id)
        if not docdef:
            raise DocDefNotFoundError(f"Document definition not found: {document_def_id}")
        
        # Extract document_type from docdef ID
        # Format: docdef:DocumentType:version
        parts = document_def_id.split(":")
        document_type = parts[1] if len(parts) >= 2 else document_def_id
        
        # Compute document_id if not provided
        if not document_id:
            document_id = self._compute_document_id(document_type, document_data)
        
        # Compute schema bundle SHA256
        schema_bundle_sha256 = await self._compute_schema_bundle_sha256(docdef)
        
        # Determine title
        display_title = title or document_data.get("title", document_type)
        
        # 2. Process sections in order
        sections_config = docdef.sections or []
        sorted_sections = sorted(sections_config, key=lambda s: s.get("order", 0))
        
        render_sections: List[RenderSection] = []
        
        for section_config in sorted_sections:
            section_blocks = await self._process_section(
                section=section_config,
                document_data=document_data,
            )
            
            # Per DOCUMENT_VIEWER_CONTRACT: omit empty sections
            if not section_blocks:
                continue
            
            # Create RenderSection
            render_section = RenderSection(
                section_id=section_config.get("section_id", "unknown"),
                title=section_config.get("title", ""),
                order=section_config.get("order", 0),
                description=section_config.get("description"),
                blocks=section_blocks,
                viewer_tab=section_config.get("viewer_tab", "details"),
                sidecar_max_items=section_config.get("sidecar_max_items"),
            )
            render_sections.append(render_section)
        
        # Build render model with envelope fields
        render_model = RenderModel(
            render_model_version="1.0",
            schema_id="schema:RenderModelV1",
            schema_bundle_sha256=schema_bundle_sha256,
            document_id=document_id,
            document_type=document_type,
            title=display_title,
            subtitle=subtitle,
            sections=render_sections,
            metadata={
                "section_count": len(sections_config),
            },
        )
        
        total_blocks = sum(len(s.blocks) for s in render_sections)
        logger.info(
            f"Built RenderModel for {document_type}: "
            f"sections={len(render_sections)}, blocks={total_blocks}"
        )
        
        return render_model
    
    def _compute_document_id(
        self,
        document_type: str,
        document_data: Dict[str, Any],
    ) -> str:
        """
        Compute deterministic document_id for preview/on-demand renders.
        
        Per DOCUMENT_VIEWER_CONTRACT v1.0:
        document_id = sha256(document_type + canonical(params))[:16]
        
        For stored documents, the database UUID should be passed explicitly.
        """
        # Extract key identifying fields from data
        params = {}
        for key in ["id", "story_id", "project_id"]:
            if key in document_data:
                params[key] = str(document_data[key])
        
        # Canonical serialization: sorted keys, k=v&k2=v2 format
        canonical = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        
        # Compute hash
        content = f"{document_type}:{canonical}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        return hash_value
    
    def _build_metadata(
        self,
        section_count: int,
        lifecycle_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build metadata dict for RenderModel.
        
        Includes lifecycle_state (ADR-036) if provided.
        """
        metadata = {"section_count": section_count}
        if lifecycle_state:
            metadata["lifecycle_state"] = lifecycle_state
        return metadata
    
    async def _compute_schema_bundle_sha256(
        self,
        docdef,
    ) -> str:
        """
        Compute SHA256 hash of schema bundle for this document.
        
        Collects all component schemas and hashes the bundle.
        """
        sections = docdef.sections or []
        
        # Collect unique component IDs
        component_ids = set()
        for section in sections:
            comp_id = section.get("component_id")
            if comp_id:
                component_ids.add(comp_id)
        
        # Build schema bundle
        bundle = {"schemas": {}}
        for comp_id in sorted(component_ids):
            component = await self.component_service.get(comp_id)
            if component and component.schema_id:
                # Try to get full schema if service available
                if self.schema_service:
                    schema_id = component.schema_id
                    if schema_id.startswith("schema:"):
                        lookup_id = schema_id[7:]  # Remove prefix
                    else:
                        lookup_id = schema_id
                    
                    schema = await self.schema_service.get_by_id(lookup_id)
                    if schema and schema.schema_json:
                        bundle["schemas"][component.schema_id] = schema.schema_json
                else:
                    bundle["schemas"][component.schema_id] = {}
        
        # Compute hash
        bundle_json = json.dumps(bundle, sort_keys=True, separators=(',', ':'))
        return f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"
    
    async def _process_section(
        self,
        section: Dict[str, Any],
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        section_id = section.get("section_id", "unknown")
        component_id = section.get("component_id")
        shape = section.get("shape", "single")
        derived_from = section.get("derived_from")
        context_mapping = section.get("context", {})
        
        if derived_from:
            return await self._process_derived_section(
                section_id=section_id,
                component_id=component_id,
                derived_from=derived_from,
                document_data=document_data,
                context_mapping=context_mapping,
            )
        
        component = await self.component_service.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        
        schema_id = component.schema_id
        
        shape_handlers = {
            "single": self._process_single_shape,
            "list": self._process_list_shape,
            "nested_list": self._process_nested_list_shape,
            "container": self._process_container_shape,
        }
        
        handler = shape_handlers.get(shape)
        if handler:
            return handler(section, schema_id, document_data)
        
        logger.warning(f"Unknown shape '{shape}' for section {section_id}")
        return []
    def _process_single_shape(
        self,
        section: Dict[str, Any],
        schema_id: str,
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        section_id = section.get("section_id", "unknown")
        source_pointer = section.get("source_pointer", "")
        context_mapping = section.get("context", {})
        
        data = self._resolve_pointer(document_data, source_pointer)
        if data is None:
            return []
        
        static_context = context_mapping if context_mapping else None
        block_data = data if isinstance(data, dict) else {"value": data}
        
        detail_ref_template = section.get("detail_ref_template")
        if detail_ref_template:
            block_data = dict(block_data) if isinstance(block_data, dict) else {"value": block_data}
            block_data["detail_ref"] = {
                "document_type": detail_ref_template.get("document_type", ""),
                "params": {
                    k: self._resolve_pointer(document_data, v) 
                    for k, v in detail_ref_template.get("params", {}).items()
                }
            }
        
        return [RenderBlock(
            type=schema_id,
            key=f"{section_id}:0",
            data=block_data,
            context=static_context,
        )]
    def _process_list_shape(
        self,
        section: Dict[str, Any],
        schema_id: str,
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        section_id = section.get("section_id", "unknown")
        source_pointer = section.get("source_pointer", "")
        
        items = self._resolve_pointer(document_data, source_pointer)
        if not items or not isinstance(items, list):
            return []
        
        blocks = []
        for idx, item in enumerate(items):
            item_data = item if isinstance(item, dict) else {"value": item}
            blocks.append(RenderBlock(
                type=schema_id,
                key=f"{section_id}:{idx}",
                data=item_data,
                context=None,
            ))
        return blocks

    def _process_nested_list_shape(
        self,
        section: Dict[str, Any],
        schema_id: str,
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        section_id = section.get("section_id", "unknown")
        source_pointer = section.get("source_pointer", "")
        repeat_over = section.get("repeat_over")
        context_mapping = section.get("context", {})
        
        if not repeat_over:
            logger.warning(f"nested_list shape requires repeat_over: {section_id}")
            return []
        
        parents = self._resolve_pointer(document_data, repeat_over)
        if not parents or not isinstance(parents, list):
            return []
        
        blocks = []
        for parent_idx, parent in enumerate(parents):
            if not isinstance(parent, dict):
                continue
            
            items = self._resolve_pointer(parent, source_pointer)
            if not items or not isinstance(items, list):
                continue
            
            context = self._build_context(parent, context_mapping)
            
            for item_idx, item in enumerate(items):
                item_data = item if isinstance(item, dict) else {"value": item}
                blocks.append(RenderBlock(
                    type=schema_id,
                    key=f"{section_id}:{parent_idx}:{item_idx}",
                    data=item_data,
                    context=context,
                ))
        
        return blocks
    def _process_container_shape(
        self,
        section: Dict[str, Any],
        schema_id: str,
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        repeat_over = section.get("repeat_over")
        
        if repeat_over:
            return self._process_container_with_repeat(section, schema_id, document_data)
        else:
            return self._process_container_simple(section, schema_id, document_data)

    def _process_container_simple(
        self,
        section: Dict[str, Any],
        schema_id: str,
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        section_id = section.get("section_id", "unknown")
        source_pointer = section.get("source_pointer", "")
        context_mapping = section.get("context", {})
        
        items = self._resolve_pointer(document_data, source_pointer)
        if not items or not isinstance(items, list):
            return []
        
        processed_items = []
        for item in items:
            item_data = item if isinstance(item, dict) else {"value": item}
            processed_items.append(item_data)
        
        static_context = context_mapping if context_mapping else None
        
        return [RenderBlock(
            type=schema_id,
            key=f"{section_id}:container",
            data={"items": processed_items},
            context=static_context,
        )]
    def _process_container_with_repeat(
        self,
        section: Dict[str, Any],
        schema_id: str,
        document_data: Dict[str, Any],
    ) -> List[RenderBlock]:
        section_id = section.get("section_id", "unknown")
        source_pointer = section.get("source_pointer", "")
        repeat_over = section.get("repeat_over")
        context_mapping = section.get("context", {})
        derived_fields = section.get("derived_fields", [])
        
        parents = self._resolve_pointer(document_data, repeat_over)
        if not parents or not isinstance(parents, list):
            return []
        
        blocks = []
        for parent_idx, parent in enumerate(parents):
            if not isinstance(parent, dict):
                continue
            
            if source_pointer in ("/", ""):
                block_data = self._build_parent_as_data(section, parent, derived_fields)
            else:
                parent_items = self._resolve_pointer(parent, source_pointer)
                if not parent_items or not isinstance(parent_items, list):
                    continue
                
                processed_items = []
                for item in parent_items:
                    item_data = item if isinstance(item, dict) else {"value": item}
                    processed_items.append(item_data)
                block_data = {"items": processed_items}
            
            context = self._build_context(parent, context_mapping)
            
            blocks.append(RenderBlock(
                type=schema_id,
                key=f"{section_id}:container:{parent_idx}",
                data=block_data,
                context=context,
            ))
        
        return blocks
    def _build_parent_as_data(
        self,
        section: Dict[str, Any],
        parent: Dict[str, Any],
        derived_fields: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        exclude_fields = section.get("exclude_fields", [])
        block_data = {k: v for k, v in parent.items() if k not in exclude_fields}
        
        for df in derived_fields:
            field_name = df.get("field")
            func_name = df.get("function")
            source = df.get("source", "")
            
            if func_name in DERIVATION_FUNCTIONS:
                if source in ("/", ""):
                    source_data = parent
                else:
                    source_data = self._resolve_pointer(parent, source)
                    if source_data is None:
                        source_data = []
                block_data[field_name] = DERIVATION_FUNCTIONS[func_name](source_data)
        
        detail_ref_template = section.get("detail_ref_template")
        if detail_ref_template:
            block_data["detail_ref"] = {
                "document_type": detail_ref_template.get("document_type", ""),
                "params": {
                    k: self._resolve_pointer(parent, v) 
                    for k, v in detail_ref_template.get("params", {}).items()
                }
            }
        
        return block_data

    async def _process_derived_section(
        self,
        section_id: str,
        component_id: str,
        derived_from: Dict[str, Any],
        document_data: Dict[str, Any],
        context_mapping: Dict[str, Any],
    ) -> List[RenderBlock]:
        """
        Process a derived section using frozen derivation rules.
        
        Args:
            section_id: Section identifier
            component_id: Component to use for rendering
            derived_from: {"function": "risk_level", "source": "/risks"}
            document_data: Full document data
            context_mapping: Static context from section config
            
        Returns:
            List containing single RenderBlock with derived value
        """
        func_name = derived_from.get("function")
        source_pointer = derived_from.get("source", "")
        
        # Validate function exists
        if func_name not in DERIVATION_FUNCTIONS:
            logger.warning(f"Unknown derivation function: {func_name}")
            return []
        
        # Check if we should omit when source is empty
        omit_when_empty = derived_from.get("omit_when_source_empty", False)
        
        # Resolve source data - "/" means pass entire document
        if source_pointer in ("/", ""):
            source_data = document_data
        else:
            source_data = self._resolve_pointer(document_data, source_pointer)
            if source_data is None:
                source_data = []
        
        # Omit block if source is empty and omit_when_source_empty is set
        if omit_when_empty:
            if source_data is None:
                return []
            if isinstance(source_data, list) and len(source_data) == 0:
                return []
            if isinstance(source_data, dict) and not source_data:
                return []
        
        # Apply derivation
        derive_fn = DERIVATION_FUNCTIONS[func_name]
        derived_value = derive_fn(source_data)
        
        # Resolve component to get schema_id
        component = await self.component_service.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        
        schema_id = component.schema_id
        static_context = context_mapping if context_mapping else None
        
        return [RenderBlock(
            type=schema_id,
            key=f"{section_id}:derived",
            data={"value": derived_value},
            context=static_context,
        )]
    
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






















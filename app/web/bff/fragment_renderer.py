"""
Fragment Renderer for ADR-032.

Renders canonical schema types using bound fragments.
"""

from typing import Dict, List, Optional, Any
import logging

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

from app.api.services.fragment_registry_service import FragmentRegistryService

logger = logging.getLogger(__name__)


class FragmentRenderError(Exception):
    """Raised when fragment rendering fails."""
    pass


class NoActiveBindingError(Exception):
    """Raised when no active binding exists for a schema type."""
    pass


class FragmentRenderer:
    """
    Renders data using canonical fragments bound to schema types.
    
    Per ADR-032:
    - Fragments render one instance of a canonical type
    - The renderer handles list iteration
    - Templates receive pre-composed HTML
    - Compiled templates are cached for performance
    """
    
    def __init__(
        self,
        registry: FragmentRegistryService,
        jinja_env: Optional[Environment] = None,
    ):
        """
        Initialize the fragment renderer.
        
        Args:
            registry: Fragment registry service for lookups
            jinja_env: Optional Jinja2 environment (creates default if not provided)
        """
        self.registry = registry
        self.jinja_env = jinja_env or Environment(loader=BaseLoader())
        
        # Cache for compiled templates: fragment_id:version -> Template
        self._template_cache: Dict[str, Any] = {}
    
    async def render(
        self,
        schema_type_id: str,
        data: dict,
        context: Optional[dict] = None,
    ) -> str:
        """
        Render a single item using the bound fragment.
        
        Args:
            schema_type_id: The canonical schema type
            data: The item data (passed as 'item' to template)
            context: Optional additional context variables
            
        Returns:
            Rendered HTML string
            
        Raises:
            NoActiveBindingError: If no active binding for type
            FragmentRenderError: If rendering fails
        """
        fragment = await self.registry.get_active_fragment_for_type(schema_type_id)
        
        if not fragment:
            raise NoActiveBindingError(
                f"No active fragment binding for schema type '{schema_type_id}'"
            )
        
        template = self._get_compiled_template(fragment)
        
        try:
            render_context = {"item": data}
            if context:
                render_context.update(context)
            
            return template.render(**render_context)
        
        except Exception as e:
            logger.error(f"Fragment render failed for {schema_type_id}: {e}")
            raise FragmentRenderError(
                f"Failed to render fragment for '{schema_type_id}': {e}"
            ) from e
    
    async def render_list(
        self,
        schema_type_id: str,
        items: List[dict],
        context: Optional[dict] = None,
        separator: str = "\n",
    ) -> str:
        """
        Render a list of items, each using the bound fragment.
        
        Per ADR-032 Section 2.5: Fragments render one instance; 
        collection rendering is handled by the viewer (this method).
        
        Args:
            schema_type_id: The canonical schema type
            items: List of item data dicts
            context: Optional additional context variables
            separator: HTML between rendered items
            
        Returns:
            Concatenated rendered HTML
            
        Raises:
            NoActiveBindingError: If no active binding for type
            FragmentRenderError: If rendering fails
        """
        if not items:
            return ""
        
        fragment = await self.registry.get_active_fragment_for_type(schema_type_id)
        
        if not fragment:
            raise NoActiveBindingError(
                f"No active fragment binding for schema type '{schema_type_id}'"
            )
        
        template = self._get_compiled_template(fragment)
        
        rendered_parts = []
        
        for idx, item in enumerate(items):
            try:
                render_context = {"item": item, "index": idx}
                if context:
                    render_context.update(context)
                
                rendered = template.render(**render_context)
                rendered_parts.append(rendered)
            
            except Exception as e:
                logger.error(f"Fragment render failed for {schema_type_id}[{idx}]: {e}")
                raise FragmentRenderError(
                    f"Failed to render fragment for '{schema_type_id}' at index {idx}: {e}"
                ) from e
        
        return separator.join(rendered_parts)
    
    def _get_compiled_template(self, fragment) -> Any:
        """
        Get compiled template from cache or compile and cache it.
        
        Args:
            fragment: FragmentArtifact with markup
            
        Returns:
            Compiled Jinja2 Template
        """
        cache_key = f"{fragment.fragment_id}:{fragment.version}"
        
        if cache_key not in self._template_cache:
            try:
                template = self.jinja_env.from_string(fragment.fragment_markup)
                self._template_cache[cache_key] = template
                logger.debug(f"Compiled and cached template: {cache_key}")
            except TemplateSyntaxError as e:
                raise FragmentRenderError(
                    f"Invalid template syntax in fragment '{fragment.fragment_id}': {e}"
                ) from e
        
        return self._template_cache[cache_key]
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()
        logger.debug("Fragment template cache cleared")
    
    @property
    def cache_size(self) -> int:
        """Return number of cached templates."""
        return len(self._template_cache)
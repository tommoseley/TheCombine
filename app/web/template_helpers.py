"""
Template helpers for Jinja2 rendering.

ADR-033: Fragment rendering is a web channel concern, not BFF.
"""

import logging
from typing import Dict, Optional
from markupsafe import Markup
from jinja2 import Environment

logger = logging.getLogger(__name__)


class PreloadedFragmentRenderer:
    """
    Fragment renderer that uses pre-loaded templates.
    
    Templates are fetched async in route handler, then this class
    renders them synchronously in Jinja templates.
    """
    
    def __init__(self, templates: Dict[str, str]):
        """
        Args:
            templates: Dict mapping type_id -> Jinja2 markup template string
        """
        self._templates = templates
        self._compiled: Dict[str, any] = {}
        self._env = Environment(autoescape=False)
    
    def _get_compiled(self, type_id: str):
        """Get or compile template for type."""
        if type_id not in self._compiled:
            markup = self._templates.get(type_id)
            if markup:
                self._compiled[type_id] = self._env.from_string(markup)
            else:
                return None
        return self._compiled.get(type_id)
    
    def render(self, type_id: str, data: dict) -> Markup:
        """
        Render a single fragment synchronously.
        
        Usage in templates:
            {{ fragment_renderer.render('OpenQuestionV1', data_dict) }}
        """
        try:
            template = self._get_compiled(type_id)
            if not template:
                logger.warning(f"No template loaded for {type_id}")
                return Markup("")
            
            # Fragment templates expect 'item' as the variable name
            html = template.render(item=data)
            return Markup(html)
        except Exception as e:
            logger.warning(f"Fragment rendering failed for {type_id}: {e}", exc_info=True)
            return Markup("")
    
    def render_list(self, type_id: str, items: list, separator: str = "") -> Markup:
        """Render a list of fragments."""
        results = []
        for item in items:
            rendered = self.render(type_id, item)
            if rendered:
                results.append(str(rendered))
        return Markup(separator.join(results))


async def create_preloaded_fragment_renderer(db_session, type_ids: list) -> PreloadedFragmentRenderer:
    """
    Create a PreloadedFragmentRenderer with templates pre-fetched from DB.
    
    Call this in route handlers (async context) before rendering template.
    
    Args:
        db_session: Async database session
        type_ids: List of schema type IDs to preload (e.g., ['OpenQuestionV1'])
        
    Returns:
        PreloadedFragmentRenderer instance
    """
    from app.api.services.fragment_registry_service import FragmentRegistryService
    
    registry = FragmentRegistryService(db_session)
    templates = {}
    
    for type_id in type_ids:
        try:
            # Get active binding for this type
            binding = await registry.get_active_binding(type_id)
            if binding:
                # Get the fragment
                fragment = await registry.get_fragment(
                    binding.fragment_id, 
                    binding.fragment_version
                )
                if fragment:
                    templates[type_id] = fragment.fragment_markup
                    logger.debug(f"Preloaded fragment for {type_id}")
        except Exception as e:
            logger.warning(f"Failed to preload fragment for {type_id}: {e}")
    
    return PreloadedFragmentRenderer(templates)
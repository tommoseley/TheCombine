"""
Story Backlog Document Handler

Handles the BA Story Set output - implementation-ready stories derived from 
PM Epic and Architecture.

Schema: BAStorySetSchemaV1
"""

from typing import Dict, Any, List, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class StoryBacklogHandler(BaseDocumentHandler):
    """
    Handler for story_backlog document type.
    
    Processes BA Mentor output containing implementation-ready stories
    with acceptance criteria and architecture component mappings.
    """
    
    @property
    def doc_type_id(self) -> str:
        return "story_backlog"
    
    @property
    def schema_path(self) -> str:
        return "schemas/ba_story_set_v1.json"
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/enrich the story backlog data.
        
        Adds computed fields for UI display:
        - story_count
        - mvp_count / later_phase_count
        - stories_by_phase grouping
        """
        stories = data.get("stories", [])
        
        # Count by phase
        mvp_count = sum(1 for s in stories if s.get("mvp_phase") == "mvp")
        later_count = sum(1 for s in stories if s.get("mvp_phase") == "later-phase")
        
        # Group stories by phase for easier template iteration
        stories_by_phase = {
            "mvp": [s for s in stories if s.get("mvp_phase") == "mvp"],
            "later-phase": [s for s in stories if s.get("mvp_phase") == "later-phase"],
        }
        
        # Collect all unique architecture components referenced
        all_components = set()
        for story in stories:
            for comp in story.get("related_arch_components", []):
                all_components.add(comp)
        
        # Add computed fields
        data["story_count"] = len(stories)
        data["mvp_count"] = mvp_count
        data["later_phase_count"] = later_count
        data["stories_by_phase"] = stories_by_phase
        data["referenced_components"] = sorted(list(all_components))
        
        return data
    
    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        Delegated to Jinja2 template: _story_backlog_content.html
        """
        # Template handles rendering - this is for programmatic render if needed
        story_count = data.get("story_count", len(data.get("stories", [])))
        return f"Story Backlog: {story_count} stories"
    
    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        story_count = data.get("story_count", len(data.get("stories", [])))
        mvp_count = data.get("mvp_count", 0)
        return f"{story_count} stories ({mvp_count} MVP)"


# Module-level instance
story_backlog_handler = StoryBacklogHandler()
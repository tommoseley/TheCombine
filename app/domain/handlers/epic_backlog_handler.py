"""
Epic Backlog Document Handler

Handles the PM Epic Set output - high-level epics with stories
that will be decomposed by the BA into implementation-ready stories.

Schema: PMEpicSetSchemaV1
"""

from typing import Dict, Any, List
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class EpicBacklogHandler(BaseDocumentHandler):
    """
    Handler for epic_backlog document type.
    
    Processes PM Mentor output containing epics with high-level stories,
    summary information, and recommendations for architecture.
    """
    
    @property
    def doc_type_id(self) -> str:
        return "epic_backlog"
    
    @property
    def schema_path(self) -> str:
        return "schemas/pm_epic_set_v1.json"
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/enrich the epic backlog data.
        
        Adds computed fields for UI display:
        - epic_count
        - mvp_count / later_phase_count
        - total_story_count
        """
        epics = data.get("epics", [])
        
        # Count by phase
        mvp_count = sum(1 for e in epics if e.get("mvp_phase") == "mvp")
        later_count = sum(1 for e in epics if e.get("mvp_phase") == "later-phase")
        
        # Count total stories across all epics
        total_stories = sum(len(e.get("stories", [])) for e in epics)
        
        # Add computed fields
        data["epic_count"] = len(epics)
        data["mvp_count"] = mvp_count
        data["later_phase_count"] = later_count
        data["total_story_count"] = total_stories
        
        return data
    
    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        Delegated to Jinja2 template: _epic_backlog_content.html
        """
        epic_count = data.get("epic_count", len(data.get("epics", [])))
        return f"Epic Backlog: {epic_count} epics"
    
    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        epic_count = data.get("epic_count", len(data.get("epics", [])))
        mvp_count = data.get("mvp_count", 0)
        return f"{epic_count} epics ({mvp_count} MVP)"


# Module-level instance for convenience
epic_backlog_handler = EpicBacklogHandler()
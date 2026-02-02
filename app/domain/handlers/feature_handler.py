"""
Feature Document Handler

Handles Feature documents - units of production intent.
Features define what will be produced and contain nested Stories.
"""

from typing import Dict, Any, List
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class FeatureHandler(BaseDocumentHandler):
    """
    Handler for feature document type.

    Features are created within Epics and contain nested Stories.
    They represent the handoff point between planning and execution.
    """

    @property
    def doc_type_id(self) -> str:
        return "feature"

    @property
    def schema_path(self) -> str:
        return "schemas/feature_v1.json"

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/enrich feature data.

        Adds computed fields:
        - story_count
        - total_points (sum of story points)
        """
        stories = data.get("stories", [])
        total_points = sum(s.get("story_points", 0) or 0 for s in stories)

        data["story_count"] = len(stories)
        data["total_points"] = total_points

        return data

    def render(self, data: Dict[str, Any]) -> str:
        """Render full view HTML."""
        name = data.get("name", "Untitled Feature")
        story_count = data.get("story_count", 0)
        return f"Feature: {name} ({story_count} stories)"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """Render compact summary."""
        name = data.get("name", "Untitled Feature")
        story_count = data.get("story_count", 0)
        total_points = data.get("total_points", 0)
        return f"{name} - {story_count} stories ({total_points} pts)"


# Module-level instance
feature_handler = FeatureHandler()

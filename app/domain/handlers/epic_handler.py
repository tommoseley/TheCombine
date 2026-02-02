"""
Epic Document Handler

Handles Epic documents - units of planning and commitment.
Epics have lifecycle gates and may require design phases.
"""

from typing import Dict, Any, List
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class EpicHandler(BaseDocumentHandler):
    """
    Handler for epic document type.

    Epics are created by Implementation Plan and serve as containers
    for Features. They have lifecycle states and design requirements.
    """

    @property
    def doc_type_id(self) -> str:
        return "epic"

    @property
    def schema_path(self) -> str:
        return "schemas/epic_v1.json"

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/enrich epic data.

        Adds computed fields:
        - feature_count
        - story_count (sum across features)
        """
        features = data.get("features", [])
        story_count = sum(len(f.get("stories", [])) for f in features)

        data["feature_count"] = len(features)
        data["story_count"] = story_count

        return data

    def render(self, data: Dict[str, Any]) -> str:
        """Render full view HTML."""
        name = data.get("name", "Untitled Epic")
        state = data.get("lifecycle_state", "draft")
        return f"Epic: {name} [{state}]"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """Render compact summary."""
        name = data.get("name", "Untitled Epic")
        state = data.get("lifecycle_state", "draft")
        feature_count = data.get("feature_count", 0)
        return f"{name} [{state}] - {feature_count} features"


# Module-level instance
epic_handler = EpicHandler()

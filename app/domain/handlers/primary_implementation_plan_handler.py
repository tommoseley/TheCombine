"""
Implementation Plan (Primary) Document Handler

Handles the preliminary implementation plan produced before technical architecture.
Contains Work Package candidates that inform architectural decisions.

WP candidates are not yet commitments - they become Work Packages
after architecture review via IPF reconciliation.
"""

from typing import Dict, Any
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class ImplementationPlanPrimaryHandler(BaseDocumentHandler):
    """
    Handler for primary_implementation_plan document type.

    Processes PM output containing Work Package candidates with preliminary
    scope, summary information, and recommendations for architecture.
    """

    @property
    def doc_type_id(self) -> str:
        return "primary_implementation_plan"

    @property
    def schema_path(self) -> str:
        return "schemas/primary_implementation_plan_v1.json"

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/enrich the implementation plan data.

        Adds computed fields for UI display:
        - candidate_count
        """
        candidates = data.get("work_package_candidates", [])

        # Add computed fields
        data["candidate_count"] = len(candidates)

        return data

    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        """
        candidate_count = data.get("candidate_count", len(data.get("work_package_candidates", [])))
        return f"Implementation Plan (Primary): {candidate_count} WP candidates"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        candidate_count = data.get("candidate_count", len(data.get("work_package_candidates", [])))
        return f"{candidate_count} WP candidates"


# Module-level instance for convenience
implementation_plan_primary_handler = ImplementationPlanPrimaryHandler()

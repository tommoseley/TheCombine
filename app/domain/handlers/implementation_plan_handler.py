"""
Implementation Plan Document Handler

Handles the unified implementation plan (merged from former IPP + IPF).
Contains Work Package candidates with risk analysis and architecture recommendations.
WP creation is now a separate manual step triggered from the Work Binder UI.
"""

from typing import Dict, Any
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class ImplementationPlanHandler(BaseDocumentHandler):
    """
    Handler for implementation_plan document type.

    Processes PM output containing Work Package candidates with risk analysis
    and architecture recommendations. Merged from former IPP + IPF handlers.
    WP creation is now a separate manual step (execution_mode: manual).
    """

    @property
    def doc_type_id(self) -> str:
        return "implementation_plan"

    @property
    def schema_path(self) -> str:
        return "schemas/implementation_plan_v1.json"

    def _get_candidates(self, data: Dict[str, Any]) -> list:
        """Get WP candidates from data, supporting v3/v2/v1 field names."""
        return (
            data.get("work_package_candidates")
            or data.get("candidate_work_packages")
            or data.get("work_packages")
            or []
        )

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/validate the implementation plan data.

        Schema has additionalProperties: false at every level, so transform
        must NOT inject computed fields into the persisted document.
        Computed fields (wp_count, associated_risks) are provided via
        render methods instead.
        """
        return data

    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        """
        wp_count = len(self._get_candidates(data))
        return f"Implementation Plan: {wp_count} WP candidates"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        wp_count = len(self._get_candidates(data))
        return f"{wp_count} WP candidates"


# Module-level instance for convenience
implementation_plan_handler = ImplementationPlanHandler()

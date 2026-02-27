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
        Transform/enrich the implementation plan data.

        Adds computed fields for UI display:
        - wp_count (from work_package_candidates / candidate_work_packages / work_packages)
        - associated_risks on each WP candidate (reverse index from risk_summary / risks_overview)
        """
        candidates = self._get_candidates(data)
        data["wp_count"] = len(candidates)

        # Build reverse mapping: candidate_id -> ["RSK-001: description", ...]
        # Support both v3 risk_summary and v2 risks_overview
        candidate_risks: Dict[str, list] = {}
        for risk in data.get("risks_overview", []):
            risk_id = risk.get("risk_id", "")
            description = risk.get("description", "")
            label = f"{risk_id}: {description}" if description else risk_id
            for cid in risk.get("affected_candidates", []):
                candidate_risks.setdefault(cid, []).append(label)
        for risk in data.get("risk_summary", []):
            risk_text = risk.get("risk", "")
            for cid in risk.get("affected_candidates", []):
                candidate_risks.setdefault(cid, []).append(risk_text)

        # Inject associated_risks into each candidate
        for candidate in candidates:
            cid = candidate.get("candidate_id", candidate.get("wp_id", ""))
            candidate["associated_risks"] = candidate_risks.get(cid, [])

        return data

    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        """
        wp_count = data.get("wp_count", len(self._get_candidates(data)))
        return f"Implementation Plan: {wp_count} WP candidates"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        wp_count = data.get("wp_count", len(self._get_candidates(data)))
        return f"{wp_count} WP candidates"


# Module-level instance for convenience
implementation_plan_handler = ImplementationPlanHandler()

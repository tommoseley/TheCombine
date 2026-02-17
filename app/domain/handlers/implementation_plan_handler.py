"""
Implementation Plan Document Handler

Handles the final implementation plan produced after technical architecture.
When this document is created, it spawns individual Epic documents.
"""

from typing import Dict, Any, List
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class ImplementationPlanHandler(BaseDocumentHandler):
    """
    Handler for implementation_plan document type.

    Processes PM output containing committed epics with sequencing,
    dependencies, and design requirements. Creates Epic child documents.
    """

    @property
    def doc_type_id(self) -> str:
        return "implementation_plan"

    @property
    def schema_path(self) -> str:
        return "schemas/implementation_plan_v1.json"

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform/enrich the implementation plan data.

        Adds computed fields for UI display:
        - epic_count
        - mvp_count / later_count
        - design_required_count

        Derives mechanical aggregations:
        - risk_summary: projected from per-epic risks (overwrites any LLM-generated version)
        """
        epics = data.get("epics", [])

        # Count by phase
        mvp_count = sum(1 for e in epics if e.get("mvp_phase") == "mvp")
        later_count = sum(1 for e in epics if e.get("mvp_phase") == "later")

        # Count design requirements
        design_required = sum(1 for e in epics if e.get("design_required") == "required")
        design_recommended = sum(1 for e in epics if e.get("design_required") == "recommended")

        # Add computed fields
        data["epic_count"] = len(epics)
        data["mvp_count"] = mvp_count
        data["later_count"] = later_count
        data["design_required_count"] = design_required
        data["design_recommended_count"] = design_recommended

        # Derive risk_summary mechanically from per-epic risks.
        # Each per-epic risk becomes a risk_summary_item with that epic as
        # the sole affected_epic. Cross-cutting grouping (merging risks that
        # span multiple epics) is a human review concern, not a mechanical one.
        data["risk_summary"] = self._derive_risk_summary(epics)

        return data

    @staticmethod
    def _derive_risk_summary(epics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Project per-epic risks into plan-level risk_summary items."""
        summary = []
        for epic in epics:
            epic_id = epic.get("epic_id", "")
            for risk in epic.get("risks", []):
                summary.append({
                    "risk": risk.get("risk", ""),
                    "affected_epics": [epic_id],
                    "overall_impact": risk.get("impact", "medium"),
                    "mitigation_strategy": risk.get("mitigation", ""),
                })
        return summary

    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        """
        epic_count = data.get("epic_count", len(data.get("epics", [])))
        mvp_count = data.get("mvp_count", 0)
        return f"Implementation Plan: {epic_count} epics ({mvp_count} MVP)"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        epic_count = data.get("epic_count", len(data.get("epics", [])))
        mvp_count = data.get("mvp_count", 0)
        return f"{epic_count} epics ({mvp_count} MVP)"

    def get_child_documents(
        self,
        data: Dict[str, Any],
        parent_title: str
    ) -> List[Dict[str, Any]]:
        """
        Extract Epic documents from the implementation plan.

        Each epic in the plan becomes a separate Epic document
        that can be managed through its lifecycle.

        Lineage metadata is included for audit traceability.
        The caller (plan_executor) injects execution_id into lineage.
        """
        epics = data.get("epics", [])
        children = []

        for epic in epics:
            epic_id = epic.get("epic_id", "")
            epic_name = epic.get("name", "Untitled Epic")

            # Build the Epic document content
            epic_content = {
                "epic_id": epic_id,
                "name": epic_name,
                "intent": epic.get("intent", ""),
                "lifecycle_state": "draft",
                "design_status": epic.get("design_required", "not_needed"),
                "sequence": epic.get("sequence"),
                "mvp_phase": epic.get("mvp_phase", "mvp"),
                "in_scope": epic.get("in_scope", []),
                "out_of_scope": epic.get("out_of_scope", []),
                "dependencies": epic.get("dependencies", []),
                "risks": epic.get("risks", []),
                "open_questions": epic.get("open_questions", []),
                "architecture_notes": epic.get("architecture_notes", []),
                "features": [],
                # Lineage: traceability back to parent IPF
                "_lineage": {
                    "parent_document_type": "implementation_plan",
                    "parent_execution_id": None,  # Injected by plan_executor
                    "source_candidate_ids": epic.get("source_candidate_ids", []),
                    "transformation": epic.get("transformation", "kept"),
                    "transformation_notes": epic.get("transformation_notes", ""),
                },
            }

            children.append({
                "doc_type_id": "epic",
                "title": f"Epic: {epic_name}",
                "content": epic_content,
                "identifier": epic_id,
            })

        logger.info(f"Extracted {len(children)} epic documents from implementation_plan")
        return children


# Module-level instance for convenience
implementation_plan_handler = ImplementationPlanHandler()

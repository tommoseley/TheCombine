"""
Implementation Plan Document Handler

Handles the final implementation plan produced after technical architecture.
When this document is created, it spawns individual Work Package documents.
"""

from typing import Dict, Any, List
from app.domain.handlers.base_handler import BaseDocumentHandler
import logging

logger = logging.getLogger(__name__)


class ImplementationPlanHandler(BaseDocumentHandler):
    """
    Handler for implementation_plan document type.

    Processes PM output containing committed Work Packages reconciled from
    WP candidates, with governance pinning, dependencies, and traceability.
    Creates Work Package child documents.
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
        - wp_count
        """
        work_packages = data.get("work_packages", [])
        data["wp_count"] = len(work_packages)
        return data

    def render(self, data: Dict[str, Any]) -> str:
        """
        Render full view HTML.
        """
        wp_count = data.get("wp_count", len(data.get("work_packages", [])))
        return f"Implementation Plan: {wp_count} Work Packages"

    def render_summary(self, data: Dict[str, Any]) -> str:
        """
        Render compact summary for cards/lists.
        """
        wp_count = data.get("wp_count", len(data.get("work_packages", [])))
        return f"{wp_count} Work Packages"

    def get_child_documents(
        self,
        data: Dict[str, Any],
        parent_title: str
    ) -> List[Dict[str, Any]]:
        """
        Extract Work Package documents from the implementation plan.

        Each WP in the plan becomes a separate Work Package document
        that can be managed through its lifecycle.

        Lineage metadata is included for audit traceability.
        The caller (plan_executor) injects execution_id into lineage.
        """
        work_packages = data.get("work_packages", [])
        children = []

        for wp in work_packages:
            wp_id = wp.get("wp_id", "")
            wp_title = wp.get("title", "Untitled Work Package")

            # Build the WP document content
            wp_content = {
                "wp_id": wp_id,
                "title": wp_title,
                "rationale": wp.get("rationale", ""),
                "scope_in": wp.get("scope_in", []),
                "scope_out": wp.get("scope_out", []),
                "dependencies": wp.get("dependencies", []),
                "definition_of_done": wp.get("definition_of_done", []),
                "state": "PLANNED",
                "ws_child_refs": [],
                "governance_pins": wp.get("governance_pins", {}),
                # Lineage: traceability back to parent IPF
                "_lineage": {
                    "parent_document_type": "implementation_plan",
                    "parent_execution_id": None,  # Injected by plan_executor
                    "source_candidate_ids": wp.get("source_candidate_ids", []),
                    "transformation": wp.get("transformation", "kept"),
                    "transformation_notes": wp.get("transformation_notes", ""),
                },
            }

            children.append({
                "doc_type_id": "work_package",
                "title": f"WP: {wp_title}",
                "content": wp_content,
                "identifier": wp_id,
            })

        logger.info(f"Extracted {len(children)} work package documents from implementation_plan")
        return children


# Module-level instance for convenience
implementation_plan_handler = ImplementationPlanHandler()

"""
Work Package Document Handler

Handles Work Package documents — units of planned work that replace
the Epic/Feature ontology. Created by IPF reconciliation, not LLM-generated.
"""

from typing import Dict, Any, Tuple, List, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler
from app.domain.services.work_package_state import WP_STATES
import logging

logger = logging.getLogger(__name__)


class WorkPackageHandler(BaseDocumentHandler):
    """
    Handler for work_package document type.

    Work Packages are created by IPF reconciliation and serve as
    containers for Work Statements. They have a state machine
    and rollup fields for child WS tracking.
    """

    @property
    def doc_type_id(self) -> str:
        return "work_package"

    def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """Validate WP content. Checks state enum if present, then delegates to base."""
        errors = []
        state = data.get("state")
        if state is not None and state not in WP_STATES:
            errors.append(
                f"Invalid state '{state}'. Must be one of: {WP_STATES}"
            )

        # Delegate to base for schema validation
        base_valid, base_errors = super().validate(data, schema)
        errors.extend(base_errors)

        return len(errors) == 0, errors

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set default rollup fields and default state if missing."""
        if "state" not in data:
            data["state"] = "PLANNED"

        data.setdefault("ws_total", 0)
        data.setdefault("ws_done", 0)
        data.setdefault("mode_b_count", 0)

        return data

    def extract_title(
        self,
        data: Dict[str, Any],
        fallback: str = "Untitled Work Package",
    ) -> str:
        return data.get("title", fallback)

    def render(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        title = data.get("title", "Untitled Work Package")
        state = data.get("state", "PLANNED")
        return f"Work Package: {title} [{state}]"

    def render_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        title = data.get("title", "Untitled Work Package")
        state = data.get("state", "PLANNED")
        ws_total = data.get("ws_total", 0)
        ws_done = data.get("ws_done", 0)
        return f"{title} [{state}] - {ws_done}/{ws_total} WS"

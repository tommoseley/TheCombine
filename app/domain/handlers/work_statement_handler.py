"""
Work Statement Document Handler

Handles Work Statement documents — units of authorized execution
that belong to a parent Work Package. Not LLM-generated.
"""

from typing import Dict, Any, Tuple, List, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler
from app.domain.services.work_statement_state import WS_STATES
import logging

logger = logging.getLogger(__name__)


class WorkStatementHandler(BaseDocumentHandler):
    """
    Handler for work_statement document type.

    Work Statements are authorized units of work within a Work Package.
    They require a parent_wp_id and have their own lifecycle state machine.
    """

    @property
    def doc_type_id(self) -> str:
        return "work_statement"

    def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """Validate WS content. Checks parent_wp_id and state enum, then delegates to base."""
        errors = []

        # parent_wp_id must be present and non-None
        if "parent_wp_id" not in data:
            errors.append("Missing required field: 'parent_wp_id'")
        elif data["parent_wp_id"] is None:
            errors.append("Required field 'parent_wp_id' is null")

        # Validate state enum if present
        state = data.get("state")
        if state is not None and state not in WS_STATES:
            errors.append(
                f"Invalid state '{state}'. Must be one of: {WS_STATES}"
            )

        # Delegate to base for schema validation
        base_valid, base_errors = super().validate(data, schema)
        errors.extend(base_errors)

        return len(errors) == 0, errors

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set default state to DRAFT if missing."""
        if "state" not in data:
            data["state"] = "DRAFT"
        return data

    def extract_title(
        self,
        data: Dict[str, Any],
        fallback: str = "Untitled Work Statement",
    ) -> str:
        return data.get("title", fallback)

    def render(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        title = data.get("title", "Untitled Work Statement")
        state = data.get("state", "DRAFT")
        return f"Work Statement: {title} [{state}]"

    def render_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        title = data.get("title", "Untitled Work Statement")
        state = data.get("state", "DRAFT")
        parent = data.get("parent_wp_id", "?")
        return f"{title} [{state}] (WP: {parent})"

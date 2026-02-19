"""
Project Logbook Document Handler

Handles Project Logbook documents — append-only audit trail of
Work Statement acceptances. Not LLM-generated.
"""

from typing import Dict, Any, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler


class ProjectLogbookHandler(BaseDocumentHandler):
    """
    Handler for project_logbook document type.

    Project Logbooks are created lazily on first WS acceptance.
    They are append-only — entries cannot be modified or deleted.
    """

    @property
    def doc_type_id(self) -> str:
        return "project_logbook"

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set defaults for logbook header fields."""
        data.setdefault("entries", [])
        data.setdefault("mode_b_rate", 0.0)
        data.setdefault("verification_debt_open", 0)
        return data

    def extract_title(
        self,
        data: Dict[str, Any],
        fallback: str = "Project Logbook",
    ) -> str:
        return "Project Logbook"

    def render(
        self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> str:
        entries = data.get("entries", [])
        count = len(entries)
        last_ts = entries[-1]["timestamp"] if entries else "N/A"
        return f"Project Logbook: {count} entries (last: {last_ts})"

    def render_summary(
        self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> str:
        entries = data.get("entries", [])
        count = len(entries)
        last_ts = entries[-1]["timestamp"] if entries else "N/A"
        return f"Logbook: {count} entries (last: {last_ts})"

"""
Work Package Candidate Document Handler — WS-WB-002.

Handles work_package_candidate documents — frozen lineage artifacts
extracted from Implementation Plans. Immutable after creation.

Key invariant: candidates are NEVER updated. validate_update() rejects
any attempt to modify an existing candidate document.
"""

import re
from typing import Dict, Any, Tuple, List, Optional
import logging

from app.domain.handlers.base_handler import BaseDocumentHandler
from app.domain.handlers.exceptions import DocumentValidationError

logger = logging.getLogger(__name__)

# Pattern for wpc_id: WPC-NNN (1-4 digits)
WPC_ID_PATTERN = re.compile(r"^WPC-\d{1,4}$")


class WorkPackageCandidateHandler(BaseDocumentHandler):
    """
    Handler for work_package_candidate document type.

    Work Package Candidates are mechanically extracted from Implementation
    Plans during IPF reconciliation. They are frozen at creation time and
    serve as governance provenance — recording what the IP proposed vs
    what was promoted to governed Work Packages.

    Immutability invariant: once created, a WPC cannot be updated.
    """

    @property
    def doc_type_id(self) -> str:
        return "work_package_candidate"

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate WPC content.

        Checks wpc_id format pattern, then delegates to base for
        schema-level required/type validation.
        """
        errors = []

        # Validate wpc_id pattern if present and non-null
        wpc_id = data.get("wpc_id")
        if wpc_id is not None and isinstance(wpc_id, str):
            if not WPC_ID_PATTERN.match(wpc_id):
                errors.append(
                    f"Field 'wpc_id' must match pattern WPC-NNN, got '{wpc_id}'"
                )

        # Delegate to base for schema validation
        base_valid, base_errors = super().validate(data, schema)
        errors.extend(base_errors)

        return len(errors) == 0, errors

    def validate_update(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Reject any update attempt — WPCs are immutable after creation.

        This method is called when an update is attempted on an existing
        document. It always raises DocumentValidationError.

        Raises:
            DocumentValidationError: Always. WPCs are immutable.
        """
        raise DocumentValidationError(
            doc_type_id=self.doc_type_id,
            errors=[
                "Work Package Candidates are immutable after creation. "
                "Updates are not permitted."
            ],
            parsed_content=data,
        )

    # =========================================================================
    # TRANSFORMATION
    # =========================================================================

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return data unchanged — candidates are frozen at creation.

        No defaults to set, no enrichment to perform. The data
        was mechanically extracted and should be preserved as-is.
        """
        return data

    # =========================================================================
    # TITLE EXTRACTION
    # =========================================================================

    def extract_title(
        self,
        data: Dict[str, Any],
        fallback: str = "Untitled Work Package Candidate",
    ) -> str:
        return data.get("title", fallback)

    # =========================================================================
    # RENDERING
    # =========================================================================

    def render(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render WPC to HTML for full document view."""
        wpc_id = self._escape(data.get("wpc_id", ""))
        title = self._escape(data.get("title", "Untitled"))
        rationale = self._escape(data.get("rationale", ""))
        source_ip_id = self._escape(data.get("source_ip_id", ""))
        source_ip_version = self._escape(data.get("source_ip_version", ""))
        frozen_at = self._escape(data.get("frozen_at", ""))
        frozen_by = self._escape(data.get("frozen_by", ""))

        scope_items = data.get("scope_summary", [])
        scope_html = "\n".join(
            f"<li>{self._escape(item)}</li>" for item in scope_items
        )

        return f"""
<div class="wpc-document">
    <h2>{wpc_id}: {title}</h2>
    <div class="wpc-rationale">
        <h3>Rationale</h3>
        <p>{rationale}</p>
    </div>
    <div class="wpc-scope">
        <h3>Scope Summary</h3>
        <ul>{scope_html}</ul>
    </div>
    <div class="wpc-provenance">
        <h3>Provenance</h3>
        <dl>
            <dt>Source IP</dt><dd>{source_ip_id} (v{source_ip_version})</dd>
            <dt>Frozen At</dt><dd>{frozen_at}</dd>
            <dt>Frozen By</dt><dd>{frozen_by}</dd>
        </dl>
    </div>
</div>
"""

    def render_summary(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render WPC to HTML for summary/card view."""
        wpc_id = self._escape(data.get("wpc_id", ""))
        title = self._escape(data.get("title", "Untitled"))
        scope_count = len(data.get("scope_summary", []))

        return f"{wpc_id}: {title} ({scope_count} scope items)"

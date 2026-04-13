"""
Binder Assembly Service (ADR-071).

Builds a work binder document from project state: queries all stabilized
documents, creates version-pinned references, and groups them by pipeline
stage. The binder is a composition layer — it references documents, it
does not duplicate their content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document

logger = logging.getLogger(__name__)

# Pipeline-order grouping for document types
DOC_TYPE_GROUPS = {
    "concierge_intake": ("intake", "Intake"),
    "project_discovery": ("discovery", "Project Discovery"),
    "technical_architecture": ("architecture", "Architecture"),
    "implementation_plan": ("planning", "Implementation Planning"),
    "work_package": ("work_packages", "Work Packages"),
    "work_statement": ("work_statements", "Work Statements"),
    "work_package_candidate": ("candidates", "Work Package Candidates"),
}

GROUP_ORDER = [
    "intake",
    "discovery",
    "architecture",
    "planning",
    "candidates",
    "work_packages",
    "work_statements",
]


@dataclass
class BinderContent:
    """Assembled binder content ready for persistence."""

    project_id: str
    assembled_at: str
    document_count: int
    referenced_documents: list[dict[str, Any]]
    groups: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "assembled_at": self.assembled_at,
            "document_count": self.document_count,
            "referenced_documents": self.referenced_documents,
            "groups": self.groups,
        }


async def assemble_binder(
    db: AsyncSession,
    project_id: str,
) -> BinderContent:
    """Assemble a work binder from current project documents.

    Queries all latest documents for the project, creates version-pinned
    references, and groups them by pipeline stage.

    Args:
        db: Database session
        project_id: Project identifier (space_id)

    Returns:
        BinderContent ready for persistence
    """
    # Fetch all latest documents for the project
    stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    # Build version-pinned references
    referenced_documents = []
    seen_groups = set()

    # Sort documents by pipeline order, then display_id
    def sort_key(doc):
        group_info = DOC_TYPE_GROUPS.get(doc.doc_type_id)
        if group_info:
            try:
                order = GROUP_ORDER.index(group_info[0])
            except ValueError:
                order = 999
        else:
            order = 999
        return (order, doc.display_id or "")

    for doc in sorted(docs, key=sort_key):
        # Skip internal document types
        if doc.doc_type_id in ("synthesis_delta",):
            continue

        group_info = DOC_TYPE_GROUPS.get(doc.doc_type_id)
        group_id = group_info[0] if group_info else "other"
        seen_groups.add(group_id)

        # Determine parent display_id for WSs
        parent_display_id = None
        if doc.doc_type_id == "work_statement" and doc.parent_document_id:
            # Look up parent WP's display_id
            parent_stmt = select(Document.display_id).where(
                Document.id == doc.parent_document_id
            )
            parent_result = await db.execute(parent_stmt)
            parent_display_id = parent_result.scalar_one_or_none()

        referenced_documents.append({
            "document_id": str(doc.id),
            "version": doc.version,
            "display_id": doc.display_id,
            "title": doc.title or doc.display_id,
            "doc_type_id": doc.doc_type_id,
            "group": group_id,
            "parent_display_id": parent_display_id,
        })

    # Build ordered groups list
    groups = []
    for group_id in GROUP_ORDER:
        if group_id in seen_groups:
            label = next(
                (v[1] for v in DOC_TYPE_GROUPS.values() if v[0] == group_id),
                group_id.replace("_", " ").title(),
            )
            groups.append({"id": group_id, "label": label})

    # Add "other" group if needed
    if "other" in seen_groups:
        groups.append({"id": "other", "label": "Other Documents"})

    assembled_at = datetime.now(timezone.utc).isoformat()

    return BinderContent(
        project_id=project_id,
        assembled_at=assembled_at,
        document_count=len(referenced_documents),
        referenced_documents=referenced_documents,
        groups=groups,
    )

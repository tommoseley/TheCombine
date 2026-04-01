"""
Lineage Path Service (ADR-067, WP-LINEAGE-001 WS-2).

Computes lineage paths from a checkpoint through valid upstream and downstream
artifacts. A lineage path is the maximal set of documents connected by lineage
edges (version chains within the same doc_type_id + display_id).

Pure functions where possible — DB queries are isolated to async entry points.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class PathDocument:
    """A document in a lineage path."""

    id: UUID
    doc_type_id: str
    display_id: str
    version: int
    title: str
    is_latest: bool
    is_stale: bool
    lifecycle_state: str
    created_at: Optional[datetime] = None
    parent_document_id: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "doc_type_id": self.doc_type_id,
            "display_id": self.display_id,
            "version": self.version,
            "title": self.title,
            "is_latest": self.is_latest,
            "is_stale": self.is_stale,
            "lifecycle_state": self.lifecycle_state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "parent_document_id": str(self.parent_document_id) if self.parent_document_id else None,
        }


@dataclass
class LineagePath:
    """A computed lineage path rooted at a checkpoint."""

    checkpoint_id: UUID
    checkpoint_doc_type: str
    checkpoint_version: int
    documents: List[PathDocument] = field(default_factory=list)
    is_active: bool = False  # True if checkpoint document is currently is_latest

    @property
    def doc_ids(self) -> List[UUID]:
        return [d.id for d in self.documents]

    @property
    def stage_summary(self) -> Dict[str, int]:
        """Count documents per stage in the path."""
        counts: Dict[str, int] = {}
        for d in self.documents:
            counts[d.doc_type_id] = counts.get(d.doc_type_id, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": str(self.checkpoint_id),
            "checkpoint_doc_type": self.checkpoint_doc_type,
            "checkpoint_version": self.checkpoint_version,
            "document_count": len(self.documents),
            "is_active": self.is_active,
            "stage_summary": self.stage_summary,
            "documents": [d.to_dict() for d in self.documents],
        }


# Pipeline stage ordering for path traversal
_STAGE_ORDER = {
    "concierge_intake": 0,
    "project_discovery": 1,
    "implementation_plan": 2,
    "technical_architecture": 3,
    "work_package": 4,
    "work_package_candidate": 4,
    "work_statement": 5,
}


def _stage_order(doc_type_id: str) -> int:
    return _STAGE_ORDER.get(doc_type_id, 99)


def compute_lineage_path(
    checkpoint: PathDocument,
    all_documents: List[PathDocument],
) -> LineagePath:
    """Compute the lineage path containing a checkpoint.

    Given a checkpoint document and all documents for a project,
    returns the path containing:
    - The checkpoint itself
    - Upstream documents (earlier stages) that share the same version lineage
    - Downstream documents (later stages) that were derived while the checkpoint was active

    Pure function — no DB access.

    Args:
        checkpoint: The anchor document for path computation.
        all_documents: All document versions for the project.

    Returns:
        LineagePath with ordered documents from earliest to latest stage.
    """
    path_docs: List[PathDocument] = [checkpoint]
    checkpoint_order = _stage_order(checkpoint.doc_type_id)

    # Index documents by various keys for lookup
    by_id: Dict[UUID, PathDocument] = {d.id: d for d in all_documents}

    # Find upstream: walk parent_document_id chain
    current = checkpoint
    while current.parent_document_id and current.parent_document_id in by_id:
        parent = by_id[current.parent_document_id]
        if _stage_order(parent.doc_type_id) < _stage_order(current.doc_type_id):
            path_docs.append(parent)
            current = parent
        else:
            break

    # For upstream stages not connected by parent_document_id,
    # find the version that was is_latest at the time the checkpoint was created
    upstream_stages = set()
    for d in path_docs:
        upstream_stages.add(d.doc_type_id)

    for doc in all_documents:
        if doc.id == checkpoint.id:
            continue
        if doc.doc_type_id in upstream_stages:
            continue
        if _stage_order(doc.doc_type_id) >= checkpoint_order:
            continue
        # For upstream stages not yet in path, find the version
        # that was current when the checkpoint was created
        if checkpoint.created_at and doc.created_at:
            if doc.created_at <= checkpoint.created_at:
                # Check if there's a newer version of this doc_type+display_id
                # that was also created before the checkpoint
                dominated = False
                for other in all_documents:
                    if (other.doc_type_id == doc.doc_type_id
                            and other.display_id == doc.display_id
                            and other.version > doc.version
                            and other.created_at
                            and other.created_at <= checkpoint.created_at):
                        dominated = True
                        break
                if not dominated and doc.doc_type_id not in {d.doc_type_id for d in path_docs if _stage_order(d.doc_type_id) == _stage_order(doc.doc_type_id)}:
                    path_docs.append(doc)

    # Find downstream: documents created after the checkpoint that reference
    # the same lineage branch (same display_id versions, created while checkpoint was latest)
    for doc in all_documents:
        if doc.id == checkpoint.id:
            continue
        if _stage_order(doc.doc_type_id) <= checkpoint_order:
            continue
        # Include downstream docs that were created after the checkpoint
        # and before any subsequent rewind of the checkpoint's stage
        if checkpoint.created_at and doc.created_at:
            if doc.created_at >= checkpoint.created_at:
                # Check this doc belongs to the same generation cycle
                # by verifying no rewind happened between checkpoint and this doc
                # For v1, use a simpler heuristic: include downstream docs
                # whose parent chain traces back to the checkpoint's generation
                if doc.parent_document_id and doc.parent_document_id in {d.id for d in path_docs}:
                    path_docs.append(doc)

    # Sort by stage order, then version
    path_docs.sort(key=lambda d: (_stage_order(d.doc_type_id), d.version))

    # Deduplicate
    seen: set[UUID] = set()
    unique_docs: List[PathDocument] = []
    for d in path_docs:
        if d.id not in seen:
            seen.add(d.id)
            unique_docs.append(d)

    # A path is active if the checkpoint itself is currently is_latest.
    # (Previous check of all(d.is_latest) was incorrect — a partial path
    # with some still-latest docs would be falsely marked active.)
    is_active = checkpoint.is_latest

    return LineagePath(
        checkpoint_id=checkpoint.id,
        checkpoint_doc_type=checkpoint.doc_type_id,
        checkpoint_version=checkpoint.version,
        documents=unique_docs,
        is_active=is_active,
    )


async def compute_lineage_path_from_db(
    db,
    project_id: UUID,
    checkpoint_id: UUID,
) -> Optional[LineagePath]:
    """Compute lineage path from database.

    Loads all documents for the project, finds the checkpoint,
    and delegates to the pure compute_lineage_path function.

    Args:
        db: AsyncSession
        project_id: Project UUID
        checkpoint_id: Document UUID to use as checkpoint

    Returns:
        LineagePath or None if checkpoint not found.
    """
    from sqlalchemy import select
    from app.api.models.document import Document

    # Load all document versions for the project
    result = await db.execute(
        select(Document).where(
            Document.space_type == "project",
            Document.space_id == project_id,
        )
    )
    all_orm = result.scalars().all()

    # Convert to PathDocument
    all_docs: List[PathDocument] = []
    checkpoint_doc: Optional[PathDocument] = None

    for orm in all_orm:
        pd = PathDocument(
            id=orm.id,
            doc_type_id=orm.doc_type_id,
            display_id=orm.display_id or "",
            version=orm.version,
            title=orm.title or "",
            is_latest=orm.is_latest,
            is_stale=orm.is_stale,
            lifecycle_state=orm.lifecycle_state or "complete",
            created_at=orm.created_at,
            parent_document_id=orm.parent_document_id,
        )
        all_docs.append(pd)
        if orm.id == checkpoint_id:
            checkpoint_doc = pd

    if checkpoint_doc is None:
        logger.warning(f"Checkpoint {checkpoint_id} not found in project {project_id}")
        return None

    return compute_lineage_path(checkpoint_doc, all_docs)

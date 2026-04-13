"""
Restore Preview Service (ADR-067, WP-LINEAGE-001 WS-6).

Evaluates the impact of restoring a lineage path before execution.
Advisory only in v1 — surfaces warnings but does not block.

Pure functions where possible.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.domain.services.lineage_path_service import LineagePath, PathDocument

logger = logging.getLogger(__name__)


@dataclass
class RestoreWarning:
    """An advisory warning about a restore operation."""

    category: str  # missing_upstream | stale_document | broken_lineage | version_gap
    message: str
    document_id: Optional[str] = None
    doc_type_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "message": self.message,
            "document_id": self.document_id,
            "doc_type_id": self.doc_type_id,
        }


@dataclass
class RestorePreview:
    """Preview of a restore operation's impact."""

    checkpoint_id: str
    path_document_count: int
    documents_to_activate: List[Dict[str, Any]]
    documents_to_demote: List[Dict[str, Any]]
    warnings: List[RestoreWarning] = field(default_factory=list)
    is_safe: bool = True  # True if no critical warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "path_document_count": self.path_document_count,
            "documents_to_activate": self.documents_to_activate,
            "documents_to_demote": self.documents_to_demote,
            "warning_count": len(self.warnings),
            "warnings": [w.to_dict() for w in self.warnings],
            "is_safe": self.is_safe,
        }


def evaluate_restore_preview(
    path: LineagePath,
    all_current_docs: List[PathDocument],
) -> RestorePreview:
    """Evaluate the impact of restoring a lineage path.

    Pure function — no DB access.

    Args:
        path: The lineage path to restore.
        all_current_docs: All documents currently marked is_latest=True.

    Returns:
        RestorePreview with lists of documents to activate/demote and warnings.
    """
    path_ids = set(path.doc_ids)
    warnings: List[RestoreWarning] = []

    # Documents to activate: path docs that are NOT currently is_latest
    to_activate = []
    for doc in path.documents:
        if not doc.is_latest:
            to_activate.append(doc.to_dict())

    # Documents to demote: current is_latest docs NOT in the path
    # but sharing the same doc_type_id + display_id with a path doc
    path_keys = {(d.doc_type_id, d.display_id) for d in path.documents}
    to_demote = []
    for doc in all_current_docs:
        if doc.id not in path_ids and (doc.doc_type_id, doc.display_id) in path_keys:
            to_demote.append(doc.to_dict())

    # Advisory warnings

    # Check for stale documents in the path
    for doc in path.documents:
        if doc.is_stale:
            warnings.append(RestoreWarning(
                category="stale_document",
                message=f"{doc.display_id} v{doc.version} was marked stale",
                document_id=str(doc.id),
                doc_type_id=doc.doc_type_id,
            ))

    # Check for missing upstream stages
    from app.domain.models.pipeline_stage import PipelineStage
    path_stages = {d.doc_type_id for d in path.documents}
    checkpoint_order = -1
    for d in path.documents:
        if d.id == path.checkpoint_id:
            try:
                checkpoint_order = PipelineStage.from_doc_type_id(d.doc_type_id).order
            except ValueError:
                pass
            break

    if checkpoint_order > 0:
        for stage in PipelineStage.all_stages_ordered():
            if stage.order < checkpoint_order and stage.doc_type_id not in path_stages:
                warnings.append(RestoreWarning(
                    category="missing_upstream",
                    message=f"No {stage.display_name} document in restored path",
                    doc_type_id=stage.doc_type_id,
                ))

    return RestorePreview(
        checkpoint_id=str(path.checkpoint_id),
        path_document_count=len(path.documents),
        documents_to_activate=to_activate,
        documents_to_demote=to_demote,
        warnings=warnings,
        is_safe=len(warnings) == 0,
    )

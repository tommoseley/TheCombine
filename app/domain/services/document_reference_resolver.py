"""
Document Reference Resolver (ADR-071).

Resolves document references (display_id or document_id) to their
governed document metadata: id, display_id, title, doc_type_id, version.

Supports batch resolution for performance and version-pinned resolution
for binder traceability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document

logger = logging.getLogger(__name__)


@dataclass
class ResolvedReference:
    """Resolved metadata for a document reference."""

    id: str  # UUID as string
    display_id: str
    title: str
    doc_type_id: str
    version: int
    space_id: str


async def resolve_reference(
    db: AsyncSession,
    ref: str,
    space_id: str,
    *,
    version: Optional[int] = None,
) -> Optional[ResolvedReference]:
    """Resolve a single document reference to its metadata.

    Args:
        db: Database session
        ref: display_id (e.g., "WS-142") or document UUID
        space_id: Project/space UUID to scope the lookup
        version: If specified, resolve to this version; otherwise latest

    Returns:
        ResolvedReference or None if not found
    """
    results = await resolve_batch(db, [ref], space_id, versions={ref: version} if version else None)
    return results.get(ref)


async def resolve_batch(
    db: AsyncSession,
    refs: list[str],
    space_id: str,
    *,
    versions: Optional[dict[str, int]] = None,
) -> dict[str, Optional[ResolvedReference]]:
    """Resolve multiple document references in a single query.

    Args:
        db: Database session
        refs: List of display_ids or document UUIDs
        space_id: Project/space UUID to scope the lookup
        versions: Optional dict mapping ref -> version for pinned resolution

    Returns:
        Dict mapping each ref to its ResolvedReference (or None if not found)
    """
    if not refs:
        return {}

    versions = versions or {}

    # Separate UUIDs from display_ids
    uuid_refs = []
    display_id_refs = []
    for ref in refs:
        try:
            UUID(ref)
            uuid_refs.append(ref)
        except ValueError:
            display_id_refs.append(ref)

    results: dict[str, Optional[ResolvedReference]] = {ref: None for ref in refs}

    # Query by display_id (latest unless version-pinned)
    if display_id_refs:
        # For non-pinned: get latest versions
        unpinned = [r for r in display_id_refs if r not in versions]
        pinned = [r for r in display_id_refs if r in versions]

        if unpinned:
            stmt = select(Document).where(
                and_(
                    Document.space_id == space_id,
                    Document.display_id.in_(unpinned),
                    Document.is_latest == True,  # noqa: E712
                )
            )
            result = await db.execute(stmt)
            for doc in result.scalars().all():
                results[doc.display_id] = _to_resolved(doc)

        # For pinned: get specific versions
        for ref in pinned:
            stmt = select(Document).where(
                and_(
                    Document.space_id == space_id,
                    Document.display_id == ref,
                    Document.version == versions[ref],
                )
            )
            result = await db.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc:
                results[ref] = _to_resolved(doc)

    # Query by UUID
    if uuid_refs:
        unpinned_uuids = [r for r in uuid_refs if r not in versions]
        pinned_uuids = [r for r in uuid_refs if r in versions]

        if unpinned_uuids:
            stmt = select(Document).where(
                and_(
                    Document.space_id == space_id,
                    Document.id.in_([UUID(u) for u in unpinned_uuids]),
                )
            )
            result = await db.execute(stmt)
            for doc in result.scalars().all():
                results[str(doc.id)] = _to_resolved(doc)

        for ref in pinned_uuids:
            stmt = select(Document).where(
                and_(
                    Document.space_id == space_id,
                    Document.id == UUID(ref),
                    Document.version == versions[ref],
                )
            )
            result = await db.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc:
                results[ref] = _to_resolved(doc)

    return results


def _to_resolved(doc: Document) -> ResolvedReference:
    """Convert a Document ORM instance to a ResolvedReference."""
    return ResolvedReference(
        id=str(doc.id),
        display_id=doc.display_id,
        title=doc.title or doc.display_id,
        doc_type_id=doc.doc_type_id,
        version=doc.version,
        space_id=str(doc.space_id),
    )

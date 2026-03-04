"""Display ID Service — minting and resolution for ADR-055 Document Identity Standard.

Provides three functions:
- parse_display_id(): Pure parser, splits {TYPE}-{NNN} into (prefix, number_str)
- resolve_display_id(): Resolves prefix to doc_type_id via document_types registry
- mint_display_id(): Mints the next sequential display_id for a doc type in a space
"""

import re
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.document_type import DocumentType

_DISPLAY_ID_PATTERN = re.compile(r'^([A-Z]{2,4})-(\d{3,})$')


def parse_display_id(display_id: str) -> tuple[str, str]:
    """Parse a display_id into (prefix, number_str).

    'WPC-001' -> ('WPC', '001')
    'PD-001' -> ('PD', '001')

    Raises ValueError if format is invalid.
    """
    match = _DISPLAY_ID_PATTERN.match(display_id)
    if not match:
        raise ValueError(f"Invalid display_id format: {display_id!r}. Expected {{TYPE}}-{{NNN}}.")
    return match.group(1), match.group(2)


async def resolve_display_id(db: AsyncSession, display_id: str) -> str:
    """Resolve a display_id prefix to its doc_type_id.

    'WPC-001' -> 'work_package_candidate'
    'PD-001' -> 'project_discovery'

    Raises ValueError if prefix not found in registry.
    """
    prefix, _ = parse_display_id(display_id)
    result = await db.execute(
        select(DocumentType.doc_type_id).where(
            DocumentType.display_prefix == prefix
        )
    )
    doc_type_id = result.scalar()
    if not doc_type_id:
        raise ValueError(f"Unknown display_id prefix: {prefix!r}. Not in document_types registry.")
    return doc_type_id


async def mint_display_id(db: AsyncSession, space_id: UUID, doc_type_id: str) -> str:
    """Mint the next sequential display_id for a document type in a space.

    Minting requires serialized access within a transaction.
    Uses SELECT MAX to find the current highest sequence number.
    """
    result = await db.execute(
        select(DocumentType.display_prefix).where(
            DocumentType.doc_type_id == doc_type_id
        )
    )
    prefix = result.scalar()
    if not prefix:
        raise ValueError(f"Document type {doc_type_id!r} has no display_prefix.")

    result = await db.execute(
        select(func.max(Document.display_id))
        .where(
            Document.space_id == space_id,
            Document.doc_type_id == doc_type_id,
        )
    )
    max_id = result.scalar()

    if max_id:
        _, num_str = parse_display_id(max_id)
        next_num = int(num_str) + 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:03d}"

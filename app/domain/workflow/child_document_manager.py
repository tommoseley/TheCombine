"""Child document lifecycle management.

Extracted from PlanExecutor (WS-CRAP decomposition).
Handles spawning, upserting, stale marking, and commit/notify
for child documents produced by workflow completion.
"""

import logging
from typing import Any, Dict, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import DocumentWorkflowState

# Domain event bus — no API layer import
from app.domain.events import publish_event

logger = logging.getLogger(__name__)


async def spawn_child_documents(
    state: DocumentWorkflowState,
    doc_content: Dict[str, Any],
    parent_id,  # UUID
    parent_title: str,
    db_session: AsyncSession,
    execution_id: str = None,
) -> None:
    """Spawn child documents using the handler's get_child_documents().

    Idempotent: if a child with the same (parent_id, doc_type_id, identifier)
    already exists, it is updated rather than duplicated.

    Drift-aware: children from a previous run that are no longer in the
    current spec are marked stale (superseded), not deleted.

    WS-CRAP-009: Thinned dispatcher -- delegates to pure helpers and
    sub-methods for envelope unwrap, lineage injection, upsert, stale
    marking, and event payload construction.
    """
    from app.domain.handlers.registry import handler_exists, get_handler
    from app.api.models.document import Document
    from app.domain.workflow.child_document_helpers import (
        unwrap_raw_envelope,
        inject_execution_id_into_lineage,
        build_children_event_payload,
    )

    if not handler_exists(state.document_type):
        return

    handler = get_handler(state.document_type)
    unwrapped = unwrap_raw_envelope(doc_content)
    child_specs = handler.get_child_documents(unwrapped, parent_title or "")

    if not child_specs:
        return

    inject_execution_id_into_lineage(child_specs, execution_id)

    existing_children = await load_existing_children(
        parent_id, child_specs, Document, db_session,
    )

    spawned_ids, created_count, updated_count = await run_upsert_loop(
        child_specs, existing_children, state, parent_id, db_session,
    )

    superseded_count = mark_stale_children(existing_children, spawned_ids)

    await commit_and_notify_children(
        created_count, updated_count, superseded_count,
        state, parent_id, child_specs, existing_children, spawned_ids,
        build_children_event_payload,
        db_session,
    )


async def upsert_child_document(
    spec: dict,
    existing_children: dict,
    state: DocumentWorkflowState,
    parent_id,  # UUID
    db_session: AsyncSession,
) -> str:
    """Upsert a single child document. Returns 'created', 'updated', or 'skipped'."""
    from app.api.models.document import Document
    from uuid import UUID

    identifier = spec.get("identifier", "")
    if not identifier:
        logger.error(
            f"Child spec for {spec.get('doc_type_id')} missing identifier - "
            f"skipping (would violate multi-instance uniqueness)"
        )
        return "skipped"

    existing = existing_children.get(identifier)
    if existing:
        # ADR-063: Create new version instead of mutating in place
        new_version = existing.version + 1
        # Mark old version as superseded
        existing.is_latest = False
        existing.status = "superseded"

        from app.domain.services.display_id_service import mint_display_id
        # Reuse existing display_id for the new version
        child_doc = Document(
            space_type="project",
            space_id=UUID(state.project_id),
            doc_type_id=spec["doc_type_id"],
            title=spec["title"],
            content=spec["content"],
            version=new_version,
            is_latest=True,
            status="draft",
            created_by=None,
            parent_document_id=parent_id,
            instance_id=identifier,
            display_id=existing.display_id,
        )
        child_doc.update_revision_hash()
        db_session.add(child_doc)
        logger.debug(f"Created new version {new_version} for child: {identifier}")
        return "versioned"
    else:
        # Mint a human-readable display_id for the child (ADR-055)
        from app.domain.services.display_id_service import mint_display_id
        from uuid import UUID
        did = await mint_display_id(db_session, UUID(state.project_id), spec["doc_type_id"])

        child_doc = Document(
            space_type="project",
            space_id=UUID(state.project_id),
            doc_type_id=spec["doc_type_id"],
            title=spec["title"],
            content=spec["content"],
            version=1,
            is_latest=True,
            status="draft",
            created_by=None,
            parent_document_id=parent_id,
            instance_id=identifier,
            display_id=did,
        )
        child_doc.update_revision_hash()
        db_session.add(child_doc)
        logger.debug(f"Created child: {identifier} (instance_id={identifier})")
        return "created"


def mark_stale_children(
    existing_children: dict,
    spawned_ids: set,
) -> int:
    """Mark children no longer in spec as stale. Returns count."""
    count = 0
    for child_id, child_doc in existing_children.items():
        if child_id not in spawned_ids:
            child_doc.is_latest = False
            if hasattr(child_doc, 'mark_stale'):
                child_doc.mark_stale()
            else:
                child_doc.lifecycle_state = "stale"
            count += 1
            logger.info(f"Superseded child: {child_id} (no longer in parent)")
    return count


async def load_existing_children(
    parent_id,  # UUID
    child_specs: list,
    Document,
    db_session: AsyncSession,
) -> dict:
    """Load existing children for idempotency check, keyed by instance_id."""
    existing_result = await db_session.execute(
        select(Document).where(
            Document.parent_document_id == parent_id,
            Document.doc_type_id.in_([s["doc_type_id"] for s in child_specs]),
            Document.is_latest == True,
        )
    )
    return {
        doc.instance_id: doc
        for doc in existing_result.scalars().all()
        if doc.instance_id
    }


async def run_upsert_loop(
    child_specs: list,
    existing_children: dict,
    state: DocumentWorkflowState,
    parent_id,  # UUID
    db_session: AsyncSession,
) -> tuple:
    """Run upsert for each child spec. Returns (spawned_ids, created, updated)."""
    spawned_ids: Set[str] = set()
    created_count = updated_count = 0
    for spec in child_specs:
        try:
            result = await upsert_child_document(
                spec, existing_children, state, parent_id, db_session,
            )
            if result == "created":
                created_count += 1
            elif result == "updated":
                updated_count += 1
            if spec.get("identifier"):
                spawned_ids.add(spec["identifier"])
        except Exception as e:
            logger.error(
                f"Failed to upsert child document "
                f"{spec.get('doc_type_id')}/{spec.get('identifier')}: {e}"
            )
    return spawned_ids, created_count, updated_count


async def commit_and_notify_children(
    created_count: int,
    updated_count: int,
    superseded_count: int,
    state: DocumentWorkflowState,
    parent_id,  # UUID
    child_specs: list,
    existing_children: dict,
    spawned_ids: set,
    build_children_event_payload,
    db_session: AsyncSession,
) -> None:
    """Commit DB changes and publish SSE event if anything changed."""
    if not (created_count or updated_count or superseded_count):
        return

    await db_session.commit()
    logger.info(
        f"Spawned children from {state.document_type} (parent={parent_id}): "
        f"created={created_count}, updated={updated_count}, "
        f"superseded={superseded_count}"
    )

    payload = build_children_event_payload(
        child_specs, set(existing_children.keys()), spawned_ids,
    )
    try:
        await publish_event(state.project_id, "children_updated", {
            "parent_document_type": state.document_type,
            "child_doc_type": "work_package",
            **payload,
        })
    except Exception as e:
        logger.warning(f"Failed to publish children_updated event: {e}")

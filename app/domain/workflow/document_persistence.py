"""Document persistence logic extracted from PlanExecutor.

Handles persisting produced documents to the database on workflow completion.
Extracted in second-pass decomposition of plan_executor.py.

Contains:
- persist_produced_documents: Main persistence orchestrator (~171 LOC)
- store_produced_document: In-flight document storage to context_state
- handle_intake_gate_result: Intake gate metadata + pause-for-review
"""

import logging
from typing import Any, Callable, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
)
from app.domain.workflow.edge_router import EdgeRouter
from app.domain.workflow.plan_models import Node, NodeType, WorkflowPlan

logger = logging.getLogger(__name__)


async def store_produced_document(
    result_produced_document: Optional[Dict[str, Any]],
    result_metadata: Optional[Dict[str, Any]],
    state: DocumentWorkflowState,
    pin_invariants_fn: Callable,
    filter_excluded_fn: Callable,
) -> None:
    """Store produced document in context_state after invariant pinning.

    Args:
        result_produced_document: The produced document from NodeResult
        result_metadata: Metadata from NodeResult
        state: Current execution state
        pin_invariants_fn: Async callable to pin invariants into document
        filter_excluded_fn: Async callable to filter excluded topics
    """
    if not result_produced_document:
        return

    produces_key = result_metadata.get("produces", "last_produced") if result_metadata else "last_produced"

    # ADR-042/ADR-047: Pin invariants into known_constraints BEFORE storing
    pinned_document = await pin_invariants_fn(
        result_produced_document, state
    )

    # ADR-042/ADR-047: Filter excluded topics from recommendations
    filtered_document = await filter_excluded_fn(
        pinned_document, state
    )

    state.update_context_state({
        f"document_{produces_key}": filtered_document,
        "last_produced_document": pinned_document,
    })
    logger.info(f"Stored produced document as document_{produces_key}")


async def handle_intake_gate_result(
    result_outcome: str,
    result_metadata: Optional[Dict[str, Any]],
    current_node: Node,
    state: DocumentWorkflowState,
    plan: WorkflowPlan,
    persistence: Any,
) -> bool:
    """Handle intake gate metadata + pause-for-review. Returns True if paused.

    Args:
        result_outcome: The outcome string from NodeResult
        result_metadata: Metadata from NodeResult
        current_node: The node that was executed
        state: Current execution state
        plan: Workflow plan
        persistence: State persistence backend (for saving)

    Returns:
        True if execution was paused for intake review
    """
    is_intake_gate = (
        current_node.type == NodeType.INTAKE_GATE or
        (current_node.type == NodeType.GATE and current_node.internals)
    )
    if not is_intake_gate or result_outcome != "qualified":
        return False

    from app.domain.workflow.result_handling import (
        extract_metadata_by_keys, INTAKE_METADATA_KEYS, should_pause_for_intake_review,
    )

    metadata = result_metadata or {}
    intake_metadata = extract_metadata_by_keys(metadata, INTAKE_METADATA_KEYS)
    if intake_metadata:
        state.update_context_state(intake_metadata)
        logger.info(f"Stored intake gate metadata: {list(intake_metadata.keys())}")

    if should_pause_for_intake_review(
        current_node.type == NodeType.INTAKE_GATE,
        metadata.get("phase"),
        state.context_state.get("phase"),
    ):
        # Advance to next node BEFORE pausing (so resume starts at generation)
        router = EdgeRouter(plan)
        next_node_id, _ = router.get_next_node(
            current_node_id=current_node.node_id,
            outcome=result_outcome,
            state=state,
        )
        if next_node_id:
            state.current_node_id = next_node_id
            logger.info(f"Advanced to {next_node_id} before pausing for review")

        state.set_paused(prompt=None, choices=None)
        await persistence.save(state)
        logger.info("Intake qualified - pausing for user review")
        return True

    return False


async def persist_produced_documents(
    state: DocumentWorkflowState,
    plan: WorkflowPlan,
    db_session: AsyncSession,
    persistence: Any,
    derive_constraint_domain_fn: Callable,
    build_invariant_statement_fn: Callable,
    spawn_child_documents_fn: Callable,
) -> None:
    """Persist produced documents to the documents table.

    Called on successful workflow completion (stabilized).
    Delegates pure data assembly to document_assembly module.

    Args:
        state: Current execution state
        plan: Workflow plan
        db_session: SQLAlchemy async session
        persistence: State persistence backend
        derive_constraint_domain_fn: Function to derive semantic domain from constraint ID
        build_invariant_statement_fn: Function to build invariant statement
        spawn_child_documents_fn: Async callable to spawn child documents
    """
    if not db_session:
        logger.warning("No db_session - skipping document persistence")
        return

    from app.api.models.document import Document
    from uuid import UUID
    from app.domain.workflow.document_assembly import (
        enforce_system_meta,
        derive_document_title,
        promote_pgc_invariants_to_document,
        embed_pgc_clarifications,
    )

    doc_key = f"document_{state.document_type}"
    produced_doc = state.context_state.get(doc_key)

    if not produced_doc:
        logger.warning(f"No produced document found at {doc_key}")
        return

    try:
        # Pure: enforce system-owned meta fields
        doc_content, meta_warnings = enforce_system_meta(
            produced_doc,
            execution_id=state.execution_id,
            document_type=state.document_type,
            workflow_id=state.workflow_id,
        )
        for w in meta_warnings:
            logger.warning(w)

        system_artifact_id = doc_content["meta"]["artifact_id"]

        # Pure: promote PGC invariants into document structure (ADR-042)
        context_invariants = state.context_state.get("pgc_invariants", [])
        inv_result = promote_pgc_invariants_to_document(
            doc_content,
            context_invariants,
            derive_domain_fn=derive_constraint_domain_fn,
            build_statement_fn=build_invariant_statement_fn,
        )
        if inv_result:
            logger.info(
                f"ADR-042: Promoted {len(inv_result)} PGC invariants to document structure"
            )

        # Pure: embed PGC clarifications for traceability
        clarifications = state.context_state.get("pgc_clarifications", [])
        embedded = embed_pgc_clarifications(doc_content, clarifications)
        if embedded:
            logger.info(
                f"Embedded {len(embedded)} PGC clarifications in document"
            )

        # Derive title -- may need DB lookups for fallback
        doc_title = doc_content.get("title") or doc_content.get("project_name")
        project_name = None
        doc_type_name = None
        if not doc_title:
            from app.api.models.project import Project as ProjectModel
            from app.api.models.document_type import DocumentType as DocTypeModel
            proj_result = await db_session.execute(
                select(ProjectModel.name).where(
                    ProjectModel.id == UUID(state.project_id)
                )
            )
            project_name = proj_result.scalar_one_or_none()
            dt_result = await db_session.execute(
                select(DocTypeModel.name).where(
                    DocTypeModel.doc_type_id == state.document_type
                )
            )
            doc_type_name = dt_result.scalar_one_or_none()

        doc_title = derive_document_title(
            doc_content,
            state.document_type,
            project_name=project_name,
            doc_type_display_name=doc_type_name,
        )

        # ADR-063: Check for existing document of this type (even stale)
        # If found, reuse its display_id and increment version
        from sqlalchemy import func as sa_func
        existing_result = await db_session.execute(
            select(Document.display_id, sa_func.max(Document.version))
            .where(
                Document.space_type == "project",
                Document.space_id == UUID(state.project_id),
                Document.doc_type_id == state.document_type,
            )
            .group_by(Document.display_id)
            .order_by(sa_func.max(Document.version).desc())
            .limit(1)
        )
        existing = existing_result.first()

        if existing:
            # Reuse existing display_id, increment version
            did = existing[0]
            new_version = existing[1] + 1
            # Mark any current/latest docs as superseded
            await db_session.execute(
                update(Document)
                .where(
                    Document.space_type == "project",
                    Document.space_id == UUID(state.project_id),
                    Document.doc_type_id == state.document_type,
                    Document.is_latest == True,
                )
                .values(is_latest=False, status="superseded")
            )
        else:
            # First document of this type -- mint new display_id
            from app.domain.services.display_id_service import mint_display_id
            did = await mint_display_id(db_session, UUID(state.project_id), state.document_type)
            new_version = 1

        # Create the document record (I/O)
        document = Document(
            space_type="project",
            space_id=UUID(state.project_id),
            doc_type_id=state.document_type,
            title=doc_title,
            content=doc_content,
            version=new_version,
            is_latest=True,
            status="draft",
            created_by=None,
            display_id=did,
        )
        document.update_revision_hash()

        db_session.add(document)
        await db_session.commit()

        # Update context_state with system-corrected document
        doc_key = f"document_{state.document_type}"
        state.context_state[doc_key] = doc_content
        await persistence.save(state)

        logger.info(
            f"Persisted {state.document_type} document to database "
            f"(id={document.id}, artifact_id={system_artifact_id}, project={state.project_id})"
        )

        # Spawn child documents if the handler defines them
        await spawn_child_documents_fn(
            state, doc_content, document.id, document.title,
            execution_id=state.execution_id,
        )

    except Exception as e:
        logger.error(f"Failed to persist document: {e}")
        # Don't fail the workflow - document is still in context_state
        await db_session.rollback()

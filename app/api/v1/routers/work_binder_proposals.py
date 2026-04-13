"""Work Binder proposal routes — WS-WB-025.

Endpoints for proposing Work Statements via LLM.
"""

import copy
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.core.database import get_db
from app.domain.services.wb_audit_service import (
    build_audit_event as build_wb_audit_event,
)
from app.domain.services.ws_proposal_service import (
    build_ws_documents,
    build_ws_index_entries,
    validate_proposal_gates,
)
from app.domain.services.document_builder_pure import apply_post_processing
from app.domain.services.wp_edition_service import apply_edition_bump
from app.domain.services.task_execution_service import (
    TaskExecutionError,
    TaskOutputParseError,
    TaskOutputValidationError,
    TaskPromptNotFoundError,
    execute_task,
)

from app.api.v1.routers.work_binder_common import (
    ProposeWSRequest,
    ProposeWSResponse,
    _find_ta_for_project,
    _load_wp_document,
    _resolve_project,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["work-binder"])


# ===========================================================================
# WS-WB-025: Propose Work Statements (LLM Draft Station)
# ===========================================================================


@router.post("/propose-ws", response_model=ProposeWSResponse)
async def propose_work_statements(
    request: ProposeWSRequest,
    db: AsyncSession = Depends(get_db),
) -> ProposeWSResponse:
    """Propose WS drafts for a promoted WP via LLM.

    This is the first LLM boundary crossing in the Work Binder.
    Gates: TA must be ready, WP ws_index must be empty.
    Produces DRAFT-only WS artifacts, validated before persistence.
    """
    # --- Resolve project FIRST (scoping) ---
    project = await _resolve_project(db, request.project_id)

    # --- Resolve WP (scoped to project) ---
    wp_doc = await _load_wp_document(db, request.wp_id, space_id=str(project.id))
    wp_content = dict(wp_doc.content or {})

    # --- Resolve TA ---
    ta_doc = await _find_ta_for_project(db, project.id)

    # --- Gate checks (mechanical) ---
    gate_errors = validate_proposal_gates(wp_content, ta_doc)
    if gate_errors:
        # Determine status code: ws_index conflict -> 409, else 400
        status_code = (
            status.HTTP_409_CONFLICT
            if any("already has Work Statements" in e for e in gate_errors)
            else status.HTTP_400_BAD_REQUEST
        )

        # Audit: rejection
        audit_evt = build_wb_audit_event(
            event_type="ws_proposal_rejected",
            entity_id=request.wp_id,
            entity_type="work_package",
            mutation_data={
                "project_id": request.project_id,
                "reason": "; ".join(gate_errors),
            },
            actor="system",
        )
        logger.info("AUDIT: %s", audit_evt)

        raise HTTPException(
            status_code=status_code,
            detail="; ".join(gate_errors),
        )

    # --- Audit: proposal requested ---
    ta_version = str(ta_doc.version) if ta_doc else "unknown"
    audit_req = build_wb_audit_event(
        event_type="ws_proposal_requested",
        entity_id=request.wp_id,
        entity_type="work_package",
        mutation_data={
            "project_id": request.project_id,
            "ta_version": ta_version,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_req)

    # --- LLM call via task execution primitive (WS-WB-022) ---
    import json as _json
    import os as _os
    wp_json = _json.dumps(wp_content, indent=2, default=str)
    ta_json = _json.dumps(ta_doc.content or {}, indent=2, default=str)

    # Wire up LLM client
    from app.llm.providers.anthropic import AnthropicProvider
    from app.domain.workflow.nodes.llm_executors import LoggingLLMService

    api_key = _os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ANTHROPIC_API_KEY not configured",
        )
    llm_client = LoggingLLMService(
        provider=AnthropicProvider(api_key=api_key),
        default_max_tokens=16384,
    )

    try:
        result = await execute_task(
            task_id="propose_work_statements",
            version="1.0.0",
            inputs={"work_package": wp_json, "technical_architecture": ta_json},
            expected_schema_id="work_statement",
            llm_client=llm_client,
        )
    except TaskPromptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task prompt not found: {exc}",
        )
    except TaskOutputParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM output parse failed: {exc}",
        )
    except TaskOutputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM output schema validation failed: {exc}",
        )
    except TaskExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {exc}",
        )

    # --- Parse LLM output ---
    # Output may be a single WS dict or a list of WS dicts
    raw_output = result["output"]
    if isinstance(raw_output, dict):
        ws_items = [raw_output]
    elif isinstance(raw_output, list):
        ws_items = raw_output
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LLM output is not a dict or list of WS objects",
        )

    if not ws_items:
        return ProposeWSResponse(
            wp_id=request.wp_id,
            created=False,
            ws_ids=[],
        )

    # --- Mint display IDs and build WS documents ---
    # Replace LLM-generated ws_ids with minted sequential IDs.
    # Mint the first ID via DB query, then increment locally for the batch
    # (unflushed rows aren't visible to subsequent MAX queries).
    from app.domain.services.display_id_service import mint_display_id, parse_display_id
    first_ws_id = await mint_display_id(db, wp_doc.space_id, "work_statement")
    prefix, num_str = parse_display_id(first_ws_id)
    first_num = int(num_str)
    for i, ws_item in enumerate(ws_items):
        ws_item["ws_id"] = f"{prefix}-{first_num + i:03d}"

    ws_docs_data = build_ws_documents(ws_items, request.wp_id)
    ws_index_entries = build_ws_index_entries(ws_items)

    # --- Persist WS documents ---
    ws_ids = []
    for ws_data in ws_docs_data:
        ws_id = ws_data["ws_id"]
        apply_post_processing(ws_data, "work_statement")
        ws_doc = Document(
            space_type=wp_doc.space_type,
            space_id=wp_doc.space_id,
            doc_type_id="work_statement",
            title=ws_data.get("title", ws_id),
            content=ws_data,
            version=1,
            status="draft",
            lifecycle_state="complete",
            display_id=ws_id,
            created_by="system",
            created_by_type="llm_proposal",
        )
        ws_doc.update_revision_hash()
        db.add(ws_doc)
        ws_ids.append(ws_id)

        # Audit: per-WS
        audit_ws = build_wb_audit_event(
            event_type="ws_proposed",
            entity_id=ws_id,
            entity_type="work_statement",
            mutation_data={
                "wp_id": request.wp_id,
                "project_id": request.project_id,
            },
            actor="system",
        )
        logger.info("AUDIT: %s", audit_ws)

    # --- Update WP ws_index (new edition) ---
    old_content = copy.deepcopy(wp_content)
    wp_content["ws_index"] = ws_index_entries
    wp_content = apply_edition_bump(wp_content, old_content, "system")
    wp_doc.content = wp_content

    await db.flush()

    # Audit: ws_index updated
    audit_idx = build_wb_audit_event(
        event_type="wp_ws_index_updated",
        entity_id=request.wp_id,
        entity_type="work_package",
        mutation_data={
            "before_count": 0,
            "after_count": len(ws_ids),
            "ws_ids": ws_ids,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_idx)

    logger.info(
        "Proposed %d WS drafts for WP %s", len(ws_ids), request.wp_id,
    )

    return ProposeWSResponse(
        wp_id=request.wp_id,
        created=True,
        ws_ids=ws_ids,
    )

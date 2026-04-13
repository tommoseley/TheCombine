"""Repair Proposal API routes (ADR-065).

Provides endpoints for:
- Listing proposals for an artifact
- Requesting a repair for a component
- Deciding on a proposal (accept/reject/regenerate)
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repair", tags=["repair"])


@router.get("/proposals")
async def list_proposals(
    artifact_id: str = Query(..., description="Target artifact (document) ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """List repair proposals for an artifact."""
    from app.domain.repositories.repair_proposal_repository import (
        PostgresRepairProposalRepository,
    )

    repo = PostgresRepairProposalRepository(db)
    proposals = await repo.get_by_artifact(UUID(artifact_id), status=status)

    return JSONResponse([
        {
            "id": str(p.id),
            "artifact_id": str(p.artifact_id),
            "artifact_type": p.artifact_type,
            "component_identifier": p.component_identifier,
            "trigger_finding": p.trigger_finding,
            "proposed_payload": p.proposed_payload,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "created_by": p.created_by,
            "decision_at": p.decision_at.isoformat() if p.decision_at else None,
            "decision_by": p.decision_by,
        }
        for p in proposals
    ])


@router.post("/request")
async def request_repair(
    artifact_id: str = Query(..., description="TA document ID"),
    component_name: str = Query(..., description="Component name to repair"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Request a repair proposal for a specific TA component.

    Finds the component, runs validation, generates a repair proposal via LLM.
    """
    from sqlalchemy import select
    from app.api.models.document import Document
    from app.domain.services.cross_layer_evaluator import validate_ta_owns
    from app.domain.services.repair_service import generate_repair_proposal
    from app.domain.repositories.repair_proposal_repository import (
        PostgresRepairProposalRepository,
    )

    # Load the TA document
    result = await db.execute(
        select(Document).where(Document.id == UUID(artifact_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse(
            status_code=404,
            content={"error": f"Document {artifact_id} not found"},
        )

    content = doc.content or {}
    components = content.get("components") or []

    # Find the target component
    target = None
    for c in components:
        if c.get("name") == component_name:
            target = c
            break

    if target is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Component '{component_name}' not found in document"},
        )

    # Get the finding for this component
    report = validate_ta_owns(content)
    finding = None
    for f in report.findings:
        if f.component_name == component_name:
            finding = f
            break

    if finding is None:
        return JSONResponse(
            status_code=409,
            content={"error": f"No ownership finding for component '{component_name}'"},
        )

    # Create LLM client
    from app.llm.client import get_llm_client
    llm_client = get_llm_client()

    repo = PostgresRepairProposalRepository(db)
    proposal = await generate_repair_proposal(
        artifact_id=UUID(artifact_id),
        component=target,
        finding=finding,
        ta_components=components,
        llm_client=llm_client,
        repo=repo,
        actor="operator",
    )

    if proposal is None:
        return JSONResponse(
            status_code=422,
            content={"error": "LLM produced invalid repair output"},
        )

    await db.commit()

    return JSONResponse({
        "id": str(proposal.id),
        "component_identifier": proposal.component_identifier,
        "proposed_payload": proposal.proposed_payload,
        "status": proposal.status,
    })


@router.post("/proposals/{proposal_id}/decide")
async def decide_proposal(
    proposal_id: str,
    decision: str = Query(..., description="accept, reject, or regenerate"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Accept, reject, or regenerate a repair proposal."""
    from app.domain.repositories.repair_proposal_repository import (
        PostgresRepairProposalRepository,
    )

    if decision not in ("accept", "reject", "regenerate"):
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid decision: {decision}. Must be accept/reject/regenerate."},
        )

    repo = PostgresRepairProposalRepository(db)
    proposal = await repo.get_by_id(UUID(proposal_id))

    if not proposal:
        return JSONResponse(
            status_code=404,
            content={"error": f"Proposal {proposal_id} not found"},
        )

    if proposal.status != "pending":
        return JSONResponse(
            status_code=409,
            content={"error": f"Proposal is already {proposal.status}"},
        )

    if decision == "regenerate":
        # Supersede current, then re-request (handled by caller)
        await repo.update_status(UUID(proposal_id), "superseded", "operator")
        await db.commit()
        return JSONResponse({
            "status": "superseded",
            "message": "Proposal superseded. Request a new repair.",
        })

    if decision == "reject":
        updated = await repo.update_status(UUID(proposal_id), "rejected", "operator")
        await db.commit()
        return JSONResponse({
            "id": str(updated.id),
            "status": updated.status,
            "decision_by": updated.decision_by,
        })

    # Accept: update status, then apply mutation + reevaluate
    updated = await repo.update_status(UUID(proposal_id), "accepted", "operator")

    from app.domain.services.repair_mutation import apply_accepted_proposal
    result = await apply_accepted_proposal(updated, db)

    if not result["success"]:
        # Revert to pending if mutation failed
        await repo.update_status(UUID(proposal_id), "pending", "system")
        await db.commit()
        return JSONResponse(
            status_code=409,
            content={"error": result["error"]},
        )

    await db.commit()

    return JSONResponse({
        "id": str(updated.id),
        "status": updated.status,
        "decision_by": updated.decision_by,
        "finding_cleared": result["finding_cleared"],
    })

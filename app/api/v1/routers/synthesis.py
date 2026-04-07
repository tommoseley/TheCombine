"""
Binder Synthesis endpoints (ADR-070).

POST /{project_id}/synthesis — trigger synthesis analysis
GET  /{project_id}/synthesis — get latest synthesis delta
PATCH /{project_id}/synthesis/findings/{finding_id} — operator decision
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.models.document import Document
from app.domain.services.synthesis_service import execute_synthesis
from app.domain.services.binder_renderer import render_project_binder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["synthesis"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SynthesisTriggerResponse(BaseModel):
    status: str
    project_id: str
    document_id: str
    action_count: int
    question_count: int
    agreement_count: int


class FindingDecision(BaseModel):
    decision: str = Field(..., pattern="^(accept|reject|modify)$")
    note: Optional[str] = None


class FindingDecisionResponse(BaseModel):
    finding_id: str
    decision: str
    note: Optional[str]
    decided_at: str
    decided_by: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{project_id}/synthesis")
async def trigger_synthesis(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> SynthesisTriggerResponse:
    """Trigger binder synthesis analysis for a project.

    Renders the binder, runs dual-instance synthesis, persists the delta
    as a synthesis_delta document.
    """
    from sqlalchemy import select, and_

    # 1. Load project documents for binder rendering
    stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    if not docs:
        raise HTTPException(status_code=404, detail="No documents found for project")

    # 2. Get project title from first doc's space or use project_id
    project_title = project_id

    # 3. Build binder docs list for renderer
    from app.config.package_loader import PackageLoader, reset_package_loader
    from app.domain.services.ia_gate import verify_document_ia
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent.parent.parent / "combine-config"
    loader = PackageLoader(config_path)
    active = loader.get_active_releases()

    binder_docs = []
    for doc in docs:
        version = active.get(doc.doc_type_id, "1.0.0")
        try:
            pkg = loader.get_document_type(doc.doc_type_id, version)
            ia = pkg.information_architecture if pkg else None
        except Exception:
            ia = None

        entry = {
            "display_id": doc.display_id or doc.doc_type_id,
            "doc_type_id": doc.doc_type_id,
            "title": doc.title or doc.doc_type_id,
            "content": doc.content or {},
            "ia": ia,
            "id": str(doc.id),
            "parent_document_id": str(doc.parent_document_id) if doc.parent_document_id else None,
        }
        if doc.doc_type_id == "work_package":
            entry["ws_index"] = (doc.content or {}).get("ws_index", [])
        binder_docs.append(entry)

    # 4. Render binder
    binder_content = render_project_binder(
        project_id=project_id,
        project_title=project_title,
        documents=binder_docs,
    )

    # 5. Execute synthesis
    delta = await execute_synthesis(
        project_id=project_id,
        binder_content=binder_content,
        binder_document_count=len(binder_docs),
    )

    # 6. Persist as document
    delta_doc = Document(
        id=uuid4(),
        space_type="project",
        space_id=project_id,
        doc_type_id="synthesis_delta",
        display_id=f"SD-{str(uuid4())[:8].upper()}",
        title="Synthesis Delta",
        content=delta.to_dict(),
        version=1,
        is_latest=True,
        lifecycle_state="complete",
        status="active",
        builder_metadata={
            "generator": "synthesis_service",
            "adr": "ADR-070",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Mark any prior synthesis_delta as not latest
    from sqlalchemy import update
    await db.execute(
        update(Document)
        .where(
            and_(
                Document.space_id == project_id,
                Document.doc_type_id == "synthesis_delta",
                Document.is_latest == True,  # noqa: E712
            )
        )
        .values(is_latest=False)
    )

    db.add(delta_doc)
    await db.commit()

    return SynthesisTriggerResponse(
        status="complete",
        project_id=project_id,
        document_id=str(delta_doc.id),
        action_count=len(delta.actions),
        question_count=len(delta.questions),
        agreement_count=delta.agreement_count,
    )


@router.get("/{project_id}/synthesis")
async def get_synthesis_delta(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest synthesis delta for a project."""
    from sqlalchemy import select, and_

    stmt = (
        select(Document)
        .where(
            and_(
                Document.space_id == project_id,
                Document.doc_type_id == "synthesis_delta",
                Document.is_latest == True,  # noqa: E712
            )
        )
        .order_by(Document.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="No synthesis delta found for project")

    return {
        "document_id": str(doc.id),
        "project_id": project_id,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "content": doc.content,
        "operator_decisions": doc.content.get("_operator_decisions", {}),
    }


@router.patch("/{project_id}/synthesis/findings/{finding_id}")
async def record_finding_decision(
    project_id: str,
    finding_id: str,
    body: FindingDecision,
    db: AsyncSession = Depends(get_db),
) -> FindingDecisionResponse:
    """Record an operator decision (accept/reject/modify) for a synthesis finding."""
    from sqlalchemy import select, and_

    stmt = (
        select(Document)
        .where(
            and_(
                Document.space_id == project_id,
                Document.doc_type_id == "synthesis_delta",
                Document.is_latest == True,  # noqa: E712
            )
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="No synthesis delta found")

    # Store decision in document content
    content = dict(doc.content)
    decisions = content.setdefault("_operator_decisions", {})
    decided_at = datetime.now(timezone.utc).isoformat()

    decisions[finding_id] = {
        "decision": body.decision,
        "note": body.note,
        "decided_at": decided_at,
        "decided_by": "operator",
    }

    doc.content = content
    await db.commit()

    return FindingDecisionResponse(
        finding_id=finding_id,
        decision=body.decision,
        note=body.note,
        decided_at=decided_at,
        decided_by="operator",
    )

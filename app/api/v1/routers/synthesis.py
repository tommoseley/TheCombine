"""
Binder Synthesis endpoints (ADR-070).

POST /{project_id}/synthesis — trigger synthesis analysis
GET  /{project_id}/synthesis — get latest synthesis delta
PATCH /{project_id}/synthesis/findings/{finding_id} — operator decision
POST /{project_id}/synthesis/findings/{finding_id}/explain — advisor context
POST /{project_id}/synthesis/apply — apply accepted actions via correction gate
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
        version = active.get_doc_type_version(doc.doc_type_id) or "1.0.0"
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

    # 5. Create LLM client and execute synthesis
    import os
    from app.llm.providers.anthropic import AnthropicProvider
    from app.domain.workflow.nodes.llm_executors import LoggingLLMService

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    llm_client = LoggingLLMService(
        provider=AnthropicProvider(api_key=api_key),
        default_max_tokens=16384,
    )

    delta = await execute_synthesis(
        project_id=project_id,
        binder_content=binder_content,
        binder_document_count=len(binder_docs),
        llm_client=llm_client,
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
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(doc, "content")
    await db.commit()

    return FindingDecisionResponse(
        finding_id=finding_id,
        decision=body.decision,
        note=body.note,
        decided_at=decided_at,
        decided_by="operator",
    )


# ---------------------------------------------------------------------------
# Advisor — explain a finding to help operator decide
# ---------------------------------------------------------------------------


class AdvisorResponse(BaseModel):
    finding_id: str
    whats_happening: str
    what_the_plan_says: str
    whats_missing: str
    options_and_tradeoffs: str
    impact: str
    consulted_at: str


@router.post("/{project_id}/synthesis/findings/{finding_id}/explain")
async def explain_finding(
    project_id: str,
    finding_id: str,
    db: AsyncSession = Depends(get_db),
) -> AdvisorResponse:
    """Get advisor context for a synthesis finding.

    Calls the synthesis_advisor task prompt with the finding's question,
    evidence, and binder context. Returns structured explanation to help
    the operator make an informed decision. Non-authoritative — explains
    but does not recommend.

    The consultation is recorded as a timestamp on the finding for
    traceability, but the advisory content itself is not persisted.
    """
    from sqlalchemy import select, and_
    from app.domain.services.task_execution_service import execute_task

    # 1. Load synthesis delta
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

    content = doc.content or {}

    # 2. Find the specific finding
    finding = None
    for action in content.get("actions", []):
        aid = f"{action.get('action_type')}-{','.join(action.get('targets', []))}"
        if aid == finding_id:
            finding = action
            break

    if not finding:
        for question in content.get("questions", []):
            if question.get("finding_id") == finding_id:
                finding = question
                break

    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

    # 3. Build advisor inputs
    decision_question = finding.get("question") or finding.get("headline") or finding.get("rationale", "")
    severity = finding.get("severity", "advisory")

    evidence_lines = []
    for ev in finding.get("evidence", []):
        evidence_lines.append(
            f"{ev.get('artifact_title', 'Unknown')} ({ev.get('artifact_id', '?')}):\n"
            f"  {ev.get('excerpt', '')}"
        )
    evidence_text = "\n\n".join(evidence_lines) if evidence_lines else "No evidence excerpts available."

    artifact_lines = []
    for ev in finding.get("evidence", []):
        artifact_lines.append(f"- {ev.get('artifact_title', 'Unknown')} ({ev.get('artifact_id', '?')})")
    artifacts_text = "\n".join(artifact_lines) if artifact_lines else "None specified."

    # 4. Render binder for context (reuse trigger logic)
    from app.config.package_loader import PackageLoader
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent.parent.parent / "combine-config"
    loader = PackageLoader(config_path)
    active = loader.get_active_releases()

    docs_stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    docs_result = await db.execute(docs_stmt)
    all_docs = docs_result.scalars().all()

    binder_docs = []
    for d in all_docs:
        if d.doc_type_id == "synthesis_delta":
            continue
        version = active.get_doc_type_version(d.doc_type_id) or "1.0.0"
        try:
            pkg = loader.get_document_type(d.doc_type_id, version)
            ia = pkg.information_architecture if pkg else None
        except Exception:
            ia = None
        binder_docs.append({
            "display_id": d.display_id or d.doc_type_id,
            "doc_type_id": d.doc_type_id,
            "title": d.title or d.doc_type_id,
            "content": d.content or {},
            "ia": ia,
            "id": str(d.id),
            "parent_document_id": str(d.parent_document_id) if d.parent_document_id else None,
        })

    from app.domain.services.binder_renderer import render_project_binder
    binder_context = render_project_binder(
        project_id=project_id,
        project_title=project_id,
        documents=binder_docs,
    )

    # 5. Execute advisor task
    import os
    from app.llm.providers.anthropic import AnthropicProvider
    from app.domain.workflow.nodes.llm_executors import LoggingLLMService

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    llm_client = LoggingLLMService(
        provider=AnthropicProvider(api_key=api_key),
        default_max_tokens=4096,
    )

    advisor_result = await execute_task(
        task_id="synthesis_advisor",
        version="1.0.0",
        inputs={
            "decision_question": decision_question,
            "severity": severity,
            "evidence_excerpts": evidence_text,
            "artifacts": artifacts_text,
            "binder_context": binder_context,
        },
        expected_schema_id="synthesis_advisor",
        llm_client=llm_client,
    )

    output = advisor_result["output"]
    consulted_at = datetime.now(timezone.utc).isoformat()

    # 6. Record consultation timestamp on finding (traceability)
    decisions = content.setdefault("_operator_decisions", {})
    finding_meta = decisions.setdefault(finding_id, {})
    finding_meta["advisor_consulted_at"] = consulted_at
    doc.content = dict(content)
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(doc, "content")
    await db.commit()

    logger.info("Advisor consulted for finding %s in project %s", finding_id, project_id)

    return AdvisorResponse(
        finding_id=finding_id,
        whats_happening=output.get("whats_happening", ""),
        what_the_plan_says=output.get("what_the_plan_says", ""),
        whats_missing=output.get("whats_missing", ""),
        options_and_tradeoffs=output.get("options_and_tradeoffs", ""),
        impact=output.get("impact", ""),
        consulted_at=consulted_at,
    )


# ---------------------------------------------------------------------------
# Apply accepted actions via correction gate (WS-SYNTHESIS-005)
# ---------------------------------------------------------------------------


class ApplyResponse(BaseModel):
    applied_count: int
    corrections: list[dict]
    skipped_count: int


@router.post("/{project_id}/synthesis/apply")
async def apply_accepted_actions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApplyResponse:
    """Apply all accepted mechanical actions as correction briefs.

    Reads the synthesis delta, finds accepted actions, converts each
    to a correction brief via synthesis_action_applier, and returns
    the correction briefs ready for rewind.

    Does NOT auto-rewind — the operator triggers rewind separately
    with the generated correction briefs.
    """
    from sqlalchemy import select, and_
    from app.domain.services.synthesis_action_applier import action_to_correction

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

    content = doc.content or {}
    decisions = content.get("_operator_decisions", {})
    actions = content.get("actions", [])

    corrections = []
    skipped = 0

    for action in actions:
        # Build finding ID to check decision
        finding_id = f"{action.get('action_type')}-{','.join(action.get('targets', []))}"
        decision = decisions.get(finding_id, {})

        if decision.get("decision") != "accept":
            skipped += 1
            continue

        try:
            brief = action_to_correction(action)
            corrections.append({
                "rewind_to_stage": brief.rewind_to_stage,
                "reason": brief.reason,
                "applies_to_stages": brief.applies_to_stages,
                "post_condition": brief.post_condition,
                "source_action_type": brief.source_action_type,
                "source_targets": brief.source_targets,
            })
        except ValueError as e:
            logger.warning("Skipping invalid action: %s", e)
            skipped += 1

    return ApplyResponse(
        applied_count=len(corrections),
        corrections=corrections,
        skipped_count=skipped,
    )

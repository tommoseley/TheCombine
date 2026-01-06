"""
BFF (Backend-for-Frontend) for Epic Backlog view.

Per ADR-030: BFF is the sole interface between UX and core.
Templates must only access vm.* (no ORM, no raw content JSON).

Note: This module imports _get_document_by_type from document_routes
as a transitional measure per WS-001. Future work should refactor
document retrieval to a core service.
"""

from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.web.viewmodels.epic_backlog_vm import (
    EpicBacklogVM,
    EpicBacklogSectionVM,
    EpicCardVM,
    EpicSetSummaryVM,
    RiskVM,
    OpenQuestionVM,
    DependencyVM,
    RelatedDiscoveryVM,
)



async def get_epic_backlog_vm(
    *,
    db: AsyncSession,
    project_id: UUID,
    project_name: str,
    base_url: str = "",
) -> EpicBacklogVM:
    """
    BFF assembler for Epic Backlog.
    
    Returns a presentation-safe ViewModel for Jinja templates.
    Templates must only access vm.* (no ORM, no raw content JSON).
    """
    # Transitional import per WS-001
    from app.web.routes.public.document_routes import _get_document_by_type
    
    doc = await _get_document_by_type(db, project_id, "epic_backlog")
    
    if not doc:
        return EpicBacklogVM(
            project_id=str(project_id),
            project_name=project_name,
            exists=False,
            message="Epic backlog has not been created yet.",
            sections=_empty_sections(),
        )
    
    content = doc.content or {}
    epics_raw = content.get("epics", [])
    
    # Classify and map epics
    mvp_cards: List[EpicCardVM] = []
    later_cards: List[EpicCardVM] = []
    
    for e in epics_raw:
        card = _map_epic_to_card_vm(e, project_id, base_url)
        

        if card.mvp_phase == "mvp":
            mvp_cards.append(card)
        else:
            later_cards.append(card)
    
    sections = [
        EpicBacklogSectionVM(
            id="mvp",
            title="MVP Epics",
            icon="rocket",
            empty_message="No MVP epics defined.",
            epics=mvp_cards,
        ),
        EpicBacklogSectionVM(
            id="later",
            title="Later Phase Epics",
            icon="calendar",
            empty_message="No later phase epics defined.",
            epics=later_cards,
        ),
    ]
    
    # Map summary
    summary_raw = content.get("epic_set_summary")
    epic_set_summary = None
    if summary_raw and isinstance(summary_raw, dict):
        epic_set_summary = EpicSetSummaryVM(
            overall_intent=summary_raw.get("overall_intent"),
            mvp_definition=summary_raw.get("mvp_definition"),
            key_constraints=summary_raw.get("key_constraints", []),
            out_of_scope=summary_raw.get("out_of_scope", []),
        )
    
    # Map risks
    risks_raw = content.get("risks_overview", [])
    risks = [
        RiskVM(
            description=r.get("description", ""),
            impact=r.get("impact", ""),
            affected_epics=r.get("affected_epics", []),
        )
        for r in risks_raw
        if isinstance(r, dict)
    ]
    

    return EpicBacklogVM(
        project_id=str(project_id),
        project_name=project_name,
        document_id=str(doc.id),
        subtitle=content.get("project_name"),
        last_updated_label=_format_dt(doc.updated_at),
        epic_set_summary=epic_set_summary,
        sections=sections,
        risks_overview=risks,
        recommendations_for_architecture=content.get("recommendations_for_architecture", []),
        exists=True,
    )


def _map_epic_to_card_vm(epic: dict, project_id: UUID, base_url: str) -> EpicCardVM:
    """Map raw epic dict to EpicCardVM."""
    epic_id = str(epic.get("epic_id", "") or epic.get("id", ""))
    
    # Classify MVP phase
    mvp_phase_raw = (epic.get("mvp_phase") or "").lower()
    if mvp_phase_raw == "mvp":
        mvp_phase = "mvp"
    else:
        mvp_phase = "later"
    
    # Map open questions (aligned with OpenQuestionV1 canonical schema)
    questions_raw = epic.get("open_questions", [])
    questions = [
        OpenQuestionVM(
            id=q.get("id", "") if isinstance(q, dict) else "",
            question=q.get("question", "") if isinstance(q, dict) else str(q),
            blocking=q.get("blocking_for_epic", False) or q.get("blocking", False) if isinstance(q, dict) else False,
            why_it_matters=q.get("why_it_matters", "") if isinstance(q, dict) else "",
            priority=q.get("priority") if isinstance(q, dict) else None,
            options=q.get("options", []) if isinstance(q, dict) else [],
            notes=q.get("notes") if isinstance(q, dict) else None,
            directed_to=q.get("directed_to") if isinstance(q, dict) else None,
        )
        for q in questions_raw
    ]
    
    # Map dependencies
    deps_raw = epic.get("dependencies", [])
    deps = [
        DependencyVM(
            depends_on_epic_id=d.get("depends_on_epic_id", "") if isinstance(d, dict) else str(d),
            reason=d.get("reason", "") if isinstance(d, dict) else "",
        )
        for d in deps_raw
    ]
    
    # Map related discovery items
    related_raw = epic.get("related_discovery_items")
    related = None
    if related_raw and isinstance(related_raw, dict):
        related = RelatedDiscoveryVM(
            risks=related_raw.get("risks", []),
            unknowns=related_raw.get("unknowns", []),
            early_decision_points=related_raw.get("early_decision_points", []),
        )
    
    return EpicCardVM(
        epic_id=epic_id,
        name=epic.get("name", "Untitled Epic"),
        intent=epic.get("intent", ""),
        mvp_phase=mvp_phase,
        business_value=epic.get("business_value"),
        in_scope=epic.get("in_scope", []),
        out_of_scope=epic.get("out_of_scope", []),
        primary_outcomes=epic.get("primary_outcomes", []),
        open_questions=questions,
        dependencies=deps,
        architecture_attention_points=epic.get("architecture_attention_points", []),
        related_discovery_items=related,
        detail_href=f"{base_url}/projects/{project_id}/epics/{epic_id}",
    )


def _empty_sections() -> List[EpicBacklogSectionVM]:
    """Return empty section structure for non-existent document."""
    return [
        EpicBacklogSectionVM(
            id="mvp",
            title="MVP Epics",
            icon="rocket",
            empty_message="No MVP epics defined.",
            epics=[],
        ),
        EpicBacklogSectionVM(
            id="later",
            title="Later Phase Epics",
            icon="calendar",
            empty_message="No later phase epics defined.",
            epics=[],
        ),
    ]


def _format_dt(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime for display."""
    if not dt:
        return None
    return dt.strftime("%b %d, %Y at %I:%M %p")
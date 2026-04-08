"""
Work Plan Assembly Service (ADR-071).

Assembles the final Work Plan artifact from:
- Work binder (version-pinned document references)
- Project documents (for executive summary composition)
- Synthesis delta (for decision log)
- WP dependency data (for dependency summary)

Mechanical composition only — no LLM involved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document

logger = logging.getLogger(__name__)


@dataclass
class WorkPlanContent:
    """Assembled Work Plan content ready for persistence."""

    project_id: str
    assembled_at: str
    document_count: int
    referenced_documents: list[dict[str, Any]]
    groups: list[dict[str, str]]
    executive_summary: dict[str, Any]
    decision_log: list[dict[str, Any]]
    dependency_summary: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "assembled_at": self.assembled_at,
            "document_count": self.document_count,
            "referenced_documents": self.referenced_documents,
            "groups": self.groups,
            "executive_summary": self.executive_summary,
            "decision_log": self.decision_log,
            "dependency_summary": self.dependency_summary,
        }


async def assemble_work_plan(
    db: AsyncSession,
    project_id: str,
) -> WorkPlanContent:
    """Assemble a Work Plan from project state.

    Mechanically composes:
    - Executive summary from PD/TA/WP/WS counts
    - Document references from binder (or fresh assembly)
    - Decision log from synthesis delta
    - Dependency summary from WP content
    """
    from app.domain.services.binder_assembly_service import assemble_binder

    # 1. Build binder references
    binder = await assemble_binder(db, project_id)

    # 2. Compose executive summary from project documents
    executive_summary = await _compose_executive_summary(db, project_id, binder)

    # 3. Build decision log from synthesis delta
    decision_log = await _build_decision_log(db, project_id)

    # 4. Build dependency summary from WP content
    dependency_summary = await _build_dependency_summary(db, project_id)

    return WorkPlanContent(
        project_id=project_id,
        assembled_at=datetime.now(timezone.utc).isoformat(),
        document_count=binder.document_count,
        referenced_documents=binder.referenced_documents,
        groups=binder.groups,
        executive_summary=executive_summary,
        decision_log=decision_log,
        dependency_summary=dependency_summary,
    )


async def _compose_executive_summary(
    db: AsyncSession,
    project_id: str,
    binder: Any,
) -> dict[str, Any]:
    """Compose executive summary from project documents. Mechanical only."""
    # Count documents by type
    refs = binder.referenced_documents
    wp_count = sum(1 for r in refs if r["doc_type_id"] == "work_package")
    ws_count = sum(1 for r in refs if r["doc_type_id"] == "work_statement")

    # Get PD for project name and objective
    project_name = project_id
    objective = ""
    scope_summary = ""
    key_constraints = []

    pd_stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.doc_type_id == "project_discovery",
            Document.is_latest == True,  # noqa: E712
        )
    ).limit(1)
    pd_result = await db.execute(pd_stmt)
    pd_doc = pd_result.scalar_one_or_none()

    if pd_doc and pd_doc.content:
        content = pd_doc.content
        project_name = content.get("project_name") or content.get("name") or project_id
        objective = content.get("objective") or content.get("vision") or ""
        scope_summary = content.get("scope_summary") or content.get("scope") or ""
        if isinstance(scope_summary, dict):
            scope_summary = scope_summary.get("summary") or str(scope_summary)
        constraints = content.get("constraints") or content.get("key_constraints") or []
        if isinstance(constraints, list):
            for c in constraints:
                if isinstance(c, str):
                    key_constraints.append(c)
                elif isinstance(c, dict):
                    key_constraints.append(c.get("constraint") or c.get("text") or str(c))

    # Get TA for component count
    component_count = 0
    ta_stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.doc_type_id == "technical_architecture",
            Document.is_latest == True,  # noqa: E712
        )
    ).limit(1)
    ta_result = await db.execute(ta_stmt)
    ta_doc = ta_result.scalar_one_or_none()

    if ta_doc and ta_doc.content:
        components = ta_doc.content.get("components") or []
        component_count = len(components)

    return {
        "project_name": project_name,
        "objective": objective,
        "component_count": component_count,
        "work_package_count": wp_count,
        "work_statement_count": ws_count,
        "key_constraints": key_constraints,
        "scope_summary": scope_summary,
    }


async def _build_decision_log(
    db: AsyncSession,
    project_id: str,
) -> list[dict[str, Any]]:
    """Build decision log from synthesis delta operator decisions."""
    stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.doc_type_id == "synthesis_delta",
            Document.is_latest == True,  # noqa: E712
        )
    ).limit(1)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc or not doc.content:
        return []

    content = doc.content
    decisions = content.get("_operator_decisions", {})
    actions = content.get("actions", [])
    questions = content.get("questions", [])

    log = []

    # Map actions to decisions
    for action in actions:
        finding_id = f"{action.get('action_type')}-{','.join(action.get('targets', []))}"
        decision = decisions.get(finding_id, {})
        if decision.get("decision"):
            log.append({
                "finding_id": finding_id,
                "severity": action.get("severity", "advisory"),
                "headline": action.get("headline", action.get("rationale", "")),
                "decision": decision["decision"],
                "note": decision.get("note"),
                "decided_at": decision.get("decided_at", ""),
                "finding_type": "action",
            })

    # Map questions to decisions
    for question in questions:
        finding_id = question.get("finding_id", "")
        decision = decisions.get(finding_id, {})
        if decision.get("decision"):
            log.append({
                "finding_id": finding_id,
                "severity": question.get("severity", "advisory"),
                "headline": question.get("headline", question.get("question", "")),
                "decision": decision["decision"],
                "note": decision.get("note"),
                "decided_at": decision.get("decided_at", ""),
                "finding_type": "question",
            })

    return log


async def _build_dependency_summary(
    db: AsyncSession,
    project_id: str,
) -> list[dict[str, Any]]:
    """Build dependency summary from WP dependency declarations."""
    stmt = select(Document).where(
        and_(
            Document.space_id == project_id,
            Document.doc_type_id == "work_package",
            Document.is_latest == True,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    wps = result.scalars().all()

    deps = []
    for wp in wps:
        if not wp.content:
            continue
        wp_deps = wp.content.get("dependencies") or []
        for dep in wp_deps:
            if isinstance(dep, dict):
                to_id = dep.get("wp_id") or dep.get("display_id") or ""
                deps.append({
                    "from_display_id": wp.display_id,
                    "from_title": wp.title or wp.display_id,
                    "to_display_id": to_id,
                    "to_title": dep.get("title") or to_id,
                    "dependency_type": dep.get("dependency_type") or "depends_on",
                })
            elif isinstance(dep, str):
                deps.append({
                    "from_display_id": wp.display_id,
                    "from_title": wp.title or wp.display_id,
                    "to_display_id": dep,
                    "to_title": dep,
                    "dependency_type": "depends_on",
                })

    return deps

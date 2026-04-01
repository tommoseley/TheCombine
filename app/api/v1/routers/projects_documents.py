"""Project documents sub-router.

Handles document retrieval, rendering, render-model, and PGC endpoints.
"""

import copy
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.document_type import DocumentType
from app.api.models.project import Project
from app.api.models.pgc_answer import PGCAnswer
from app.api.models.workflow_execution import WorkflowExecution
from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService
from app.core.database import get_db
from app.domain.services.render_model_builder import (
    RenderModelBuilder,
    DocDefNotFoundError,
)
from app.api.v1.routers.projects_common import (
    DISPLAY_ID_PATTERN,
    resolve_project,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["project-documents"])


# =============================================================================
# Private helpers
# =============================================================================

async def _resolve_view_docdef(
    db: AsyncSession,
    doc_type_id: str,
) -> tuple:
    """Resolve view_docdef and package config for a document type.

    Loads from combine-config (authoritative) with DB fallback.

    Returns:
        (view_docdef, doc_type, pkg_rendering, pkg_ia) tuple.
    """
    doc_type_result = await db.execute(
        select(DocumentType).where(DocumentType.doc_type_id == doc_type_id)
    )
    doc_type = doc_type_result.scalar_one_or_none()

    _package = None
    try:
        from app.config.package_loader import get_package_loader
        _package = get_package_loader().get_document_type(doc_type_id)
    except Exception:
        pass  # combine-config lookup is best-effort

    if _package:
        view_docdef = _package.view_docdef
    else:
        view_docdef = doc_type.view_docdef if doc_type else None

    pkg_rendering = _package.rendering if _package else None
    pkg_ia = _package.information_architecture if _package else None
    return view_docdef, doc_type, pkg_rendering, pkg_ia


async def _find_execution_id(
    db: AsyncSession,
    project_id,
    doc_type_id: str,
    document_id: str,
    workflow_id: str,
) -> Optional[int]:
    """Query execution_id for document metadata from DB.

    Tries three query strategies in order:
    1. Completed execution matching project + workflow_id
    2. Any execution matching project + workflow_id
    3. Execution matching document_id

    Returns the first matching execution_id or None.
    """
    for query in [
        select(WorkflowExecution.execution_id)
        .where(WorkflowExecution.project_id == project_id)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .where(WorkflowExecution.status == "completed")
        .order_by(WorkflowExecution.execution_id.desc())
        .limit(1),
        select(WorkflowExecution.execution_id)
        .where(WorkflowExecution.project_id == project_id)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .order_by(WorkflowExecution.execution_id.desc())
        .limit(1),
        select(WorkflowExecution.execution_id)
        .where(WorkflowExecution.document_id == document_id)
        .order_by(WorkflowExecution.execution_id.desc())
        .limit(1),
    ]:
        result = await db.execute(query)
        exec_id = result.scalar_one_or_none()
        if exec_id:
            return exec_id
    return None


def _render_ontology_summary(binder_docs: List[Dict[str, Any]]) -> str | None:
    """Run ontology evaluator against binder docs and render a summary section.

    Loads all ontology YAML files from combine-config/ontologies/.
    If no ontology is declared, returns None (skip with notice).

    Returns:
        Markdown section string, or None if no ontology files exist.
    """
    import pathlib
    import yaml
    from app.domain.services.ontology_evaluator import evaluate_ontology

    ontology_dir = pathlib.Path("combine-config/ontologies")
    if not ontology_dir.exists():
        return None

    yaml_files = sorted(ontology_dir.glob("*.yaml"))
    if not yaml_files:
        return None

    sections: list[str] = []
    sections.append("---")
    sections.append("")
    sections.append("## Ontology Evaluation (ADR-059)")
    sections.append("")

    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            ontology_config = yaml.safe_load(f) or {}

        report = evaluate_ontology(ontology_config, binder_docs)

        if report.skipped:
            sections.append(f"**{yaml_file.stem}**: {report.skip_reason}")
            continue

        if not report.findings:
            sections.append(
                f"**{report.project_id} (v{report.ontology_version})**: "
                f"ontology clean — {report.artifact_count} artifacts checked, "
                f"0 cross-layer leakage findings"
            )
        else:
            sections.append(
                f"**{report.project_id} (v{report.ontology_version})**: "
                f"ontology leakage findings: {len(report.findings)}"
            )
            sections.append("")
            sections.append("| Artifact | Field | Term | Expected Layer | Actual Layer |")
            sections.append("| --- | --- | --- | --- | --- |")
            for f in report.findings:
                sections.append(
                    f"| {f.artifact_id} | {f.field_path} | `{f.offending_term}` "
                    f"| {f.expected_layer} | {f.actual_layer} |"
                )

    return "\n".join(sections)


def _render_overlap_summary(binder_docs: List[Dict[str, Any]]) -> str | None:
    """Run WP boundary overlap evaluator and render a summary section.

    Returns:
        Markdown section string, or None if fewer than 2 WPs exist.
    """
    from app.domain.services.wp_overlap_evaluator import evaluate_wp_overlap

    wp_docs = [d for d in binder_docs if d.get("doc_type_id") == "work_package"]
    ws_docs = [d for d in binder_docs if d.get("doc_type_id") == "work_statement"]

    if len(wp_docs) < 2:
        return None

    report = evaluate_wp_overlap(wp_docs, ws_docs)

    sections: list[str] = []
    sections.append("---")
    sections.append("")
    sections.append("## WP Boundary Overlap Evaluation")
    sections.append("")

    if not report.findings:
        sections.append(
            f"**Boundaries clean** — {report.wp_count} WPs checked, "
            f"0 overlap findings"
        )
    else:
        sections.append(
            f"**Overlap findings: {len(report.findings)}** "
            f"({report.wp_count} WPs checked)"
        )
        sections.append("")
        sections.append("| Rule | WPs | Type | Evidence |")
        sections.append("| --- | --- | --- | --- |")
        for f in report.findings:
            sections.append(
                f"| {f.rule_id} | {', '.join(f.wp_ids)} "
                f"| {f.overlap_type} | {f.evidence} |"
            )

    return "\n".join(sections)


def _render_contradiction_summary(binder_docs: List[Dict[str, Any]]) -> str | None:
    """Run cross-layer contradiction evaluator and render a summary section.

    Finds the TA document, compares WS content against TA authority surfaces.

    Returns:
        Markdown section string, or None if no TA exists.
    """
    from app.domain.services.cross_layer_evaluator import evaluate_cross_layer

    ta_docs = [d for d in binder_docs if d.get("doc_type_id") == "technical_architecture"]
    ws_docs = [d for d in binder_docs if d.get("doc_type_id") == "work_statement"]

    if not ta_docs:
        return None

    ta_doc = ta_docs[0]  # Use first TA
    report = evaluate_cross_layer(ta_doc, ws_docs)

    sections: list[str] = []
    sections.append("---")
    sections.append("")
    sections.append("## Cross-Layer Contradiction Evaluation (ADR-061)")
    sections.append("")

    if not report.findings:
        sections.append(
            f"**No contradictions detected** — {report.artifacts_checked} WSs "
            f"checked against TA authority surfaces"
        )
    else:
        sections.append(
            f"**Contradiction findings: {len(report.findings)}** "
            f"({report.artifacts_checked} WSs checked)"
        )
        sections.append("")
        sections.append("| Rule | WS | Type | TA Authority | WS Claim |")
        sections.append("| --- | --- | --- | --- | --- |")
        for f in report.findings:
            sections.append(
                f"| {f.rule_id} | {f.artifact_id} | {f.contradiction_type} "
                f"| {f.ta_authority} | {f.ws_claim} |"
            )

    return "\n".join(sections)


def _render_duplicate_summary(binder_docs: List[Dict[str, Any]]) -> str | None:
    """Run WS duplicate objective evaluator and render a summary section.

    Returns:
        Markdown section string, or None if fewer than 2 WSs exist.
    """
    from app.domain.services.ws_duplicate_evaluator import evaluate_ws_duplicates

    ws_docs = [d for d in binder_docs if d.get("doc_type_id") == "work_statement"]

    if len(ws_docs) < 2:
        return None

    report = evaluate_ws_duplicates(ws_docs)

    sections: list[str] = []
    sections.append("---")
    sections.append("")
    sections.append("## Duplicate WS Objective Detection (ADR-062)")
    sections.append("")

    if not report.findings:
        sections.append(
            f"**No duplicates detected** — {report.ws_count} WSs checked"
        )
    else:
        sections.append(
            f"**Potential duplicates: {len(report.findings)}** "
            f"({report.ws_count} WSs checked)"
        )
        sections.append("")
        sections.append("| Rule | Work Statements | WPs | Type | Evidence |")
        sections.append("| --- | --- | --- | --- | --- |")
        for f in report.findings:
            sections.append(
                f"| {f.rule_id} | {', '.join(f.ws_ids)} "
                f"| {', '.join(f.parent_wp_ids)} "
                f"| {f.duplicate_type} | {f.evidence[:100]} |"
            )

    return "\n".join(sections)


def _load_governance_policies() -> List[Dict[str, str]]:
    """Read policy files from combine-config/policies/ and return as data.

    Each policy dict has 'title' (parsed from first # heading) and 'content'.
    Returns empty list if directory doesn't exist or has no .md files.
    """
    from pathlib import Path

    policies_dir = Path("combine-config/policies")
    if not policies_dir.is_dir():
        return []

    result = []
    for path in sorted(policies_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # Parse title from first # heading
        title = path.stem
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                title = stripped[2:].strip()
                break
        result.append({"title": title, "content": text})
    return result


def _prepare_document_content(doc_type_id: str, raw_content: Any) -> tuple:
    """Unwrap, transform, and snapshot document content for rendering.

    Returns:
        (document_data, ia_raw_content) tuple. document_data may be
        mutated by handler transforms; ia_raw_content is a deep copy
        preserving schema-canonical field names for IA rendering.
    """
    from app.api.v1.services.render_pure import unwrap_raw_envelope

    document_data = unwrap_raw_envelope(raw_content)
    unwrap_failed = (
        document_data is raw_content
        and isinstance(document_data, dict)
        and document_data.get("raw")
    )
    if unwrap_failed:
        logger.warning(f"Failed to parse raw content JSON for {doc_type_id}")

    # Apply handler transform at render time (computed fields like associated_risks)
    if isinstance(document_data, dict):
        try:
            from app.domain.handlers.registry import handler_exists, get_handler
            if handler_exists(doc_type_id):
                _handler = get_handler(doc_type_id)
                document_data = _handler.transform(document_data)
        except Exception:
            pass  # Handler transform is best-effort at render time

    # Snapshot for IA-driven rendering (schema-canonical names)
    ia_raw_content = copy.deepcopy(document_data) if isinstance(document_data, dict) else document_data

    return document_data, ia_raw_content


def _repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to repair truncated JSON from LLM output."""
    from app.api.v1.services.render_pure import repair_truncated_json
    return repair_truncated_json(text)


def _build_pgc_from_answers_table(pgc_answer: PGCAnswer) -> List[Dict[str, Any]]:
    """Build clarifications from pgc_answers table (newer format)."""
    from app.api.v1.services.pgc_pure import build_pgc_from_answers
    return build_pgc_from_answers(pgc_answer.questions or [], pgc_answer.answers or {})


def _build_pgc_from_context_state(context_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build clarifications from workflow execution context_state (older format)."""
    from app.api.v1.services.pgc_pure import build_pgc_from_context_state
    return build_pgc_from_context_state(context_state)


def _resolve_answer_label(question: Dict[str, Any], user_answer: Any) -> Optional[str]:
    """Resolve human-readable answer label from question choices."""
    from app.api.v1.services.pgc_pure import resolve_answer_label
    return resolve_answer_label(question, user_answer)


# =============================================================================
# Document Endpoints
# =============================================================================

@router.get("/{project_id}/documents/{identifier}")
async def get_project_document(
    project_id: str,
    identifier: str,
    instance_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get document content for a project.

    Accepts either a doc_type_id (e.g., 'project_discovery') or a display_id
    (e.g., 'PD-001') per ADR-055. Display_id format is detected automatically.

    Returns the full document content as JSON for the SPA viewer.
    When instance_id is provided, filters to that specific instance
    (needed for multi-instance doc types like epics).
    """
    # Resolve project (supports both UUID and project_id)
    project = await resolve_project(project_id, db)

    # ADR-055: Detect display_id format vs doc_type_id
    if DISPLAY_ID_PATTERN.match(identifier):
        # Display ID path: resolve prefix -> doc_type_id, then query by display_id
        from app.domain.services.display_id_service import resolve_display_id
        try:
            doc_type_id = await resolve_display_id(db, identifier)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        result = await db.execute(
            select(Document).where(
                Document.space_id == project.id,
                Document.doc_type_id == doc_type_id,
                Document.display_id == identifier,
                Document.is_latest == True,
            )
        )
        document = result.scalars().first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {identifier} in project {project_id}",
            )
    else:
        # Traditional doc_type_id path
        doc_type_id = identifier
        query = (
            select(Document)
            .where(Document.space_type == "project")
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == doc_type_id)
            .where(Document.is_latest == True)
        )
        if instance_id:
            query = query.where(Document.instance_id == instance_id)
        doc_result = await db.execute(query)
        document = doc_result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{doc_type_id}' not found for project",
            )

    return {
        "id": str(document.id),
        "display_id": getattr(document, 'display_id', None),
        "doc_type_id": document.doc_type_id,
        "title": document.title,
        "content": document.content,
        "summary": document.summary,
        "version": document.version,
        "status": document.status,
        "lifecycle_state": document.lifecycle_state if document.lifecycle_state else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "accepted_at": document.accepted_at.isoformat() if document.accepted_at else None,
        "accepted_by": document.accepted_by,
    }


@router.get("/{project_id}/documents/{display_id}/render")
async def render_document_markdown(
    project_id: str,
    display_id: str,
    format: str = Query("md", description="Output format (only 'md' supported)"),
    profile: str = Query("standard", description="Render profile: standard | print"),
    mode: str = Query("standard", description="Render mode: standard | evidence"),
    db: AsyncSession = Depends(get_db),
):
    """Render a document to Markdown using its IA definitions (WS-RENDER-001/004).

    Resolves the document by display_id, loads IA from package.yaml,
    and renders to Markdown using the block renderer.

    When mode=evidence, prepends YAML frontmatter with provenance data.

    Returns the rendered Markdown as a downloadable attachment.
    """
    # Validate params
    if format != "md":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Only 'md' is supported.",
        )
    if mode not in ("standard", "evidence"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mode '{mode}'. Use 'standard' or 'evidence'.",
        )

    # Resolve project
    project = await resolve_project(project_id, db)

    # Resolve document by display_id
    if not DISPLAY_ID_PATTERN.match(display_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid display_id format: {display_id}. Expected format like PD-001.",
        )

    from app.domain.services.display_id_service import resolve_display_id
    try:
        doc_type_id = await resolve_display_id(db, display_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = await db.execute(
        select(Document).where(
            Document.space_id == project.id,
            Document.doc_type_id == doc_type_id,
            Document.display_id == display_id,
            Document.is_latest == True,
        )
    )
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {display_id} in project {project_id}",
        )

    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {display_id} has no content",
        )

    # Load IA definitions from package.yaml
    ia = None
    try:
        from app.config.package_loader import get_package_loader
        package = get_package_loader().get_document_type(doc_type_id)
        ia = package.information_architecture
    except Exception:
        pass

    # Unwrap document content
    from app.api.v1.services.render_pure import unwrap_raw_envelope
    content = unwrap_raw_envelope(document.content)

    # Apply handler transform (computed fields)
    if isinstance(content, dict):
        try:
            from app.domain.handlers.registry import handler_exists, get_handler
            if handler_exists(doc_type_id):
                content = get_handler(doc_type_id).transform(content)
        except Exception:
            pass

    # IA gate (WS-RENDER-003): verify content before rendering
    from app.domain.services.ia_gate import verify_document_ia
    ia_result = verify_document_ia(content, ia)
    if ia_result["status"] == "FAIL":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": "ia_violation",
                "message": f"Rendering blocked: IA verification failed for {display_id}.",
                "failures": [
                    {"display_id": display_id, "summary": f}
                    for f in ia_result["failures"]
                ],
            },
        )

    # Render to Markdown
    from app.domain.services.markdown_renderer import render_document_to_markdown

    if ia:
        markdown = render_document_to_markdown(content, ia)
    else:
        # Fallback: render raw content as key-value dump
        parts = []
        if isinstance(content, dict):
            for key, value in content.items():
                parts.append(f"## {key.replace('_', ' ').title()}\n\n{value}")
        markdown = "\n\n".join(parts) + "\n" if parts else "No content.\n"

    # Evidence mode (WS-RENDER-004): prepend YAML frontmatter
    if mode == "evidence":
        from app.domain.services.evidence_renderer import render_evidence_header
        evidence_header = render_evidence_header(
            project_id=project.project_id,
            display_id=display_id,
            doc_type_id=doc_type_id,
            content=content,
            document_version=getattr(document, "version", None),
            ia_status=ia_result["status"] if ia_result["status"] != "SKIP" else None,
        )
        markdown = evidence_header + "\n" + markdown

    # Build filename
    suffix = "-evidence" if mode == "evidence" else ""
    filename = f"{project.project_id}-{display_id}{suffix}.md"

    from fastapi.responses import Response
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{project_id}/render")
async def render_project_binder(
    project_id: str,
    scope: str = Query(..., description="Render scope (only 'project' supported)"),
    format: str = Query("md", description="Output format (only 'md' supported)"),
    profile: str = Query("print", description="Render profile: standard | print"),
    mode: str = Query("standard", description="Render mode: standard | evidence"),
    governance: str = Query("native", description="Governance mode: native | portable (ADR-060)"),
    db: AsyncSession = Depends(get_db),
):
    """Render all project documents as a single Markdown binder (WS-RENDER-002/004).

    Assembles cover, TOC, and all documents in deterministic pipeline order.
    WPs are ordered by display_id; WSs within WPs follow ws_index order.

    When mode=evidence, includes per-document YAML frontmatter and Evidence Index.
    When governance=portable, policies are rendered as declarative constraints
    without references to Combine-internal infrastructure (ADR-060).

    Returns the rendered Markdown as a downloadable attachment.
    """
    # Validate params
    if scope != "project":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported scope '{scope}'. Only 'project' is supported.",
        )
    if format != "md":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Only 'md' is supported.",
        )
    if mode not in ("standard", "evidence"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mode '{mode}'. Use 'standard' or 'evidence'.",
        )

    # Resolve project
    project = await resolve_project(project_id, db)

    # Query all latest documents for this project
    result = await db.execute(
        select(Document).where(
            Document.space_type == "project",
            Document.space_id == project.id,
            Document.is_latest == True,
        )
    )
    all_docs = result.scalars().all()

    # Build document dicts for the binder renderer
    from app.config.package_loader import get_package_loader
    from app.api.v1.services.render_pure import unwrap_raw_envelope

    loader = None
    try:
        loader = get_package_loader()
    except Exception:
        pass

    binder_docs = []
    for doc in all_docs:
        content = unwrap_raw_envelope(doc.content) if doc.content else {}

        # Apply handler transform (computed fields)
        if isinstance(content, dict):
            try:
                from app.domain.handlers.registry import handler_exists, get_handler
                if handler_exists(doc.doc_type_id):
                    content = get_handler(doc.doc_type_id).transform(content)
            except Exception:
                pass

        # Load IA
        ia = None
        if loader:
            try:
                pkg = loader.get_document_type(doc.doc_type_id)
                ia = pkg.information_architecture
            except Exception:
                pass

        entry = {
            "display_id": getattr(doc, "display_id", None) or doc.doc_type_id,
            "doc_type_id": doc.doc_type_id,
            "title": doc.title or doc.doc_type_id,
            "content": content,
            "ia": ia,
            "id": str(doc.id) if doc.id else None,
            "parent_document_id": str(doc.parent_document_id) if doc.parent_document_id else None,
        }

        # For WPs, include ws_index from content
        if doc.doc_type_id == "work_package" and isinstance(content, dict):
            entry["ws_index"] = content.get("ws_index", [])

        binder_docs.append(entry)

    # IA gate (WS-RENDER-003): verify all documents before rendering binder
    from app.domain.services.ia_gate import verify_document_ia
    ia_failures = []
    for entry in binder_docs:
        ia_result = verify_document_ia(entry.get("content", {}), entry.get("ia"))
        if ia_result["status"] == "FAIL":
            ia_failures.append({
                "display_id": entry.get("display_id", ""),
                "summary": "; ".join(ia_result["failures"]),
            })

    if ia_failures:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": "ia_violation",
                "message": f"Binder rendering blocked: IA verification failed for {len(ia_failures)} document(s).",
                "failures": ia_failures,
            },
        )

    # Load governance policies from combine-config/policies/
    policy_list = _load_governance_policies()

    # Portable mode (ADR-060): convert policies to declarative constraints
    is_portable = governance.lower() == "portable"
    if is_portable:
        from app.domain.services.governance_portable import convert_policies_to_portable
        policy_list = convert_policies_to_portable(policy_list)

    # Render binder
    from app.domain.services.binder_renderer import render_project_binder as _render_binder

    markdown = _render_binder(
        project_id=project.project_id,
        project_title=project.name or project.project_id,
        documents=binder_docs,
        policies=policy_list,
        governance_mode="portable" if is_portable else "native",
    )

    # Evidence mode (WS-RENDER-004): add per-document frontmatter + Evidence Index
    if mode == "evidence":
        from app.domain.services.evidence_renderer import (
            compute_source_hash, render_evidence_index,
        )
        # Build evidence index data
        evidence_entries = []
        for entry in binder_docs:
            ia_check = verify_document_ia(entry.get("content", {}), entry.get("ia"))
            evidence_entries.append({
                "display_id": entry.get("display_id", ""),
                "title": entry.get("title", ""),
                "version": "",  # version not available in binder doc dict
                "ia_status": ia_check["status"],
                "source_hash": compute_source_hash(entry.get("content", {})),
            })

        # Insert Evidence Index after cover + TOC
        evidence_index = render_evidence_index(evidence_entries)
        # Find the first "---" separator (after TOC) and insert evidence index
        parts = markdown.split("\n---\n", 1)
        if len(parts) == 2:
            markdown = parts[0] + "\n\n" + evidence_index + "\n\n---\n" + parts[1]
        else:
            markdown = evidence_index + "\n\n" + markdown

    # Ontology evaluation (ADR-059): append summary if ontology is declared
    ontology_section = _render_ontology_summary(binder_docs)
    if ontology_section:
        markdown += "\n\n" + ontology_section

    # WP boundary overlap evaluation: append summary
    overlap_section = _render_overlap_summary(binder_docs)
    if overlap_section:
        markdown += "\n\n" + overlap_section

    # Cross-layer contradiction evaluation (ADR-061): append summary
    contradiction_section = _render_contradiction_summary(binder_docs)
    if contradiction_section:
        markdown += "\n\n" + contradiction_section

    # Duplicate WS objective detection (ADR-062): append summary
    duplicate_section = _render_duplicate_summary(binder_docs)
    if duplicate_section:
        markdown += "\n\n" + duplicate_section

    suffix = "-evidence" if mode == "evidence" else ""
    filename = f"{project.project_id}-binder{suffix}.md"

    from fastapi.responses import Response
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{project_id}/documents/{doc_type_id}/render-model")
async def get_document_render_model(
    project_id: str,
    doc_type_id: str,
    instance_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get RenderModel for a document.

    Returns the data-driven RenderModel structure that can be used
    by any frontend (React, HTMX, etc.) to render the document.

    The RenderModel includes:
    - sections: Ordered list of sections with blocks
    - metadata: Document metadata and schema info
    - title/subtitle: Display information

    When instance_id is provided, filters to that specific instance
    (needed for multi-instance doc types like epics).
    """
    from app.api.v1.services.render_pure import (
        build_document_metadata_dict,
        build_fallback_render_model,
        build_spawned_children,
        inject_ia_config,
        normalize_document_keys,
        resolve_display_title,
    )

    # Get project
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )

    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Get the document
    doc_query = (
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == doc_type_id)
        .where(Document.is_latest == True)
    )
    if instance_id:
        doc_query = doc_query.where(Document.instance_id == instance_id)
    doc_result = await db.execute(doc_query)
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_type_id}' not found for project",
        )

    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_type_id}' has no content",
        )

    # Resolve view_docdef and package config
    view_docdef, doc_type, _pkg_rendering, _pkg_ia = await _resolve_view_docdef(
        db, doc_type_id,
    )

    # Prepare document content (unwrap, transform, snapshot)
    document_data, ia_raw_content = _prepare_document_content(
        doc_type_id, document.content,
    )

    # Build document metadata
    exec_id = await _find_execution_id(
        db, project.id, doc_type_id, str(document.id), doc_type_id,
    )
    doc_meta = build_document_metadata_dict(
        doc_type_id=doc_type_id,
        doc_type_name=doc_type.name if doc_type else None,
        display_id=getattr(document, 'display_id', None),
        version=document.version,
        lifecycle_state=document.lifecycle_state,
        created_at=document.created_at,
        updated_at=document.updated_at,
        created_by=document.created_by,
        execution_id=exec_id,
    )

    if not view_docdef:
        doc_meta["fallback"] = True
        doc_meta["reason"] = "no_view_docdef"
        result = build_fallback_render_model(
            document_id=str(document.id),
            doc_type_id=doc_type_id,
            title=document.title or doc_type_id,
            metadata=doc_meta,
            raw_content=ia_raw_content,
        )
        inject_ia_config(result, _pkg_rendering, _pkg_ia)
        return result

    # Normalize LLM output keys to match docdef source pointers
    if isinstance(document_data, dict):
        normalize_document_keys(document_data)

    display_title = resolve_display_title(document.title, document_data)

    # Build the RenderModel
    try:
        builder = RenderModelBuilder(
            docdef_service=DocumentDefinitionService(db),
            component_service=ComponentRegistryService(db),
            schema_service=SchemaRegistryService(db),
        )

        render_model = await builder.build(
            document_def_id=view_docdef,
            document_data=document_data,
            document_id=str(document.id),
            title=display_title,
            lifecycle_state=document.lifecycle_state,
        )

        result_dict = render_model.to_dict()
        result_dict["raw_content"] = ia_raw_content
        inject_ia_config(result_dict, _pkg_rendering, _pkg_ia)

        meta = result_dict.setdefault("metadata", {})
        meta.update(doc_meta)

        # Query spawned child documents for this document
        child_result = await db.execute(
            select(Document)
            .where(Document.parent_document_id == document.id)
            .where(Document.is_latest == True)
        )
        child_docs = child_result.scalars().all()
        if child_docs:
            meta["spawned_children"] = build_spawned_children(child_docs)

        return result_dict

    except DocDefNotFoundError as e:
        logger.debug(f"DocDef not in DB for {doc_type_id} (using IA config fallback): {e}")
        doc_meta["fallback"] = True
        doc_meta["reason"] = "docdef_not_found"
        doc_meta["view_docdef"] = view_docdef
        result = build_fallback_render_model(
            document_id=str(document.id),
            doc_type_id=doc_type_id,
            title=display_title or doc_type_id,
            metadata=doc_meta,
            raw_content=ia_raw_content,
        )
        inject_ia_config(result, _pkg_rendering, _pkg_ia)
        return result
    except Exception as e:
        logger.error(f"Failed to build RenderModel for {doc_type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build render model: {str(e)}",
        )


@router.get("/{project_id}/documents/{doc_type_id}/pgc")
async def get_document_pgc_context(
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get PGC (Pre-Generation Clarification) context for a document.

    Returns the PGC questions (with why_it_matters rationale) and the
    operator's answers. Checks two sources:
    1. pgc_answers table (newer executions)
    2. workflow_executions.context_state (older executions)
    """
    project = await resolve_project(project_id, db)

    # Source 1: pgc_answers table (newer format)
    result = await db.execute(
        select(PGCAnswer)
        .where(PGCAnswer.project_id == project.id)
        .where(PGCAnswer.workflow_id == doc_type_id)
        .order_by(PGCAnswer.created_at.desc())
        .limit(1)
    )
    pgc_answer = result.scalar_one_or_none()

    if pgc_answer:
        clarifications = _build_pgc_from_answers_table(pgc_answer)
        return {
            "clarifications": clarifications,
            "has_pgc": True,
            "execution_id": pgc_answer.execution_id,
            "created_at": pgc_answer.created_at.isoformat() if pgc_answer.created_at else None,
        }

    # Source 2: workflow_executions context_state (older format)
    we_result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.project_id == project.id)
        .where(WorkflowExecution.document_type == doc_type_id)
        .where(WorkflowExecution.status == "completed")
        .order_by(WorkflowExecution.execution_id.desc())
        .limit(1)
    )
    execution = we_result.scalar_one_or_none()

    if execution and execution.context_state:
        clarifications = _build_pgc_from_context_state(execution.context_state)
        if clarifications:
            return {
                "clarifications": clarifications,
                "has_pgc": True,
                "execution_id": execution.execution_id,
                "created_at": None,
            }

    return {"clarifications": [], "has_pgc": False}

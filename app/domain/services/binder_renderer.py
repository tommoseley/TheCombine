"""
Project binder renderer (WS-RENDER-002).

Assembles all project documents into a single Markdown file with:
- Cover block (project identity, generation metadata)
- Table of Contents with anchor links
- Documents rendered in deterministic pipeline order
- WS documents nested under their parent WPs

Pure function — no DB, no side effects, deterministic output.
Reuses the single-document renderer from WS-RENDER-001.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.services.markdown_renderer import render_document_to_markdown


# Pipeline order for document types (deterministic)
_PIPELINE_ORDER = [
    "concierge_intake",
    "project_discovery",
    "implementation_plan",
    "technical_architecture",
    "work_package",
]

_RENDERER_VERSION = "render-md@1.0.0"


def render_project_binder(
    project_id: str,
    project_title: str,
    documents: List[Dict[str, Any]],
    policies: Optional[List[Dict[str, str]]] = None,
    generated_at: Optional[str] = None,
) -> str:
    """
    Render a project binder to Markdown.

    Args:
        project_id: Project identifier (e.g., "HWCA-001").
        project_title: Human-readable project name.
        documents: List of document dicts. Each must have:
            - display_id: str (e.g., "PD-001")
            - doc_type_id: str (e.g., "project_discovery")
            - title: str
            - content: dict (canonical JSON body)
            - ia: dict or None (IA definitions from package.yaml)
            - ws_index: list or None (for WP documents only)
            - id: str or None (database primary key, for parent_document_id fallback)
            - parent_document_id: str or None (for WS documents, points to parent WP id)
        policies: Optional list of policy dicts for the governance section.
            Each dict: {"title": "POL-XXX — Name", "content": "markdown body"}.
            If None or empty, governance section is omitted.
        generated_at: ISO 8601 timestamp (for deterministic output).
            If None, uses current time.

    Returns:
        Markdown string for the complete binder.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    # Sort policies alphabetically by title
    sorted_policies = sorted(policies, key=lambda p: p.get("title", "")) if policies else []

    # Separate documents by type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    ws_docs: List[Dict[str, Any]] = []

    for doc in documents:
        dtype = doc.get("doc_type_id", "")
        if dtype == "work_statement":
            ws_docs.append(doc)
        else:
            by_type.setdefault(dtype, []).append(doc)

    # Sort each type group by display_id ascending
    for dtype in by_type:
        by_type[dtype].sort(key=lambda d: d.get("display_id", ""))

    # Build ordered list of (doc, children) tuples
    ordered: List[Dict[str, Any]] = []
    for dtype in _PIPELINE_ORDER:
        if dtype not in by_type:
            continue
        for doc in by_type[dtype]:
            ordered.append(doc)
            # For WPs, attach child WSs in ws_index order
            if dtype == "work_package":
                children = _get_ordered_ws(doc, ws_docs)
                for child in children:
                    ordered.append(child)

    # Cover block
    parts: List[str] = []
    parts.append(_render_cover(project_id, project_title, generated_at, len(ordered)))

    if not ordered:
        parts.append("*No documents produced yet.*")
        return "\n\n".join(parts) + "\n"

    # Table of Contents (governance + pipeline)
    parts.append(_render_toc(ordered, sorted_policies))

    # Governance section (before pipeline documents)
    if sorted_policies:
        parts.append(_render_governance_section(sorted_policies))

    # Document sections
    for doc in ordered:
        parts.append("---")
        parts.append(_render_document_section(doc))

    return "\n\n".join(parts) + "\n"


def _render_cover(
    project_id: str,
    project_title: str,
    generated_at: str,
    document_count: int,
) -> str:
    """Render the binder cover block."""
    lines = [
        f"# {project_id} — {project_title}",
        "",
        f"> Generated: {generated_at}",
        f"> Renderer: {_RENDERER_VERSION}",
        f"> Documents: {document_count}",
    ]
    return "\n".join(lines)


def _render_toc(
    documents: List[Dict[str, Any]],
    policies: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Render a Table of Contents with anchor links."""
    lines = ["## Table of Contents", ""]

    # Governance TOC group
    if policies:
        lines.append("### Project Governance")
        for pol in policies:
            title = pol.get("title", "")
            # Extract policy ID (first word) for anchor
            pol_id = title.split()[0] if title else ""
            anchor = _make_anchor(pol_id)
            lines.append(f"  - [{title}](#{anchor})")
        lines.append("")
        lines.append("### Pipeline Documents")

    for doc in documents:
        display_id = doc.get("display_id", "")
        title = doc.get("title", "")
        anchor = _make_anchor(display_id)
        dtype = doc.get("doc_type_id", "")

        if dtype == "work_statement":
            # Indent WSs under their parent WP
            lines.append(f"  - [{display_id} — {title}](#{anchor})")
        else:
            lines.append(f"- [{display_id} — {title}](#{anchor})")

    return "\n".join(lines)


def _render_governance_section(policies: List[Dict[str, str]]) -> str:
    """Render the Project Governance section with all policy documents."""
    parts = [
        "---",
        "",
        "# Project Governance",
        "",
        "These standards apply to all work in this project.",
    ]
    for pol in policies:
        title = pol.get("title", "")
        content = pol.get("content", "")
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(f"## {title}")
        parts.append("")
        parts.append(content)

    return "\n".join(parts)


def _render_document_section(doc: Dict[str, Any]) -> str:
    """Render a single document section with header and content."""
    display_id = doc.get("display_id", "")
    title = doc.get("title", "")
    content = doc.get("content", {})
    ia = doc.get("ia")
    dtype = doc.get("doc_type_id", "")

    # WS documents get ### headers (nested under WP)
    if dtype == "work_statement":
        header = f"### {display_id} — {title}"
    else:
        header = f"# {display_id} — {title}"

    # Render content using IA if available
    if ia and isinstance(content, dict):
        body = render_document_to_markdown(content, ia)
    elif isinstance(content, dict):
        # Fallback: key-value dump
        body_parts = []
        for key, value in content.items():
            body_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        body = "\n\n".join(body_parts) + "\n" if body_parts else ""
    else:
        body = str(content) if content else ""

    return f"{header}\n\n{body}" if body.strip() else header


def _get_ordered_ws(
    wp_doc: Dict[str, Any],
    ws_docs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Get WS documents for a WP, ordered by ws_index.

    Primary path: match WS docs by content.ws_id against ws_index[].ws_id.
    Fallback: if ws_index matching produces no results but WS docs exist
    with parent_document_id matching the WP's id, use those ordered by
    display_id.
    """
    ws_index = wp_doc.get("ws_index", [])

    # Build lookup: ws_id → WS doc
    ws_by_id: Dict[str, Dict[str, Any]] = {}
    for ws in ws_docs:
        ws_id = ws.get("content", {}).get("ws_id", "")
        if ws_id:
            ws_by_id[ws_id] = ws

    # Primary path: return WSs in ws_index order
    if ws_index:
        ordered = []
        for entry in ws_index:
            ws_id = entry.get("ws_id", "")
            if ws_id in ws_by_id:
                ordered.append(ws_by_id[ws_id])
        if ordered:
            return ordered

    # Fallback: match by parent_document_id
    wp_id = wp_doc.get("id")
    if wp_id is not None:
        children = [
            ws for ws in ws_docs
            if ws.get("parent_document_id") == wp_id
        ]
        if children:
            children.sort(key=lambda d: d.get("display_id", ""))
            return children

    return []


def _make_anchor(display_id: str) -> str:
    """Convert a display_id to a valid markdown anchor."""
    return re.sub(r'[^a-z0-9-]', '', display_id.lower())

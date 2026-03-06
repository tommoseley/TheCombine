"""
Evidence renderer for audit-grade exports (WS-RENDER-004).

Generates YAML frontmatter evidence headers with provenance,
source hashes, IA verification status, and document lineage.
Also produces Evidence Index tables for project binders.

Pure function — no DB, no side effects, deterministic output.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_RENDERER_VERSION = "render-md@1.0.0"


def compute_source_hash(content: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of canonical JSON content.

    Uses sorted keys and no whitespace for deterministic output.
    """
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def render_evidence_header(
    project_id: str,
    display_id: str,
    doc_type_id: str,
    content: Dict[str, Any],
    document_version: Optional[int] = None,
    ia_status: Optional[str] = None,
    ia_report_id: Optional[str] = None,
    ia_verified_at: Optional[str] = None,
    lineage: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
    render_profile: str = "print",
) -> str:
    """Render a YAML frontmatter evidence block for a single document.

    Only includes fields that have values (no null/empty fields).
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    source_hash = compute_source_hash(content)

    lines = ["---"]
    lines.append(f"project_id: {project_id}")
    lines.append(f"display_id: {display_id}")
    lines.append(f"doc_type_id: {doc_type_id}")

    if document_version is not None:
        lines.append(f"document_version: {document_version}")

    lines.append(f"source_hash: {source_hash}")
    lines.append(f"renderer_version: {_RENDERER_VERSION}")
    lines.append(f"render_profile: {render_profile}")
    lines.append(f"generated_at: {generated_at}")

    # IA verification
    if ia_status:
        lines.append("ia_verification:")
        lines.append(f"  status: {ia_status}")
        if ia_report_id:
            lines.append(f"  report_id: {ia_report_id}")
        if ia_verified_at:
            lines.append(f"  verified_at: {ia_verified_at}")

    # Lineage
    if lineage:
        lines.append("lineage:")
        for key, value in lineage.items():
            if isinstance(value, list):
                lines.append(f"  {key}: {json.dumps(value)}")
            else:
                lines.append(f"  {key}: {value}")

    lines.append("---")
    return "\n".join(lines) + "\n"


def render_evidence_index(documents: List[Dict[str, Any]]) -> str:
    """Render an Evidence Index table for a project binder.

    Args:
        documents: List of dicts, each with:
            - display_id, title, version, ia_status, source_hash

    Returns:
        GFM table string.
    """
    lines = [
        "## Evidence Index",
        "",
        "| Display ID | Title | Version | IA Status | Source Hash |",
        "| --- | --- | --- | --- | --- |",
    ]

    for doc in documents:
        display_id = doc.get("display_id", "")
        title = doc.get("title", "")
        version = doc.get("version", "")
        ia_status = doc.get("ia_status", "")
        source_hash = doc.get("source_hash", "")
        lines.append(f"| {display_id} | {title} | {version} | {ia_status} | {source_hash} |")

    return "\n".join(lines)

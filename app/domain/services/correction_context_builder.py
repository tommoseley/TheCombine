"""
Correction context builder for prompt assembly (ADR-069).

Loads operator corrections applicable to a pipeline stage and renders
them as numbered text with provenance tags for injection into task prompts.

Per ADR-069 §3.5: corrections are injected via {{operator_corrections}}
template variable. If no corrections apply, the section is absent.
"""

import logging
from typing import List, Tuple
from uuid import UUID

from app.domain.services.authority_service import AuthorityService

logger = logging.getLogger(__name__)


async def build_correction_text(
    project_id: str,
    stage: str,
    authority_service: AuthorityService,
) -> Tuple[str, List[str]]:
    """Build correction text for prompt injection.

    Args:
        project_id: Project UUID as string
        stage: Pipeline stage name (e.g., 'TA', 'IP', 'PD')
        authority_service: AuthorityService instance

    Returns:
        Tuple of (rendered_text, authority_record_ids).
        Both empty if no corrections apply.
    """
    try:
        project_uuid = UUID(project_id)
    except (ValueError, TypeError):
        return "", []

    corrections = await authority_service.get_corrections_for_stage(
        project_uuid, stage
    )

    if not corrections:
        return "", []

    lines = []
    record_ids = []
    for i, record in enumerate(corrections, start=1):
        text = ""
        if isinstance(record.value, dict):
            text = record.value.get("text", "")
        lines.append(f"{i}. [From {record.stage} rewind] {text}")
        record_ids.append(str(record.id))

    rendered = "\n".join(lines)

    logger.info(
        "Built correction context for stage '%s' (project=%s, corrections=%d)",
        stage, project_id, len(corrections),
    )

    return rendered, record_ids

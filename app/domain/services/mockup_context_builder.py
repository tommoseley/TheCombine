"""
Mockup context builder for prompt assembly.

Loads project mockup artifacts and builds multimodal content blocks
for injection into LLM prompt messages.

Per ADR-068: Mockups are treated as design intent context, not instructions.
"""

import base64
import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Stages where mockups are injected by default
DEFAULT_MOCKUP_STAGES = {"project_discovery", "technical_architecture"}

MOCKUP_FRAMING = (
    "## Reference Mockups\n"
    "The following mockups represent intended UX design for this project.\n"
    "Treat them as design intent, not implementation specification.\n"
)


async def load_mockup_content_blocks(
    project_id: str,
    stage: str,
    db_session: AsyncSession,
) -> tuple:
    """Load mockup artifacts and build multimodal content blocks.

    Args:
        project_id: Project UUID as string
        stage: Pipeline stage ID (e.g., 'project_discovery', 'technical_architecture')
        db_session: Async database session

    Returns:
        Tuple of (content_blocks: List[Dict], artifact_ids: List[str]).
        Both empty lists if no mockups available.
    """
    from app.api.models.project_artifact import ProjectArtifact

    try:
        project_uuid = UUID(project_id)
    except (ValueError, TypeError):
        return [], []

    result = await db_session.execute(
        select(ProjectArtifact)
        .where(
            ProjectArtifact.project_id == project_uuid,
            ProjectArtifact.artifact_type == "mockup",
        )
        .order_by(ProjectArtifact.created_at)
    )
    artifacts = result.scalars().all()

    if not artifacts:
        return [], []

    # Filter by stage hints
    selected = []
    for artifact in artifacts:
        hints = (artifact.metadata_ or {}).get("stage_hints", [])
        if not hints or stage in hints:
            selected.append(artifact)

    if not selected:
        return [], []

    # Build content blocks
    blocks: List[Dict[str, Any]] = [
        {"type": "text", "text": MOCKUP_FRAMING},
    ]

    artifact_ids = []
    for artifact in selected:
        # Only inject image types as multimodal (skip PDFs for now)
        if artifact.mime_type.startswith("image/"):
            encoded = base64.b64encode(artifact.file_content).decode("ascii")
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": artifact.mime_type,
                    "data": encoded,
                },
            })
            blocks.append({
                "type": "text",
                "text": f"[Mockup: {artifact.label}]\n",
            })
            artifact_ids.append(str(artifact.id))
        else:
            # Non-image artifacts get a text note only
            blocks.append({
                "type": "text",
                "text": f"[Attached: {artifact.label} ({artifact.mime_type})]\n",
            })
            artifact_ids.append(str(artifact.id))

    logger.info(
        f"Loaded {len(selected)} mockup(s) for stage '{stage}' "
        f"(project={project_id}, artifact_ids={artifact_ids})"
    )

    return blocks, artifact_ids

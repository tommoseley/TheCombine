"""Project creation service.

Handles project creation logic including intake-based creation.
Used by both API endpoints and web routes.
"""

import logging
import re
import uuid as uuid_module
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.project import Project

logger = logging.getLogger(__name__)


def _generate_project_id_prefix(project_name: str) -> str:
    """Generate 2-5 letter prefix from project name.

    Examples:
        "Legacy Inventory Replacement" -> "LIR"
        "Mobile App" -> "MA"
        "Customer Portal Redesign" -> "CPR"
    """
    words = re.findall(r'[A-Za-z]+', project_name)
    if not words:
        return "PRJ"

    initials = ''.join(w[0].upper() for w in words[:5])

    if len(initials) < 2:
        initials = (initials + "X" * 2)[:2]

    return initials[:5]


async def generate_unique_project_id(db: AsyncSession, project_name: str) -> str:
    """Generate unique project_id in format LIR-001."""
    prefix = _generate_project_id_prefix(project_name)

    pattern = f"{prefix}-%"
    result = await db.execute(
        select(Project.project_id)
        .where(Project.project_id.like(pattern))
        .order_by(Project.project_id.desc())
    )
    existing = result.scalars().all()

    if not existing:
        return f"{prefix}-001"

    max_num = 0
    for pid in existing:
        try:
            num = int(pid.split('-')[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            continue

    return f"{prefix}-{max_num + 1:03d}"


def _parse_user_id(user_id: Optional[str]) -> Optional[UUID]:
    """Parse user_id to UUID, handling various formats."""
    if user_id is None:
        return None

    try:
        if isinstance(user_id, uuid_module.UUID):
            return user_id
        elif hasattr(user_id, 'hex'):
            # asyncpg UUID - convert via hex
            return uuid_module.UUID(user_id.hex)
        else:
            return uuid_module.UUID(str(user_id))
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse user_id: {user_id}")
        return None


async def create_project_from_intake(
    db: AsyncSession,
    intake_document: Dict[str, Any],
    execution_id: str,
    user_id: Optional[str] = None,
) -> Project:
    """Create a Project from completed intake workflow.

    Extracts project_name from the intake document and creates both
    the Project and the concierge_intake Document.

    Args:
        db: Database session
        intake_document: The intake document content
        execution_id: Workflow execution ID for traceability
        user_id: Optional owner user ID

    Returns:
        Created Project instance

    Raises:
        ValueError: If project_name cannot be extracted
    """
    # Extract project name
    project_name = intake_document.get("project_name")
    if not project_name:
        summary = intake_document.get("summary", {})
        if isinstance(summary, dict):
            project_name = summary.get("description", "New Project")[:100]
        else:
            project_name = "New Project"

    if not project_name or project_name == "New Project":
        logger.warning("Could not extract meaningful project name from intake document")

    # Generate unique project_id
    project_id = await generate_unique_project_id(db, project_name)

    # Parse user_id to UUID
    owner_uuid = _parse_user_id(user_id)

    # Create project
    project = Project(
        project_id=project_id,
        name=project_name,
        description=(
            intake_document.get("summary", {}).get("description")
            if isinstance(intake_document.get("summary"), dict)
            else None
        ),
        status="active",
        icon="folder",
        owner_id=owner_uuid,
        organization_id=owner_uuid,
        created_by=str(user_id) if user_id else None,
        meta={
            "intake_document": intake_document,
            "workflow_execution_id": execution_id,
        }
    )

    db.add(project)
    await db.flush()  # Get the project.id before creating document

    # Create concierge_intake document
    summary_obj = intake_document.get("summary", {})
    doc_summary = (
        summary_obj.get("description", "")[:500]
        if isinstance(summary_obj, dict)
        else str(summary_obj)[:500]
    )

    intake_doc = Document(
        space_type="project",
        space_id=project.id,
        doc_type_id="concierge_intake",
        title=f"Concierge Intake: {project_name}",
        summary=doc_summary,
        content=intake_document,
        status="active",
        lifecycle_state="complete",
        version=1,
        is_latest=True,
    )

    db.add(intake_doc)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Created project {project_id}: {project_name}")
    logger.info(f"Created concierge_intake document for project {project.id}")

    return project


def extract_intake_document_from_state(state) -> Optional[Dict[str, Any]]:
    """Extract intake document from workflow state.

    Checks multiple possible locations in context_state and node_history.

    Args:
        state: Workflow state object

    Returns:
        Intake document dict or None if not found
    """
    import json

    context_state = state.context_state or {}

    # Try multiple possible keys
    intake_doc = (
        context_state.get("document_concierge_intake_document") or
        context_state.get("last_produced_document") or
        context_state.get("concierge_intake_document")
    )

    if intake_doc:
        return intake_doc

    # Try to find in node history metadata
    for execution in reversed(state.node_history):
        if execution.node_id == "generation":
            response = execution.metadata.get("response")
            if response:
                try:
                    parsed = json.loads(response) if isinstance(response, str) else response
                    logger.info(
                        f"Found intake doc in node history: "
                        f"{list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}"
                    )
                    return parsed
                except json.JSONDecodeError:
                    continue

    logger.warning("No intake document found in workflow state")
    return None

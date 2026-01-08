"""
Seed data for component_artifacts and document_definitions tables.

Per ADR-034: Canonical components and document definitions are seeded as governed artifacts.

Usage:
    python -m app.domain.registry.seed_component_artifacts
    
Or call seed_component_artifacts(db) from your migration/startup.
"""

from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.models.schema_artifact import SchemaArtifact
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.document_definition_service import DocumentDefinitionService


logger = logging.getLogger(__name__)


# =============================================================================
# CANONICAL COMPONENT SPECIFICATIONS - ADR-034
# =============================================================================

OPEN_QUESTION_V1_COMPONENT = {
    "component_id": "component:OpenQuestionV1:1.0.0",
    "schema_id": "schema:OpenQuestionV1",
    "generation_guidance": {
        "bullets": [
            "Provide a stable question id (e.g., Q-001).",
            "Write a clear, specific question that requires human decision.",
            "Set blocking=true only if work cannot proceed responsibly without an answer.",
            "Explain why_it_matters in one sentence.",
            "Include options only if there are meaningful discrete choices.",
            "If options exist, default_response SHOULD match one option.",
            "Use notes for assumptions, context, or follow-up suggestions."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:OpenQuestionV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


# =============================================================================
# DOCUMENT DEFINITIONS - ADR-034
# =============================================================================

EPIC_BACKLOG_DOCDEF = {
    "document_def_id": "docdef:EpicBacklog:1.0.0",
    "document_schema_id": None,  # nullable for MVP; schema bundle from components
    "prompt_header": {
        "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
        "constraints": [
            "Output valid JSON matching the document schema.",
            "Be specific and actionable.",
            "Do not invent requirements not supported by inputs.",
            "Each epic must have at least one open question if unknowns exist."
        ]
    },
    "sections": [
        {
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}


# Lists for seeding
INITIAL_COMPONENT_ARTIFACTS: List[Dict[str, Any]] = [
    OPEN_QUESTION_V1_COMPONENT,
]

INITIAL_DOCUMENT_DEFINITIONS: List[Dict[str, Any]] = [
    EPIC_BACKLOG_DOCDEF,
]


async def _get_schema_artifact_id(db: AsyncSession, schema_id: str) -> str:
    """
    Look up schema_artifact UUID by schema_id.
    
    Args:
        db: Database session
        schema_id: Schema ID (e.g., "OpenQuestionV1" or "schema:OpenQuestionV1")
        
    Returns:
        UUID of the schema artifact
        
    Raises:
        ValueError: If schema not found
    """
    # Strip 'schema:' prefix if present
    lookup_id = schema_id
    if schema_id.startswith("schema:"):
        lookup_id = schema_id[7:]
    
    stmt = select(SchemaArtifact).where(SchemaArtifact.schema_id == lookup_id)
    result = await db.execute(stmt)
    schema = result.scalar_one_or_none()
    
    if not schema:
        raise ValueError(f"Schema artifact not found: {schema_id}")
    
    return schema.id


async def seed_component_artifacts(db: AsyncSession) -> int:
    """
    Seed the component_artifacts table with canonical components.
    
    Skips any artifacts that already exist (by component_id).
    
    Args:
        db: Database session
        
    Returns:
        Number of artifacts created
    """
    service = ComponentRegistryService(db)
    created_count = 0
    
    for artifact_data in INITIAL_COMPONENT_ARTIFACTS:
        component_id = artifact_data["component_id"]
        
        # Check if already exists
        existing = await service.get(component_id)
        
        if existing:
            logger.info(f"Component '{component_id}' already exists, skipping")
            continue
        
        # Look up schema artifact UUID
        schema_artifact_id = await _get_schema_artifact_id(db, artifact_data["schema_id"])
        
        # Create the component
        await service.create(
            component_id=component_id,
            schema_artifact_id=schema_artifact_id,
            schema_id=artifact_data["schema_id"],
            generation_guidance=artifact_data["generation_guidance"],
            view_bindings=artifact_data["view_bindings"],
            status=artifact_data["status"],
            created_by="seed",
        )
        
        created_count += 1
        logger.info(f"Created component: {component_id} ({artifact_data['status']})")
    
    await db.commit()
    logger.info(f"Seeded {created_count} component artifacts")
    return created_count


async def seed_document_definitions(db: AsyncSession) -> int:
    """
    Seed the document_definitions table with document definitions.
    
    Skips any definitions that already exist (by document_def_id).
    
    Args:
        db: Database session
        
    Returns:
        Number of definitions created
    """
    service = DocumentDefinitionService(db)
    created_count = 0
    
    for docdef_data in INITIAL_DOCUMENT_DEFINITIONS:
        document_def_id = docdef_data["document_def_id"]
        
        # Check if already exists
        existing = await service.get(document_def_id)
        
        if existing:
            logger.info(f"Document definition '{document_def_id}' already exists, skipping")
            continue
        
        # Create the document definition
        await service.create(
            document_def_id=document_def_id,
            prompt_header=docdef_data["prompt_header"],
            sections=docdef_data["sections"],
            document_schema_id=docdef_data.get("document_schema_id"),
            status=docdef_data["status"],
            created_by="seed",
        )
        
        created_count += 1
        logger.info(f"Created document definition: {document_def_id} ({docdef_data['status']})")
    
    await db.commit()
    logger.info(f"Seeded {created_count} document definitions")
    return created_count


async def seed_all(db: AsyncSession) -> Dict[str, int]:
    """
    Seed all component artifacts and document definitions.
    
    Args:
        db: Database session
        
    Returns:
        Dict with counts: {"components": n, "docdefs": n}
    """
    components = await seed_component_artifacts(db)
    docdefs = await seed_document_definitions(db)
    
    return {
        "components": components,
        "docdefs": docdefs,
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()  # Load .env before importing database
    from app.core.database import async_session_factory
    
    async def main():
        async with async_session_factory() as db:
            counts = await seed_all(db)
            print(f"Seeded {counts['components']} components, {counts['docdefs']} document definitions")
    
    asyncio.run(main())



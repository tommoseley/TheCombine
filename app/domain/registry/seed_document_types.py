"""
Seed data for document_types table.

Run this after creating the document_types table to populate
the initial document types.

Usage:
    python -m app.domain.registry.seed_document_types
    
Or call seed_document_types(db) from your migration.
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.api.models.document_type import DocumentType

logger = logging.getLogger(__name__)


# =============================================================================
# SEED DATA - Initial Document Types
# =============================================================================

INITIAL_DOCUMENT_TYPES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # ARCHITECTURE DOCUMENTS
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "project_discovery",
        "name": "Project Discovery",
        "view_docdef": "ProjectDiscovery",
        "description": (
            "Early architectural discovery performed before PM decomposition. "
            "Surfaces critical questions, identifies constraints and risks, "
            "proposes candidate directions, and establishes guardrails."
        ),
        "category": "architecture",
        "icon": "search",
        "builder_role": "architect",
        "builder_task": "preliminary",
        "handler_id": "project_discovery",
        "required_inputs": [],  # No dependencies - this is the first document
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 10,
        "schema_definition": {
            "type": "object",
            "required": ["project_name", "preliminary_summary"],
            "properties": {
                "project_name": {"type": "string"},
                "preliminary_summary": {"type": "string"},
                "unknowns": {"type": "array", "items": {"type": "object"}},
                "blocking_questions": {"type": "array", "items": {"type": "object"}},
                "early_decision_points": {"type": "array", "items": {"type": "object"}},
                "mvp_guardrails": {"type": "array", "items": {"type": "object"}},
                "architectural_directions": {"type": "array", "items": {"type": "object"}},
            }
        },
        "schema_version": "1.0",
    },
    {
        "doc_type_id": "architecture_spec",
        "name": "Architecture Specification",
        "view_docdef": "ArchitecturalSummaryView",
        "description": (
            "Comprehensive architecture specification including components, "
            "interfaces, data models, workflows, and quality attributes. "
            "Built after discovery, informs development."
        ),
        "category": "architecture",
        "icon": "landmark",
        "builder_role": "architect",
        "builder_task": "final",
        "handler_id": "architecture_spec",
        "required_inputs": ["project_discovery"],  # Depends on discovery
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",  # Can also be 'epic' for epic-level architecture
        "display_order": 20,
        "schema_definition": {
            "type": "object",
            "required": ["architecture_summary", "components"],
            "properties": {
                "architecture_summary": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "style": {"type": "string"},
                        "key_decisions": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "purpose"],
                        "properties": {
                            "name": {"type": "string"},
                            "purpose": {"type": "string"},
                            "technology": {"type": "string"},
                            "interfaces": {"type": "array"},
                        }
                    }
                },
                "data_models": {"type": "array"},
                "api_interfaces": {"type": "array"},
                "quality_attributes": {"type": "object"},
                "workflows": {"type": "array"},
                "risks": {"type": "array"},
            }
        },
        "schema_version": "1.0",
    },
    
    # -------------------------------------------------------------------------
    # PLANNING DOCUMENTS
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "epic_backlog",
        "name": "Epic Set",
        "view_docdef": "EpicBacklogView",
        "description": (
            "Set of epics decomposed from project discovery. "
            "Defines the major work streams for the project."
        ),
        "category": "planning",
        "icon": "layers",
        "builder_role": "pm",
        "builder_task": "epic_generation",
        "handler_id": "epic_backlog",
        "required_inputs": ["project_discovery"],  # Needs discovery first
        "optional_inputs": ["architecture_spec"],  # Better with arch spec
        "gating_rules": {},
        "scope": "project",
        "display_order": 30,
        "schema_definition": {
            "type": "object",
            "required": ["epics"],
            "properties": {
                "epics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "objectives"],
                        "properties": {
                            "epic_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "objectives": {"type": "array", "items": {"type": "string"}},
                            "acceptance_criteria": {"type": "array"},
                            "dependencies": {"type": "array"},
                        }
                    }
                },
                "rationale": {"type": "string"},
                "sequencing_notes": {"type": "string"},
            }
        },
        "schema_version": "1.0",
    },
    {
        "doc_type_id": "story_backlog",
        "name": "Story Backlog",
        "view_docdef": "StoryBacklogView",
        "description": (
            "User stories decomposed from an epic. "
            "Detailed, implementable units of work."
        ),
        "category": "planning",
        "icon": "list-checks",
        "builder_role": "ba",
        "builder_task": "story_decomposition",
        "handler_id": "story_backlog",
        "required_inputs": [],  # Required at epic scope, so epic must exist
        "optional_inputs": ["architecture_spec"],
        "gating_rules": {},
        "scope": "epic",  # One per epic
        "display_order": 40,
        "schema_definition": {
            "type": "object",
            "required": ["stories"],
            "properties": {
                "epic_id": {"type": "string"},
                "stories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "description"],
                        "properties": {
                            "story_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "acceptance_criteria": {"type": "array"},
                            "story_points": {"type": "integer"},
                            "priority": {"type": "string"},
                        }
                    }
                }
            }
        },
        "schema_version": "1.0",
    },
]


async def seed_document_types(db: AsyncSession) -> int:
    """
    Seed the document_types table with initial document types.
    
    Skips any document types that already exist (by doc_type_id).
    
    Args:
        db: Database session
        
    Returns:
        Number of document types created
    """
    created_count = 0
    
    for doc_data in INITIAL_DOCUMENT_TYPES:
        doc_type_id = doc_data["doc_type_id"]
        
        # Check if already exists
        query = select(DocumentType).where(DocumentType.doc_type_id == doc_type_id)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Document type '{doc_type_id}' already exists, skipping")
            continue
        
        # Create new document type
        doc_type = DocumentType(**doc_data)
        db.add(doc_type)
        created_count += 1
        logger.info(f"Created document type: {doc_type_id}")
    
    await db.commit()
    logger.info(f"Seeded {created_count} document types")
    
    return created_count


async def clear_document_types(db: AsyncSession) -> int:
    """
    Clear all document types from the table.
    
    WARNING: This is destructive. Use only in development/testing.
    
    Args:
        db: Database session
        
    Returns:
        Number of document types deleted
    """
    from sqlalchemy import delete
    
    result = await db.execute(delete(DocumentType))
    await db.commit()
    
    deleted_count = result.rowcount
    logger.warning(f"Deleted {deleted_count} document types")
    
    return deleted_count


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from database import get_db_session
    
    async def main():
        async with get_db_session() as db:
            count = await seed_document_types(db)
            print(f"Seeded {count} document types")
    
    asyncio.run(main())
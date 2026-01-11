"""
Document Registry Loader - Query functions and seed data.

This module provides:
1. Query functions to load document type configurations from the database
2. Seed data for initial document types

Usage:
    from app.domain.registry.loader import get_document_config, seed_document_types
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.api.models.document_type import DocumentType

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DocumentNotFoundError(Exception):
    """Raised when a document type is not found in the registry."""
    
    def __init__(self, doc_type_id: str):
        self.doc_type_id = doc_type_id
        super().__init__(f"Document type '{doc_type_id}' not found in registry")


class DependencyNotMetError(Exception):
    """Raised when required dependencies are not met for building a document."""
    
    def __init__(self, doc_type_id: str, missing: List[str]):
        self.doc_type_id = doc_type_id
        self.missing = missing
        super().__init__(
            f"Cannot build '{doc_type_id}': missing dependencies {missing}"
        )


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

async def get_document_config(db: AsyncSession, doc_type_id: str) -> Dict[str, Any]:
    """
    Get the configuration for a document type.
    
    Args:
        db: Database session
        doc_type_id: The document type identifier
        
    Returns:
        Dictionary with document type configuration
        
    Raises:
        DocumentNotFoundError: If document type not found
    """
    query = select(DocumentType).where(
        DocumentType.doc_type_id == doc_type_id,
        DocumentType.is_active == True
    )
    result = await db.execute(query)
    doc_type = result.scalar_one_or_none()
    
    if doc_type is None:
        raise DocumentNotFoundError(doc_type_id)
    
    return doc_type.to_dict()


async def list_document_types(db: AsyncSession, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    List all document types.
    
    Args:
        db: Database session
        active_only: If True, only return active document types
        
    Returns:
        List of document type configurations
    """
    query = select(DocumentType).order_by(DocumentType.display_order)
    
    if active_only:
        query = query.where(DocumentType.is_active == True)
    
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def list_by_category(db: AsyncSession, category: str) -> List[Dict[str, Any]]:
    """
    List document types by category.
    
    Args:
        db: Database session
        category: The category to filter by (e.g., 'architecture', 'planning')
        
    Returns:
        List of document type configurations in that category
    """
    query = (
        select(DocumentType)
        .where(DocumentType.category == category)
        .where(DocumentType.is_active == True)
        .order_by(DocumentType.display_order)
    )
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def list_by_scope(db: AsyncSession, scope: str) -> List[Dict[str, Any]]:
    """
    List document types by scope.
    
    Args:
        db: Database session
        scope: The scope to filter by ('project', 'epic', 'story')
        
    Returns:
        List of document type configurations in that scope
    """
    query = (
        select(DocumentType)
        .where(DocumentType.scope == scope)
        .where(DocumentType.is_active == True)
        .order_by(DocumentType.display_order)
    )
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def get_dependencies(db: AsyncSession, doc_type_id: str) -> Dict[str, List[str]]:
    """
    Get the dependencies for a document type.
    
    Args:
        db: Database session
        doc_type_id: The document type identifier
        
    Returns:
        Dictionary with 'required' and 'optional' dependency lists
    """
    config = await get_document_config(db, doc_type_id)
    
    return {
        "required": config.get("required_inputs", []),
        "optional": config.get("optional_inputs", []),
    }


async def get_dependents(db: AsyncSession, doc_type_id: str) -> List[str]:
    """
    Get document types that depend on this document type.
    
    Args:
        db: Database session
        doc_type_id: The document type identifier
        
    Returns:
        List of doc_type_ids that require this document
    """
    all_types = await list_document_types(db)
    
    dependents = []
    for dt in all_types:
        required = dt.get("required_inputs", [])
        optional = dt.get("optional_inputs", [])
        if doc_type_id in required or doc_type_id in optional:
            dependents.append(dt["doc_type_id"])
    
    return dependents


async def can_build(
    db: AsyncSession, 
    doc_type_id: str, 
    existing_doc_types: List[str]
) -> Tuple[bool, List[str]]:
    """
    Check if a document type can be built given existing documents.
    
    Args:
        db: Database session
        doc_type_id: The document type to check
        existing_doc_types: List of doc_type_ids that already exist
        
    Returns:
        Tuple of (can_build, missing_dependencies)
    """
    config = await get_document_config(db, doc_type_id)
    required = config.get("required_inputs", [])
    
    missing = [dep for dep in required if dep not in existing_doc_types]
    
    return len(missing) == 0, missing


async def get_buildable_documents(
    db: AsyncSession,
    existing_doc_types: List[str],
    scope: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all document types that can currently be built.
    
    Args:
        db: Database session
        existing_doc_types: List of doc_type_ids that already exist
        scope: Optional scope filter ('project', 'epic', 'story')
        
    Returns:
        List of document type configurations that can be built
    """
    all_types = await list_document_types(db)
    
    if scope:
        all_types = [dt for dt in all_types if dt.get("scope") == scope]
    
    buildable = []
    for dt in all_types:
        required = dt.get("required_inputs", [])
        if all(dep in existing_doc_types for dep in required):
            buildable.append(dt)
    
    return buildable


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
        "scope": "project",
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
        "name": "Epic Backlog",
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
    # =========================================================================
    # WS-STORY-BACKLOG-COMMANDS: story_backlog (system-initialized)
    # =========================================================================
    {
        "doc_type_id": "story_backlog",
        "name": "Story Backlog",
        "description": (
            "Canonical story backlog containing epics with nested story summaries. "
            "Initialized from EpicBacklog, populated by generate-epic commands."
        ),
        "category": "planning",
        "icon": "list-checks",
        "builder_role": "system",
        "builder_task": "init",
        "handler_id": "story_backlog_init",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 40,
        "schema_definition": {
            "type": "object",
            "required": ["project_id", "epics"],
            "properties": {
                "project_id": {"type": "string"},
                "project_name": {"type": "string"},
                "source_epic_backlog_ref": {"type": "object"},
                "epics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["epic_id", "name", "stories"],
                        "properties": {
                            "epic_id": {"type": "string"},
                            "name": {"type": "string"},
                            "intent": {"type": "string"},
                            "mvp_phase": {"type": "string"},
                            "stories": {"type": "array"}
                        }
                    }
                }
            }
        },
        "schema_version": "2.0",
    },
    # =========================================================================
    # WS-STORY-BACKLOG-COMMANDS: story_detail (BA-generated per story)
    # =========================================================================
    {
        "doc_type_id": "story_detail",
        "name": "Story Detail",
        "description": (
            "Full BA story output with acceptance criteria, components, and notes. "
            "Source of truth for individual story details."
        ),
        "category": "planning",
        "icon": "file-text",
        "builder_role": "ba",
        "builder_task": "story_backlog",
        "handler_id": "story_detail",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "story",
        "display_order": 41,
        "schema_definition": {
            "type": "object",
            "required": ["story_id", "epic_id", "title", "description"],
            "properties": {
                "story_id": {"type": "string"},
                "epic_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "acceptance_criteria": {"type": "array"},
                "related_arch_components": {"type": "array"},
                "related_pm_story_ids": {"type": "array"},
                "notes": {"type": "array"},
                "mvp_phase": {"type": "string"}
            }
        },
        "schema_version": "1.0",
    },
]


# =============================================================================
# SEED FUNCTIONS
# =============================================================================

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








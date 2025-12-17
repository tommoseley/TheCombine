"""
Document Registry Loader - Database-backed document type configuration.

This module provides functions to query the document_types table
and retrieve configuration for building documents.

The registry is the source of truth for:
- What documents exist
- How they are built (prompts, handlers)
- What they depend on
- How they are displayed

Adding a new document type is an INSERT, not a code change.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.models.document_type import DocumentType

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document type is not found in the registry."""
    def __init__(self, doc_type_id: str):
        self.doc_type_id = doc_type_id
        super().__init__(f"Document type not found: {doc_type_id}")


class DependencyNotMetError(Exception):
    """Raised when required dependencies are not met."""
    def __init__(self, doc_type_id: str, missing: List[str]):
        self.doc_type_id = doc_type_id
        self.missing = missing
        super().__init__(f"Missing dependencies for {doc_type_id}: {', '.join(missing)}")


async def get_document_config(
    db: AsyncSession, 
    doc_type_id: str,
    active_only: bool = True
) -> Dict[str, Any]:
    """
    Get the full configuration for a document type.
    
    Args:
        db: Database session
        doc_type_id: The stable identifier (e.g., 'project_discovery')
        active_only: If True, only return active document types
        
    Returns:
        Dictionary with full document type configuration
        
    Raises:
        DocumentNotFoundError: If document type not found
    """
    query = select(DocumentType).where(DocumentType.doc_type_id == doc_type_id)
    
    if active_only:
        query = query.where(DocumentType.is_active == True)
    
    result = await db.execute(query)
    doc_type = result.scalar_one_or_none()
    
    if not doc_type:
        raise DocumentNotFoundError(doc_type_id)
    
    return doc_type.to_dict()


async def list_document_types(
    db: AsyncSession,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    List all document types.
    
    Args:
        db: Database session
        active_only: If True, only return active document types
        
    Returns:
        List of document type configurations, ordered by display_order
    """
    query = select(DocumentType).order_by(DocumentType.display_order, DocumentType.name)
    
    if active_only:
        query = query.where(DocumentType.is_active == True)
    
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def list_by_category(
    db: AsyncSession,
    category: str,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    List document types by category.
    
    Args:
        db: Database session
        category: Category to filter by (e.g., 'architecture', 'planning')
        active_only: If True, only return active document types
        
    Returns:
        List of document type configurations in the category
    """
    query = select(DocumentType).where(
        DocumentType.category == category
    ).order_by(DocumentType.display_order, DocumentType.name)
    
    if active_only:
        query = query.where(DocumentType.is_active == True)
    
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def list_by_scope(
    db: AsyncSession,
    scope: str,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    List document types by scope.
    
    Args:
        db: Database session
        scope: Scope to filter by ('project', 'epic', 'story')
        active_only: If True, only return active document types
        
    Returns:
        List of document type configurations with the scope
    """
    query = select(DocumentType).where(
        DocumentType.scope == scope
    ).order_by(DocumentType.display_order, DocumentType.name)
    
    if active_only:
        query = query.where(DocumentType.is_active == True)
    
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def get_dependencies(
    db: AsyncSession,
    doc_type_id: str
) -> Dict[str, List[str]]:
    """
    Get dependencies for a document type.
    
    Args:
        db: Database session
        doc_type_id: The document type to check
        
    Returns:
        Dictionary with 'required' and 'optional' lists of doc_type_ids
        
    Raises:
        DocumentNotFoundError: If document type not found
    """
    config = await get_document_config(db, doc_type_id)
    
    return {
        "required": config.get("required_inputs", []),
        "optional": config.get("optional_inputs", []),
    }


async def get_dependents(
    db: AsyncSession,
    doc_type_id: str,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get document types that depend on this one.
    
    Args:
        db: Database session
        doc_type_id: The document type to check
        active_only: If True, only return active document types
        
    Returns:
        List of document types that have this as a required or optional input
    """
    # Query for documents that have this doc_type_id in their required_inputs
    # Using PostgreSQL JSONB containment operator
    query = select(DocumentType).where(
        DocumentType.required_inputs.contains([doc_type_id])
    ).order_by(DocumentType.display_order)
    
    if active_only:
        query = query.where(DocumentType.is_active == True)
    
    result = await db.execute(query)
    doc_types = result.scalars().all()
    
    return [dt.to_dict() for dt in doc_types]


async def can_build(
    db: AsyncSession,
    doc_type_id: str,
    existing_documents: List[str]
) -> tuple[bool, List[str]]:
    """
    Check if a document type can be built given existing documents.
    
    Args:
        db: Database session
        doc_type_id: The document type to build
        existing_documents: List of doc_type_ids that already exist
        
    Returns:
        Tuple of (can_build, missing_dependencies)
        
    Raises:
        DocumentNotFoundError: If document type not found
    """
    deps = await get_dependencies(db, doc_type_id)
    required = deps.get("required", [])
    
    missing = [dep for dep in required if dep not in existing_documents]
    
    return (len(missing) == 0, missing)


async def get_buildable_documents(
    db: AsyncSession,
    existing_documents: List[str],
    scope: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all document types that can be built given existing documents.
    
    Args:
        db: Database session
        existing_documents: List of doc_type_ids that already exist
        scope: Optional scope filter ('project', 'epic', 'story')
        active_only: If True, only return active document types
        
    Returns:
        List of document types that can be built now
    """
    if scope:
        all_docs = await list_by_scope(db, scope, active_only)
    else:
        all_docs = await list_document_types(db, active_only)
    
    buildable = []
    for doc in all_docs:
        doc_type_id = doc["doc_type_id"]
        
        # Skip if already exists
        if doc_type_id in existing_documents:
            continue
        
        # Check dependencies
        required = doc.get("required_inputs", [])
        if all(dep in existing_documents for dep in required):
            buildable.append(doc)
    
    return buildable


async def get_document_status(
    db: AsyncSession,
    project_id: str,
    artifact_repo,  # ArtifactRepository - avoid circular import
    scope: str = "project",
    epic_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get status of all document types for a project/epic.
    
    Returns each document type with:
    - exists: bool
    - can_build: bool
    - missing_deps: List[str]
    - artifact_id: Optional[str] if exists
    
    Args:
        db: Database session
        project_id: Project to check
        artifact_repo: Repository for checking artifact existence
        scope: Filter by scope
        epic_id: Epic ID if scope is 'epic' or 'story'
        
    Returns:
        List of document types with status information
    """
    doc_types = await list_by_scope(db, scope)
    
    # Get existing artifacts for this project/epic
    # This would query artifacts and map them to doc_type_ids
    # Implementation depends on artifact structure
    
    status_list = []
    existing_doc_types = []  # Populated from artifacts
    
    for doc in doc_types:
        doc_type_id = doc["doc_type_id"]
        required = doc.get("required_inputs", [])
        
        # Check if this document exists
        # This requires mapping artifact_type to doc_type_id
        exists = doc_type_id in existing_doc_types
        
        # Check if dependencies are met
        missing = [dep for dep in required if dep not in existing_doc_types]
        
        status_list.append({
            **doc,
            "exists": exists,
            "can_build": len(missing) == 0 and not exists,
            "missing_deps": missing,
            "artifact_id": None,  # Would be populated if exists
        })
    
    return status_list
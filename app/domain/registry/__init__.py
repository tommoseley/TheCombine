"""
Document Registry - The heart of document-centric architecture.

This package provides access to the document type registry,
which defines what documents the system can produce and how.

Usage:
    from app.domain.registry import (
        get_document_config,
        list_document_types,
        list_by_category,
        get_dependencies
    )
    
    # Get config for a document type
    config = await get_document_config(db, "project_discovery")
    
    # List all active document types
    doc_types = await list_document_types(db)
    
    # List by category
    arch_docs = await list_by_category(db, "architecture")
    
    # Get dependencies
    deps = await get_dependencies(db, "architecture_spec")
"""

from app.domain.registry.loader import (
    get_document_config,
    list_document_types,
    list_by_category,
    list_by_scope,
    get_dependencies,
    get_dependents,
    can_build,
    DocumentNotFoundError,
    DependencyNotMetError,
)

__all__ = [
    "get_document_config",
    "list_document_types",
    "list_by_category",
    "list_by_scope",
    "get_dependencies",
    "get_dependents",
    "can_build",
    "DocumentNotFoundError",
    "DependencyNotMetError",
]
"""
Domain-level protocols for registry services.

These protocols define the interface that domain code uses to access
document definitions, components, and schemas without depending on
the API layer implementation.

Created by WS-CLEANUP-006 to fix domain/API boundary leakage.
"""

from typing import Any, Dict, List, Optional, Protocol


class DocumentDefinitionPort(Protocol):
    """Protocol for document definition lookup."""

    async def get(self, document_def_id: str) -> Any:
        """Get a document definition by ID.

        Returns the definition object, or None if not found.
        """
        ...


class ComponentRegistryPort(Protocol):
    """Protocol for component registry lookup."""

    async def get(self, component_id: str) -> Any:
        """Get a component by ID.

        Returns the component object, or None if not found.
        """
        ...


class SchemaRegistryPort(Protocol):
    """Protocol for schema registry lookup."""

    async def get_by_id(self, schema_id: str, version: Optional[str] = None) -> Any:
        """Get a schema by ID and optional version.

        Returns the schema artifact, or None if not found.
        """
        ...

    async def get_accepted(self, schema_id: str) -> Any:
        """Get the accepted version of a schema.

        Returns the schema artifact, or None if not found.
        """
        ...


class DocumentServicePort(Protocol):
    """Protocol for document persistence."""

    async def get_existing_doc_types(
        self, space_type: str, space_id: str
    ) -> List[str]:
        """Get list of existing document type IDs for a space."""
        ...

    async def create_document(
        self,
        space_type: str,
        space_id: str,
        doc_type_id: str,
        title: str,
        content: Dict[str, Any],
        created_by: str,
        created_by_type: str = "system",
        builder_metadata: Optional[Dict[str, Any]] = None,
        derived_from: Optional[str] = None,
    ) -> Any:
        """Create and persist a document. Returns the document object."""
        ...

    async def get_latest(
        self, space_type: str, space_id: str, doc_type: str
    ) -> Any:
        """Get the latest document of a given type for a space."""
        ...


class RolePromptServicePort(Protocol):
    """Protocol for role prompt loading."""

    async def get_role_task(self, role_name: str, task_name: str) -> Any:
        """Get a composed prompt for a role/task combination."""
        ...

    async def build_prompt(self, role_name: str, task_name: str) -> Any:
        """Build a prompt for a role/task combination."""
        ...

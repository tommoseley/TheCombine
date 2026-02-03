"""
Admin Workbench Service for Git-canonical configuration.

Per ADR-044, this service provides read access to Document Type Packages
and shared artifacts from combine-config/.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.package_loader import (
    PackageLoader,
    PackageLoaderError,
    PackageNotFoundError,
    VersionNotFoundError,
    get_package_loader,
    reset_package_loader,
)
from app.config.package_model import (
    DocumentTypePackage,
    RolePrompt,
    Template,
    ActiveReleases,
)

logger = logging.getLogger(__name__)


class AdminWorkbenchService:
    """
    Service for Admin Workbench operations.

    Provides a high-level interface for browsing and inspecting
    Git-canonical configuration artifacts.
    """

    def __init__(self, loader: Optional[PackageLoader] = None):
        """
        Initialize the service.

        Args:
            loader: Optional PackageLoader instance. Uses singleton if not provided.
        """
        self._loader = loader or get_package_loader()

    # =========================================================================
    # Document Types
    # =========================================================================

    def list_document_types(self) -> List[Dict[str, Any]]:
        """
        List all available document types with summary info.

        Returns:
            List of document type summaries.
        """
        doc_type_ids = self._loader.list_document_types()
        active = self._loader.get_active_releases()

        summaries = []
        for doc_type_id in sorted(doc_type_ids):
            active_version = active.get_doc_type_version(doc_type_id)

            try:
                package = self._loader.get_document_type(doc_type_id)
                summaries.append({
                    "doc_type_id": doc_type_id,
                    "display_name": package.display_name,
                    "active_version": active_version,
                    "authority_level": package.authority_level.value,
                    "creation_mode": package.creation_mode.value,
                    "scope": package.scope.value,
                    "description": package.description,
                })
            except PackageLoaderError as e:
                logger.warning(f"Could not load document type {doc_type_id}: {e}")
                summaries.append({
                    "doc_type_id": doc_type_id,
                    "display_name": doc_type_id.replace("_", " ").title(),
                    "active_version": active_version,
                    "authority_level": None,
                    "creation_mode": None,
                    "scope": None,
                    "description": None,
                    "error": str(e),
                })

        return summaries

    def get_document_type(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get full document type details.

        Args:
            doc_type_id: Document type identifier
            version: Specific version or None for active version

        Returns:
            Full document type details including artifacts

        Raises:
            PackageNotFoundError: Document type not found
            VersionNotFoundError: Requested version not found
        """
        package = self._loader.get_document_type(doc_type_id, version)

        return {
            "doc_type_id": package.doc_type_id,
            "display_name": package.display_name,
            "version": package.version,
            "description": package.description,
            "authority_level": package.authority_level.value,
            "creation_mode": package.creation_mode.value,
            "production_mode": package.production_mode.value if package.production_mode else None,
            "scope": package.scope.value,
            "required_inputs": package.required_inputs,
            "optional_inputs": package.optional_inputs,
            "creates_children": package.creates_children,
            "parent_doc_type": package.parent_doc_type,
            "role_prompt_ref": package.role_prompt_ref,
            "template_ref": package.template_ref,
            "requires_pgc": package.requires_pgc(),
            "is_llm_generated": package.is_llm_generated(),
            "artifacts": {
                "task_prompt": package.artifacts.task_prompt,
                "qa_prompt": package.artifacts.qa_prompt,
                "pgc_context": package.artifacts.pgc_context,
                "schema": package.artifacts.schema,
            },
            "ui": {
                "icon": package.ui.icon,
                "category": package.ui.category,
                "display_order": package.ui.display_order,
            },
        }

    def get_document_type_versions(self, doc_type_id: str) -> List[str]:
        """
        List all available versions for a document type.

        Args:
            doc_type_id: Document type identifier

        Returns:
            List of version strings
        """
        return self._loader.list_document_type_versions(doc_type_id)

    def get_task_prompt(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get the task prompt content for a document type.

        Args:
            doc_type_id: Document type identifier
            version: Specific version or None for active version

        Returns:
            Task prompt content or None
        """
        package = self._loader.get_document_type(doc_type_id, version)
        return package.get_task_prompt()

    def get_schema(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the output schema for a document type.

        Args:
            doc_type_id: Document type identifier
            version: Specific version or None for active version

        Returns:
            Schema dict or None
        """
        package = self._loader.get_document_type(doc_type_id, version)
        return package.get_schema()

    def get_pgc_context(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get the PGC context content for a document type.

        Args:
            doc_type_id: Document type identifier
            version: Specific version or None for active version

        Returns:
            PGC context content or None
        """
        package = self._loader.get_document_type(doc_type_id, version)
        return package.get_pgc_context()

    # =========================================================================
    # Roles
    # =========================================================================

    def list_roles(self) -> List[Dict[str, Any]]:
        """
        List all available role prompts.

        Returns:
            List of role summaries
        """
        role_ids = self._loader.list_roles()
        active = self._loader.get_active_releases()

        summaries = []
        for role_id in sorted(role_ids):
            active_version = active.get_role_version(role_id)

            try:
                role = self._loader.get_role(role_id)
                summaries.append({
                    "role_id": role_id,
                    "active_version": active_version,
                    "content_preview": role.content[:200] + "..." if len(role.content) > 200 else role.content,
                })
            except PackageLoaderError as e:
                logger.warning(f"Could not load role {role_id}: {e}")
                summaries.append({
                    "role_id": role_id,
                    "active_version": active_version,
                    "content_preview": None,
                    "error": str(e),
                })

        return summaries

    def get_role(
        self,
        role_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get full role prompt details.

        Args:
            role_id: Role identifier
            version: Specific version or None for active version

        Returns:
            Role details including content

        Raises:
            PackageNotFoundError: Role not found
            VersionNotFoundError: Requested version not found
        """
        role = self._loader.get_role(role_id, version)

        return {
            "role_id": role.role_id,
            "version": role.version,
            "content": role.content,
        }

    # =========================================================================
    # Templates
    # =========================================================================

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates.

        Returns:
            List of template summaries
        """
        template_ids = self._loader.list_templates()
        active = self._loader.get_active_releases()

        summaries = []
        for template_id in sorted(template_ids):
            active_version = active.get_template_version(template_id)

            try:
                template = self._loader.get_template(template_id)
                summaries.append({
                    "template_id": template_id,
                    "active_version": active_version,
                    "content_preview": template.content[:200] + "..." if len(template.content) > 200 else template.content,
                })
            except PackageLoaderError as e:
                logger.warning(f"Could not load template {template_id}: {e}")
                summaries.append({
                    "template_id": template_id,
                    "active_version": active_version,
                    "content_preview": None,
                    "error": str(e),
                })

        return summaries

    def get_template(
        self,
        template_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get full template details.

        Args:
            template_id: Template identifier
            version: Specific version or None for active version

        Returns:
            Template details including content

        Raises:
            PackageNotFoundError: Template not found
            VersionNotFoundError: Requested version not found
        """
        template = self._loader.get_template(template_id, version)

        return {
            "template_id": template.template_id,
            "version": template.version,
            "content": template.content,
        }

    # =========================================================================
    # Active Releases
    # =========================================================================

    def get_active_releases(self) -> Dict[str, Any]:
        """
        Get the current active releases configuration.

        Returns:
            Active releases data
        """
        active = self._loader.get_active_releases()

        return {
            "document_types": active.document_types,
            "roles": active.roles,
            "templates": active.templates,
            "workflows": active.workflows,
        }

    # =========================================================================
    # Prompt Assembly
    # =========================================================================

    def assemble_prompt(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """
        Assemble the complete prompt for a document type.

        Combines role prompt, task prompt, and schema using the template.

        Args:
            doc_type_id: Document type identifier
            version: Specific version or None for active version

        Returns:
            Assembled prompt string or None
        """
        package = self._loader.get_document_type(doc_type_id, version)
        return self._loader.assemble_prompt(package)

    # =========================================================================
    # Cache Management
    # =========================================================================

    def invalidate_cache(self) -> None:
        """Invalidate the package loader cache."""
        self._loader.invalidate_cache()


# Module-level singleton
_service: Optional[AdminWorkbenchService] = None


def get_admin_workbench_service() -> AdminWorkbenchService:
    """Get the singleton AdminWorkbenchService instance."""
    global _service
    if _service is None:
        _service = AdminWorkbenchService()
    return _service


def reset_admin_workbench_service() -> None:
    """Reset the singleton (for testing)."""
    global _service
    _service = None
    reset_package_loader()

"""
Admin Workbench Service for Git-canonical configuration.

Per ADR-044, this service provides read access to Document Type Packages
and shared artifacts from combine-config/.
"""

import json
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
        self._workflow_doc_type_map: Optional[Dict[str, str]] = None

    # =========================================================================
    # Internal: Workflow-to-DocType mapping
    # =========================================================================

    def _build_workflow_doc_type_map(self) -> Dict[str, str]:
        """
        Build a mapping from document_type -> workflow artifact ID.

        Scans graph-based workflow definitions and reads their document_type field.
        Cached after first call; invalidated with cache.
        """
        if self._workflow_doc_type_map is not None:
            return self._workflow_doc_type_map

        mapping: Dict[str, str] = {}
        active = self._loader.get_active_releases()
        config_path = self._loader.config_path
        workflows_dir = config_path / "workflows"

        if not workflows_dir.exists():
            self._workflow_doc_type_map = mapping
            return mapping

        for workflow_id, version in active.workflows.items():
            definition_path = (
                workflows_dir / workflow_id / "releases" / version / "definition.json"
            )
            try:
                with open(definition_path, "r", encoding="utf-8-sig") as f:
                    raw = json.load(f)

                # Only graph-based workflows have document_type
                if "nodes" in raw and "edges" in raw:
                    doc_type = raw.get("document_type")
                    if doc_type:
                        mapping[doc_type] = f"workflow:{workflow_id}:{version}:definition"
            except (json.JSONDecodeError, FileNotFoundError, OSError):
                continue

        self._workflow_doc_type_map = mapping
        return mapping

    def _find_workflow_for_doc_type(self, doc_type_id: str) -> Optional[str]:
        """
        Find the workflow artifact ID for a document type.

        Returns:
            Artifact ID string (e.g., "workflow:concierge_intake:1.3.0:definition")
            or None if no workflow is associated.
        """
        mapping = self._build_workflow_doc_type_map()
        return mapping.get(doc_type_id)

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
            "qa_template_ref": package.qa_template_ref,
            "pgc_template_ref": package.pgc_template_ref,
            "requires_pgc": package.requires_pgc(),
            "is_llm_generated": package.is_llm_generated(),
            "artifacts": {
                "task_prompt": package.artifacts.task_prompt,
                "qa_prompt": package.artifacts.qa_prompt,
                "reflection_prompt": package.artifacts.reflection_prompt,
                "pgc_context": package.artifacts.pgc_context,
                "schema": package.artifacts.schema,
            },
            "ui": {
                "icon": package.ui.icon,
                "category": package.ui.category,
                "display_order": package.ui.display_order,
            },
            "workflow_ref": self._find_workflow_for_doc_type(package.doc_type_id),
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
    # Workflows
    # =========================================================================

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all available workflow plans (ADR-039 graph-based format).

        Scans combine-config/workflows/ for directories with release versions.

        Returns:
            List of workflow summaries
        """
        import json

        active = self._loader.get_active_releases()
        config_path = self._loader.config_path
        workflows_dir = config_path / "workflows"

        if not workflows_dir.exists():
            return []

        summaries = []
        for workflow_dir in sorted(workflows_dir.iterdir()):
            if not workflow_dir.is_dir() or workflow_dir.name.startswith("_"):
                continue

            workflow_id = workflow_dir.name
            active_version = active.workflows.get(workflow_id)

            if not active_version:
                # Try to find any version
                releases_dir = workflow_dir / "releases"
                if releases_dir.exists():
                    versions = sorted([d.name for d in releases_dir.iterdir() if d.is_dir()])
                    if versions:
                        active_version = versions[-1]

            if not active_version:
                continue

            definition_path = (
                workflow_dir / "releases" / active_version / "definition.json"
            )

            try:
                with open(definition_path, "r", encoding="utf-8-sig") as f:
                    raw = json.load(f)

                # Only include graph-based workflows (ADR-039 format)
                if "nodes" not in raw or "edges" not in raw:
                    continue

                summaries.append({
                    "workflow_id": workflow_id,
                    "name": raw.get("name", workflow_id),
                    "active_version": active_version,
                    "description": raw.get("description"),
                    "node_count": len(raw.get("nodes", [])),
                    "edge_count": len(raw.get("edges", [])),
                })
            except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
                logger.warning(f"Could not load workflow {workflow_id}: {e}")
                summaries.append({
                    "workflow_id": workflow_id,
                    "name": workflow_id,
                    "active_version": active_version,
                    "description": None,
                    "node_count": 0,
                    "edge_count": 0,
                    "error": str(e),
                })

        return summaries

    def list_orchestration_workflows(self) -> List[Dict[str, Any]]:
        """
        List project orchestration workflows (step-based format).

        These are workflow.v1 format files with steps/scopes/document_types,
        NOT ADR-039 graph-based plans.

        Returns:
            List of orchestration workflow summaries
        """
        active = self._loader.get_active_releases()
        config_path = self._loader.config_path
        workflows_dir = config_path / "workflows"

        if not workflows_dir.exists():
            return []

        summaries = []
        for workflow_dir in sorted(workflows_dir.iterdir()):
            if not workflow_dir.is_dir() or workflow_dir.name.startswith("_"):
                continue

            workflow_id = workflow_dir.name
            active_version = active.workflows.get(workflow_id)

            if not active_version:
                releases_dir = workflow_dir / "releases"
                if releases_dir.exists():
                    versions = sorted([d.name for d in releases_dir.iterdir() if d.is_dir()])
                    if versions:
                        active_version = versions[-1]

            if not active_version:
                continue

            definition_path = (
                workflow_dir / "releases" / active_version / "definition.json"
            )

            try:
                with open(definition_path, "r", encoding="utf-8-sig") as f:
                    raw = json.load(f)

                # Only include step-based workflows (NOT graph-based)
                if "nodes" in raw and "edges" in raw:
                    continue

                summaries.append({
                    "workflow_id": workflow_id,
                    "name": raw.get("name", workflow_id.replace("_", " ").title()),
                    "active_version": active_version,
                    "description": raw.get("description"),
                    "step_count": len(raw.get("steps", [])),
                    "schema_version": raw.get("schema_version", "workflow.v1"),
                })
            except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
                logger.warning(f"Could not load orchestration workflow {workflow_id}: {e}")
                summaries.append({
                    "workflow_id": workflow_id,
                    "name": workflow_id.replace("_", " ").title(),
                    "active_version": active_version,
                    "description": None,
                    "step_count": 0,
                    "schema_version": "workflow.v1",
                    "error": str(e),
                })

        return summaries

    def get_workflow(
        self,
        workflow_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get full workflow definition JSON.

        Args:
            workflow_id: Workflow identifier
            version: Specific version or None for active version

        Returns:
            Full workflow definition dict

        Raises:
            PackageNotFoundError: Workflow not found
        """
        import json

        if version is None:
            active = self._loader.get_active_releases()
            version = active.workflows.get(workflow_id)
            if not version:
                raise PackageNotFoundError(
                    f"No active version for workflow: {workflow_id}"
                )

        config_path = self._loader.config_path
        definition_path = (
            config_path / "workflows" / workflow_id /
            "releases" / version / "definition.json"
        )

        if not definition_path.exists():
            raise PackageNotFoundError(
                f"Workflow definition not found: {workflow_id} v{version}"
            )

        with open(definition_path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f)

        return {
            "workflow_id": workflow_id,
            "version": version,
            "definition": raw,
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
        self._workflow_doc_type_map = None


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

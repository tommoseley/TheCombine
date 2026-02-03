"""
Package Loader for Git-canonical configuration.

Per ADR-044, this module loads Document Type Packages and shared artifacts
from the combine-config/ repository.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.config.package_model import (
    DocumentTypePackage,
    RolePrompt,
    Template,
    ActiveReleases,
)

logger = logging.getLogger(__name__)

# Default path to combine-config (relative to project root)
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "combine-config"


class PackageLoaderError(Exception):
    """Error loading a package or artifact."""
    pass


class PackageNotFoundError(PackageLoaderError):
    """Package or artifact not found."""
    pass


class VersionNotFoundError(PackageLoaderError):
    """Requested version not found."""
    pass


class PackageLoader:
    """
    Loads Document Type Packages and shared artifacts from combine-config/.

    This is the primary interface for accessing Git-canonical configuration
    at runtime. All configuration access should go through this class.

    Usage:
        loader = PackageLoader()
        package = loader.get_document_type("project_discovery")
        role = loader.get_role("technical_architect")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the package loader.

        Args:
            config_path: Path to combine-config/ directory.
                        Defaults to combine-config/ in project root.
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH

        if not self.config_path.exists():
            raise PackageLoaderError(f"Config path does not exist: {self.config_path}")

        # Paths
        self._active_releases_path = self.config_path / "_active" / "active_releases.json"
        self._document_types_path = self.config_path / "document_types"
        self._roles_path = self.config_path / "prompts" / "roles"
        self._templates_path = self.config_path / "prompts" / "templates"

        # Caches
        self._active_releases: Optional[ActiveReleases] = None
        self._package_cache: Dict[str, DocumentTypePackage] = {}
        self._role_cache: Dict[str, RolePrompt] = {}
        self._template_cache: Dict[str, Template] = {}

    def get_active_releases(self) -> ActiveReleases:
        """Load and return the active releases configuration."""
        if self._active_releases is None:
            if not self._active_releases_path.exists():
                raise PackageLoaderError(
                    f"Active releases file not found: {self._active_releases_path}"
                )
            self._active_releases = ActiveReleases.from_json(self._active_releases_path)
            logger.debug(f"Loaded active releases: {self._active_releases.document_types}")

        return self._active_releases

    def invalidate_cache(self) -> None:
        """Invalidate all caches. Call after config changes."""
        self._active_releases = None
        self._package_cache.clear()
        self._role_cache.clear()
        self._template_cache.clear()
        logger.info("Package loader cache invalidated")

    # =========================================================================
    # Document Type Packages
    # =========================================================================

    def get_document_type(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> DocumentTypePackage:
        """
        Load a Document Type Package.

        Args:
            doc_type_id: Document type identifier (e.g., "project_discovery")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded DocumentTypePackage

        Raises:
            PackageNotFoundError: Document type not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_doc_type_version(doc_type_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for document type: {doc_type_id}"
                )

        # Check cache
        cache_key = f"{doc_type_id}:{version}"
        if cache_key in self._package_cache:
            return self._package_cache[cache_key]

        # Load package
        package_path = self._document_types_path / doc_type_id / "releases" / version
        if not package_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for document type: {doc_type_id}"
            )

        manifest_path = package_path / "package.yaml"
        if not manifest_path.exists():
            raise PackageLoaderError(
                f"Package manifest not found: {manifest_path}"
            )

        package = DocumentTypePackage.from_yaml(manifest_path)
        self._package_cache[cache_key] = package

        logger.debug(f"Loaded document type package: {doc_type_id} v{version}")
        return package

    def list_document_types(self) -> List[str]:
        """List all available document type IDs."""
        if not self._document_types_path.exists():
            return []

        return [
            d.name for d in self._document_types_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def list_document_type_versions(self, doc_type_id: str) -> List[str]:
        """List all available versions for a document type."""
        releases_path = self._document_types_path / doc_type_id / "releases"
        if not releases_path.exists():
            return []

        return sorted([
            d.name for d in releases_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])

    # =========================================================================
    # Role Prompts
    # =========================================================================

    def get_role(
        self,
        role_id: str,
        version: Optional[str] = None,
    ) -> RolePrompt:
        """
        Load a shared role prompt.

        Args:
            role_id: Role identifier (e.g., "technical_architect")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded RolePrompt

        Raises:
            PackageNotFoundError: Role not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_role_version(role_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for role: {role_id}"
                )

        # Check cache
        cache_key = f"{role_id}:{version}"
        if cache_key in self._role_cache:
            return self._role_cache[cache_key]

        # Load role
        role_path = self._roles_path / role_id / "releases" / version
        if not role_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for role: {role_id}"
            )

        role = RolePrompt.from_path(role_path, role_id, version)
        self._role_cache[cache_key] = role

        logger.debug(f"Loaded role prompt: {role_id} v{version}")
        return role

    def list_roles(self) -> List[str]:
        """List all available role IDs."""
        if not self._roles_path.exists():
            return []

        return [
            d.name for d in self._roles_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # Templates
    # =========================================================================

    def get_template(
        self,
        template_id: str,
        version: Optional[str] = None,
    ) -> Template:
        """
        Load a shared template.

        Args:
            template_id: Template identifier (e.g., "document_generator")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded Template

        Raises:
            PackageNotFoundError: Template not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_template_version(template_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for template: {template_id}"
                )

        # Check cache
        cache_key = f"{template_id}:{version}"
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # Load template
        template_path = self._templates_path / template_id / "releases" / version
        if not template_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for template: {template_id}"
            )

        template = Template.from_path(template_path, template_id, version)
        self._template_cache[cache_key] = template

        logger.debug(f"Loaded template: {template_id} v{version}")
        return template

    def list_templates(self) -> List[str]:
        """List all available template IDs."""
        if not self._templates_path.exists():
            return []

        return [
            d.name for d in self._templates_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def resolve_role_for_package(
        self,
        package: DocumentTypePackage,
    ) -> Optional[RolePrompt]:
        """
        Resolve and load the role prompt referenced by a package.

        Args:
            package: The document type package

        Returns:
            Loaded RolePrompt or None if no role reference
        """
        if not package.role_prompt_ref:
            return None

        # Parse reference: prompt:role:{role_id}:{version}
        parts = package.role_prompt_ref.split(":")
        if len(parts) != 4 or parts[0] != "prompt" or parts[1] != "role":
            logger.warning(f"Invalid role prompt ref: {package.role_prompt_ref}")
            return None

        role_id = parts[2]
        version = parts[3]

        return self.get_role(role_id, version)

    def resolve_template_for_package(
        self,
        package: DocumentTypePackage,
    ) -> Optional[Template]:
        """
        Resolve and load the template referenced by a package.

        Args:
            package: The document type package

        Returns:
            Loaded Template or None if no template reference
        """
        if not package.template_ref:
            return None

        # Parse reference: prompt:template:{template_id}:{version}
        parts = package.template_ref.split(":")
        if len(parts) != 4 or parts[0] != "prompt" or parts[1] != "template":
            logger.warning(f"Invalid template ref: {package.template_ref}")
            return None

        template_id = parts[2]
        version = parts[3]

        return self.get_template(template_id, version)

    def assemble_prompt(
        self,
        package: DocumentTypePackage,
    ) -> Optional[str]:
        """
        Assemble a complete prompt for a document type.

        Combines role prompt, task prompt, and schema using the template.

        Args:
            package: The document type package

        Returns:
            Assembled prompt string or None if unable to assemble
        """
        if not package.is_llm_generated():
            return None

        # Get components
        role = self.resolve_role_for_package(package)
        template = self.resolve_template_for_package(package)
        task_prompt = package.get_task_prompt()
        schema = package.get_schema()

        if not all([role, template, task_prompt]):
            logger.warning(
                f"Cannot assemble prompt for {package.doc_type_id}: "
                f"missing components (role={bool(role)}, template={bool(template)}, "
                f"task={bool(task_prompt)})"
            )
            return None

        # Assemble using template
        import json
        schema_str = json.dumps(schema, indent=2) if schema else ""

        assembled = template.content
        assembled = assembled.replace("$$ROLE_PROMPT", role.content)
        assembled = assembled.replace("$$TASK_PROMPT", task_prompt)
        assembled = assembled.replace("$$OUTPUT_SCHEMA", schema_str)

        return assembled


# Module-level singleton
_loader: Optional[PackageLoader] = None


def get_package_loader(config_path: Optional[Path] = None) -> PackageLoader:
    """
    Get the singleton PackageLoader instance.

    Args:
        config_path: Optional config path. Only used on first call.

    Returns:
        PackageLoader instance
    """
    global _loader

    if _loader is None:
        _loader = PackageLoader(config_path)

    return _loader


def reset_package_loader() -> None:
    """Reset the singleton (for testing)."""
    global _loader
    _loader = None
